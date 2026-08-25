"""Configuração do sistema — sempre relativa à pasta do .xlsm.

Nenhum caminho absoluto de usuário é gravado. A raiz é descoberta a partir
da localização deste arquivo (ou de sys.executable quando empacotado com
PyInstaller), de modo que o mesmo config.json funciona em qualquer máquina.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def raiz_projeto() -> Path:
    """Pasta que contém o .xlsm, as bases, o banco e o config.json.

    Em desenvolvimento este módulo está em <raiz>/python/motor/config.py.
    Empacotado com PyInstaller, o executável fica em <raiz>/motor.exe
    (--onedir coloca-o em <raiz>/motor/motor.exe).
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # --onedir: <raiz>/motor/motor.exe  |  --onefile: <raiz>/motor.exe
        if exe.parent.name.lower() == "motor":
            return exe.parent.parent
        return exe.parent
    return Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------- defaults

# Política de escopo (ver FASE1_DIAGNOSTICO §5.1).
# Cada escopo define se a mão de obra interna entra, se os materiais da
# referência devem ser importados e se os equipamentos devem ser importados.
POLITICA_ESCOPO_PADRAO: dict[str, dict[str, Any]] = {
    "MAO_DE_OBRA": {
        "mao_obra_interna": True, "importar_materiais": True,
        "importar_equipamentos": True, "motivo": "",
    },
    "EXECUCAO_INDEFINIDO": {
        "mao_obra_interna": True, "importar_materiais": True,
        "importar_equipamentos": True, "motivo": "",
    },
    "DEMOLICAO_REMOCAO": {
        "mao_obra_interna": True, "importar_materiais": True,
        "importar_equipamentos": True, "motivo": "",
    },
    "FORNEC_E_INSTAL": {
        "mao_obra_interna": True, "importar_materiais": False,
        "importar_equipamentos": True,
        "motivo": "Serviço interno já inclui fornecimento do material; "
                  "importar materiais da referência causaria dupla contagem.",
    },
    "FORNECIMENTO": {
        "mao_obra_interna": True, "importar_materiais": False,
        "importar_equipamentos": False,
        "motivo": "Serviço interno é apenas fornecimento de material.",
    },
    "LOCACAO": {
        "mao_obra_interna": True, "importar_materiais": False,
        "importar_equipamentos": False,
        "motivo": "Locação não é execução; não comporta insumos de composição.",
    },
}

# Pesos do score de serviços. Somam 1,0 (ver matching.py).
PESOS_SERVICO_PADRAO = {
    "textual": 0.26,
    "semantico": 0.18,
    "cobertura": 0.18,   # cobertura dos termos que identificam o serviço
    "unidade": 0.16,
    "tecnico": 0.22,
}

# Pesos do score de materiais — mais peso no técnico (item 24).
PESOS_MATERIAL_PADRAO = {
    "textual": 0.24,
    "semantico": 0.14,
    "cobertura": 0.16,
    "unidade": 0.12,
    "tecnico": 0.34,
}

# Faixas de confiança (item 35) — calibráveis.
FAIXAS_CONFIANCA_PADRAO = {
    "forte": 0.90,
    "provavel": 0.75,
    "baixa": 0.50,
}


