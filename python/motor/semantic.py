"""Camada semântica local (itens 43, 44, 45).

Dois backends, escolhidos automaticamente:

  1. `sentence-transformers` — modelo multilíngue local, quando instalado.
  2. TF-IDF + n-gramas de caractere, implementado aqui sem dependências.

O item 44 exige que o sistema continue funcionando sem LLM, e o item 45
proíbe API paga. O backend 2 garante isso: é determinístico, roda sem
download, sem rede e sem GPU. O backend 1 é um upgrade opcional.

O índice é persistido em disco (item 43) e reconstruído apenas quando o
conteúdo do corpus muda — a consulta gera embedding só da query.
"""
from __future__ import annotations

import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .normalize import chave_comparacao, normalizar_texto

VERSAO_INDICE = 3


# ------------------------------------------------------- backend determinístico

def _ngramas(texto: str, n: int = 4) -> list[str]:
    """N-gramas de caractere sobre o texto normalizado.

    Robustos a abreviação e flexão ("CIMENTO"/"CIM.") sem precisar de
    dicionário — o que importa aqui é o português técnico da construção.
    """
    t = f" {texto} "
    if len(t) <= n:
        return [t]
    return [t[i:i + n] for i in range(len(t) - n + 1)]


def _termos(texto: str) -> list[str]:
    palavras = [p for p in re.split(r"[^0-9A-Z]+", texto) if len(p) >= 2]
    saida = list(palavras)
    for p in palavras:
        saida.extend(_ngramas(p, 4) if len(p) > 4 else [])
    return saida


@dataclass
class IndiceTfIdf:
    """Índice TF-IDF esparso com similaridade de cosseno."""

    idf: dict[str, float]
    vetores: list[dict[str, float]]
    ids: list[str]

    def vetorizar(self, texto: str) -> dict[str, float]:
        contagem = Counter(_termos(normalizar_texto(texto)))
        if not contagem:
            return {}
        vetor = {t: (1.0 + math.log(c)) * self.idf.get(t, 0.0)
                 for t, c in contagem.items()}
        vetor = {t: v for t, v in vetor.items() if v > 0.0}
        norma = math.sqrt(sum(v * v for v in vetor.values()))
        if norma == 0.0:
            return {}
        return {t: v / norma for t, v in vetor.items()}

    def similaridades(self, texto: str, candidatos: Sequence[int] | None = None
                      ) -> dict[int, float]:
        consulta = self.vetorizar(texto)
        if not consulta:
            return {}
        alvos = candidatos if candidatos is not None else range(len(self.vetores))
        saida: dict[int, float] = {}
        for i in alvos:
            doc = self.vetores[i]
            if len(consulta) < len(doc):
                acumulado = sum(v * doc.get(t, 0.0) for t, v in consulta.items())
            else:
                acumulado = sum(v * consulta.get(t, 0.0) for t, v in doc.items())
            if acumulado > 0.0:
                saida[i] = acumulado
        return saida


def construir_tfidf(textos: Sequence[str], ids: Sequence[str]) -> IndiceTfIdf:
    docs = [Counter(_termos(normalizar_texto(t))) for t in textos]
    n = max(1, len(docs))
    freq: Counter[str] = Counter()
    for d in docs:
        freq.update(d.keys())
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in freq.items()}
    indice = IndiceTfIdf(idf=idf, vetores=[], ids=list(ids))
    for d in docs:
        if not d:
            indice.vetores.append({})
            continue
        vetor = {t: (1.0 + math.log(c)) * idf.get(t, 0.0) for t, c in d.items()}
        vetor = {t: v for t, v in vetor.items() if v > 0.0}
        norma = math.sqrt(sum(v * v for v in vetor.values()))
        indice.vetores.append({t: v / norma for t, v in vetor.items()}
                              if norma else {})
    return indice


# ------------------------------------------------------------------ fachada

class MotorSemantico:
    """Fachada sobre o backend disponível, com cache em disco."""

    def __init__(self, pasta_cache: Path, backend: str = "auto",
                 modelo: str = "") -> None:
        self.pasta_cache = Path(pasta_cache)
        self.pasta_cache.mkdir(parents=True, exist_ok=True)
        self.modelo_nome = modelo
        self.backend = self._resolver_backend(backend)
        self._st = None
        self._indices: dict[str, object] = {}

    # -------------------------------------------------------------- backend
    def _resolver_backend(self, pedido: str) -> str:
        if pedido == "off":
            return "off"
        if pedido in {"tfidf", "sentence_transformers"}:
            return pedido
        try:                                    # auto
            import sentence_transformers  # noqa: F401
            return "sentence_transformers"
        except Exception:                        # noqa: BLE001
            return "tfidf"          # instalação quebrada também cai aqui

    def _modelo_st(self):
        if self._st is None:
            from sentence_transformers import SentenceTransformer
            self._st = SentenceTransformer(self.modelo_nome)
        return self._st

    def descricao_backend(self) -> str:
        if self.backend == "sentence_transformers":
            return f"sentence-transformers ({self.modelo_nome}) — local"
        if self.backend == "tfidf":
            return "TF-IDF + n-gramas de caractere — local, determinístico"
        return "desativado"

    # ---------------------------------------------------------------- índice
    def _caminho(self, nome: str) -> Path:
        return self.pasta_cache / f"{nome}.{self.backend}.v{VERSAO_INDICE}.pkl"

    @staticmethod
    def _impressao(textos: Sequence[str]) -> str:
        """Impressão digital do corpus — decide se o índice está válido."""
        import hashlib
        h = hashlib.sha256()
        h.update(str(len(textos)).encode())
        for t in textos:
            h.update(chave_comparacao(t).encode())
            h.update(b"\x00")
        return h.hexdigest()

    def indexar(self, nome: str, textos: Sequence[str], ids: Sequence[str],
                *, forcar: bool = False) -> None:
        """Constrói ou recarrega o índice (item 43).

        Não recalcula quando o corpus não mudou.
        """
        if self.backend == "off":
            return
        impressao = self._impressao(textos)
        caminho = self._caminho(nome)
        if not forcar and caminho.exists():
            try:
                dados = pickle.loads(caminho.read_bytes())
                if dados.get("impressao") == impressao:
                    self._indices[nome] = dados["indice"]
                    return
            except Exception:                    # noqa: BLE001
                pass                             # cache corrompido: reconstrói

        if self.backend == "sentence_transformers":
            modelo = self._modelo_st()
            matriz = modelo.encode(
                [normalizar_texto(t) for t in textos],
                batch_size=64, convert_to_numpy=True,
                normalize_embeddings=True, show_progress_bar=False)
            indice: object = {"ids": list(ids), "matriz": matriz}
        else:
            indice = construir_tfidf(textos, ids)

        self._indices[nome] = indice
        try:
            caminho.write_bytes(pickle.dumps(
                {"impressao": impressao, "indice": indice},
                protocol=pickle.HIGHEST_PROTOCOL))
        except OSError:
            pass                                 # cache é otimização, não requisito

    def tem_indice(self, nome: str) -> bool:
        return nome in self._indices

    def similaridades(self, nome: str, consulta: str,
                      candidatos: Sequence[int] | None = None) -> dict[int, float]:
        """Similaridade semântica da consulta contra o índice (0..1)."""
        if self.backend == "off" or nome not in self._indices:
            return {}
        indice = self._indices[nome]
        if self.backend == "sentence_transformers":
            import numpy as np
            modelo = self._modelo_st()
            vetor = modelo.encode([normalizar_texto(consulta)],
                                  convert_to_numpy=True,
                                  normalize_embeddings=True)[0]
            matriz = indice["matriz"]                    # type: ignore[index]
            if candidatos is not None:
                idx = np.fromiter(candidatos, dtype=np.int64)
                if idx.size == 0:
                    return {}
                escores = matriz[idx] @ vetor
                return {int(i): float(s) for i, s in zip(idx, escores) if s > 0}
            escores = matriz @ vetor
            return {int(i): float(s) for i, s in enumerate(escores) if s > 0}
        return indice.similaridades(consulta, candidatos)   # type: ignore[union-attr]