@dataclass
class Config:
    """Configuração efetiva, carregada de config.json com defaults."""

    raiz: Path

    arquivo_servicos: str = ""
    arquivo_materiais: str = ""
    arquivo_edif: str = ""
    arquivo_infra: str = ""
    arquivo_auxiliares: str = ""

    # Sobreposição manual da detecção automática de origem (item 4).
    # Vazio = confiar na detecção pelo conteúdo do arquivo.
    origem_forcada: dict[str, str] = field(default_factory=dict)

    politica_preco_material: str = "VALOR_APROVADO"
    meses_preco_desatualizado: int = 24
    politica_escopo: dict[str, dict[str, Any]] = field(
        default_factory=lambda: json.loads(json.dumps(POLITICA_ESCOPO_PADRAO))
    )

    pesos_servico: dict[str, float] = field(
        default_factory=lambda: dict(PESOS_SERVICO_PADRAO))
    pesos_material: dict[str, float] = field(
        default_factory=lambda: dict(PESOS_MATERIAL_PADRAO))
    faixas_confianca: dict[str, float] = field(
        default_factory=lambda: dict(FAIXAS_CONFIANCA_PADRAO))

    top_n_padrao: int = 10
    score_minimo_sugestao: float = 0.50

    backend_semantico: str = "auto"   # auto | sentence_transformers | tfidf | off
    modelo_embeddings: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    usuario: str = ""

    # ------------------------------------------------------------ caminhos
    @property
    def pasta_bases(self) -> Path:
        p = self.raiz / "BASES"
        return p if p.is_dir() else self.raiz

    @property
    def caminho_db(self) -> Path:
        return self.raiz / "banco_composicoes.db"

    @property
    def caminho_log(self) -> Path:
        return self.raiz / "log.txt"

    @property
    def caminho_config(self) -> Path:
        return self.raiz / "config.json"

    @property
    def pasta_cache(self) -> Path:
        p = self.raiz / ".cache_embeddings"
        p.mkdir(exist_ok=True)
        return p

    def resolver(self, nome_arquivo: str) -> Path | None:
        """Resolve um nome de arquivo de base para caminho absoluto."""
        if not nome_arquivo:
            return None
        p = Path(nome_arquivo)
        if p.is_absolute() and p.exists():
            return p
        for base in (self.pasta_bases, self.raiz):
            cand = base / nome_arquivo
            if cand.exists():
                return cand
        return None

    def usuario_efetivo(self) -> str:
        return (self.usuario or os.environ.get("USERNAME")
                or os.environ.get("USER") or "desconhecido")

    # -------------------------------------------------------------- persistência
    def to_dict(self) -> dict[str, Any]:
        return {
            "arquivo_servicos": self.arquivo_servicos,
            "arquivo_materiais": self.arquivo_materiais,
            "arquivo_edif": self.arquivo_edif,
            "arquivo_infra": self.arquivo_infra,
            "arquivo_auxiliares": self.arquivo_auxiliares,
            "origem_forcada": self.origem_forcada,
            "politica_preco_material": self.politica_preco_material,
            "meses_preco_desatualizado": self.meses_preco_desatualizado,
            "politica_escopo": self.politica_escopo,
            "pesos_servico": self.pesos_servico,
            "pesos_material": self.pesos_material,
            "faixas_confianca": self.faixas_confianca,
            "top_n_padrao": self.top_n_padrao,
            "score_minimo_sugestao": self.score_minimo_sugestao,
            "backend_semantico": self.backend_semantico,
            "modelo_embeddings": self.modelo_embeddings,
            "usuario": self.usuario,
        }

    def salvar(self) -> None:
        self.caminho_config.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def carregar(raiz: Path | str | None = None) -> Config:
    """Carrega config.json da raiz, preenchendo defaults para chaves ausentes."""
    base = Path(raiz) if raiz else raiz_projeto()
    cfg = Config(raiz=base)
    caminho = base / "config.json"
    if not caminho.exists():
        return cfg
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cfg
    if not isinstance(dados, dict):
        return cfg

    for campo in ("arquivo_servicos", "arquivo_materiais", "arquivo_edif",
                  "arquivo_infra", "arquivo_auxiliares",
                  "politica_preco_material", "backend_semantico",
                  "modelo_embeddings", "usuario"):
        if isinstance(dados.get(campo), str):
            setattr(cfg, campo, dados[campo])

    for campo in ("top_n_padrao", "meses_preco_desatualizado"):
        if isinstance(dados.get(campo), int):
            setattr(cfg, campo, dados[campo])
    if isinstance(dados.get("score_minimo_sugestao"), (int, float)):
        cfg.score_minimo_sugestao = float(dados["score_minimo_sugestao"])

    if isinstance(dados.get("origem_forcada"), dict):
        cfg.origem_forcada = {str(k): str(v)
                              for k, v in dados["origem_forcada"].items()}

    # Mesclagem rasa: o usuário pode sobrepor apenas um escopo.
    if isinstance(dados.get("politica_escopo"), dict):
        for esc, regra in dados["politica_escopo"].items():
            if isinstance(regra, dict):
                cfg.politica_escopo.setdefault(esc, {}).update(regra)

    for campo, alvo in (("pesos_servico", cfg.pesos_servico),
                        ("pesos_material", cfg.pesos_material),
                        ("faixas_confianca", cfg.faixas_confianca)):
        if isinstance(dados.get(campo), dict):
            for k, v in dados[campo].items():
                if isinstance(v, (int, float)):
                    alvo[k] = float(v)
    return cfg


def politica_para(cfg: Config, escopo: str) -> dict[str, Any]:
    """Política de composição para um escopo, com fallback seguro."""
    return cfg.politica_escopo.get(
        escopo, cfg.politica_escopo.get("EXECUCAO_INDEFINIDO",
                                        POLITICA_ESCOPO_PADRAO["EXECUCAO_INDEFINIDO"]))
