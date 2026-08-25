"""Importação das bases para o SQLite (itens 53, 54, 55).

Regras:
  * Só reimporta o que mudou — compara SHA-256 com `source_files`.
  * Nunca apaga vínculos confirmados, composições próprias ou regras de
    conversão. Só as tabelas de origem são recriadas.
  * Marca composições próprias como REVISAR quando a referência de que
    nasceram mudou de conteúdo.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import loaders
from .config import Config
from .database import limpar_dados_origem, registrar_log

# Nomes de arquivo prováveis, quando o config.json ainda não foi preenchido.
PISTAS_ARQUIVO = {
    "MATERIAIS": ("materiais",),
    "SERVICOS": ("servico", "serviços", "mao", "mão", "xlsx_5"),
}


@dataclass
class RelatorioImportacao:
    executado_em: str = ""
    cargas: list[dict[str, Any]] = field(default_factory=list)
    ignorados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    revisar: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executado_em": self.executado_em,
            "cargas": self.cargas,
            "ignorados": self.ignorados,
            "avisos": self.avisos,
            "erros": self.erros,
            "composicoes_para_revisar": self.revisar,
        }


def descobrir_arquivos(cfg: Config, con: sqlite3.Connection | None = None
                       ) -> dict[str, Path]:
    """Localiza as bases: config.json, depois a importação anterior, depois varredura.

    A varredura identifica os .xls pelo CONTEÚDO (item 4) — nunca por
    ordem alfabética ou tamanho. Como abrir cada planilha só para
    descobrir o que ela é custa segundos, o mapeamento já estabelecido em
    `source_files` é reaproveitado enquanto o arquivo continuar no lugar.
    """
    achados: dict[str, Path] = {}

    if con is not None:
        for linha in con.execute("SELECT papel, nome_arquivo FROM source_files"):
            caminho = cfg.resolver(linha["nome_arquivo"])
            if caminho and linha["papel"] not in achados:
                achados[linha["papel"]] = caminho

    for papel, campo in (("SERVICOS", "arquivo_servicos"),
                         ("MATERIAIS", "arquivo_materiais"),
                         ("EDIF", "arquivo_edif"),
                         ("INFRA", "arquivo_infra"),
                         ("AUX", "arquivo_auxiliares")):
        caminho = cfg.resolver(getattr(cfg, campo, ""))
        if caminho:
            achados[papel] = caminho          # config.json tem precedência

    pasta = cfg.pasta_bases
    if not pasta.is_dir():
        return achados

    # XLSX ainda não resolvidos: distinguidos pelo cabeçalho.
    for caminho in sorted(pasta.glob("*.xlsx")):
        if caminho.name.startswith("~$") or caminho in achados.values():
            continue
        try:
            aba, linhas = loaders.ler_planilha(caminho)
        except Exception:
            continue
        if "MATERIAIS" not in achados and loaders.localizar_cabecalho(
                linhas, ("CODIGO_MATERIAL",)) is not None:
            achados["MATERIAIS"] = caminho
        elif "SERVICOS" not in achados and loaders.localizar_cabecalho(
                linhas, ("CODIGO", "DESCRICAO")) is not None:
            achados["SERVICOS"] = caminho

    # XLS: origem determinada pelo conteúdo.
    for caminho in sorted(pasta.glob("*.xls")):
        if caminho.name.startswith("~$") or caminho in achados.values():
            continue
        try:
            aba, linhas = loaders.ler_planilha(caminho)
        except Exception:
            continue
        forcada = cfg.origem_forcada.get(caminho.name, "")
        origem, _ = ((forcada, "config") if forcada
                     else loaders.detectar_origem(aba, linhas, caminho.name))
        if origem and origem not in achados:
            achados[origem] = caminho
    return achados


def _precisa_reimportar(con: sqlite3.Connection, papel: str, caminho: Path,
                        forcar: bool) -> tuple[bool, dict[str, Any]]:
    """Decide pelo HASH, antes de parsear — parsear .xls custa segundos."""
    info = loaders.info_arquivo(caminho)
    if forcar:
        return True, info
    return _mudou(con, papel, info), info


def _mudou(con: sqlite3.Connection, papel: str, info: dict[str, Any]) -> bool:
    linha = con.execute(
        "SELECT hash_sha256 FROM source_files WHERE papel = ?", (papel,)).fetchone()
    return linha is None or linha["hash_sha256"] != info["hash_sha256"]


def _gravar_fonte(con: sqlite3.Connection, papel: str, res: loaders.ResultadoCarga) -> None:
    con.execute(
        "INSERT INTO source_files(papel, nome_arquivo, hash_sha256, tamanho_bytes,"
        " data_modificacao, data_base, data_importacao, registros, detectado_por)"
        " VALUES(?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(papel) DO UPDATE SET"
        "  nome_arquivo=excluded.nome_arquivo, hash_sha256=excluded.hash_sha256,"
        "  tamanho_bytes=excluded.tamanho_bytes, data_modificacao=excluded.data_modificacao,"
        "  data_base=excluded.data_base, data_importacao=excluded.data_importacao,"
        "  registros=excluded.registros, detectado_por=excluded.detectado_por",
        (papel, res.info.get("nome_arquivo", ""), res.info.get("hash_sha256", ""),
         res.info.get("tamanho_bytes", 0), res.info.get("data_modificacao", ""),
         res.data_base, datetime.now().isoformat(timespec="seconds"),
         res.registros, res.detectado_por),
    )


def _marcar_revisar(con: sqlite3.Connection, origem: str) -> list[str]:
    """Marca como REVISAR as composições próprias nascidas de uma base
    que acabou de mudar (item 55)."""
    linhas = con.execute(
        "SELECT codigo FROM own_compositions"
        " WHERE origem_referencia = ? AND status IN ('COMPLETA','PENDENTE')",
        (origem,)).fetchall()
    codigos = [l["codigo"] for l in linhas]
    if codigos:
        agora = datetime.now().isoformat(timespec="seconds")
        con.executemany(
            "UPDATE own_compositions SET status='REVISAR',"
            " motivo_status='Base de referência ' || ? || ' foi atualizada.',"
            " data_atualizacao=? WHERE codigo=?",
            [(origem, agora, c) for c in codigos])
    return codigos


def importar(con: sqlite3.Connection, cfg: Config, *, forcar: bool = False
             ) -> RelatorioImportacao:
    """Importa (ou reimporta) as bases. Idempotente e incremental."""
    rel = RelatorioImportacao(executado_em=datetime.now().isoformat(timespec="seconds"))
    arquivos = descobrir_arquivos(cfg, con)

    for papel in ("SERVICOS", "MATERIAIS", "EDIF", "INFRA", "AUX"):
        if papel not in arquivos:
            rel.avisos.append(f"Base {papel} não localizada em {cfg.pasta_bases}.")

    # A base de auxiliares precisa ser lida antes, para classificar os
    # insumos de EDIF/INFRA que apontam para composições auxiliares.
    # Só é preciso relê-la se alguma base de referência será reimportada.
    codigos_aux: set[str] = set()
    precisa_aux = any(
        papel in arquivos and _precisa_reimportar(con, papel, arquivos[papel], forcar)[0]
        for papel in ("AUX", "EDIF", "INFRA"))
    if "AUX" in arquivos and precisa_aux:
        try:
            codigos_aux = loaders.ler_codigos_auxiliares(arquivos["AUX"])
        except Exception as exc:                         # noqa: BLE001
            rel.erros.append(f"Falha ao ler códigos auxiliares: {exc}")

    # ------------------------------------------------------------ serviços
    if "SERVICOS" in arquivos:
        caminho = arquivos["SERVICOS"]
        try:
            reimportar, _info = _precisa_reimportar(con, "SERVICOS", caminho, forcar)
            if not reimportar:
                rel.ignorados.append(f"SERVICOS ({caminho.name}) — inalterada.")
                res = loaders.ResultadoCarga(papel="SERVICOS")
            else:
                res, registros = loaders.carregar_servicos(caminho)
                limpar_dados_origem(con, ["SERVICOS"])
                con.executemany(
                    "INSERT INTO company_services(codigo, familia, unidade, unidade_orig,"
                    " descricao, descricao_norm, preco, preco_texto, preco_aprovado,"
                    " escopo, linha_origem)"
                    " VALUES(:codigo,:familia,:unidade,:unidade_orig,:descricao,"
                    ":descricao_norm,:preco,:preco_texto,:preco_aprovado,:escopo,"
                    ":linha_origem)", registros)
                _gravar_fonte(con, "SERVICOS", res)
                rel.cargas.append({"papel": "SERVICOS", "arquivo": caminho.name,
                                   "registros": res.registros, "aba": res.aba})
            rel.avisos.extend(f"SERVICOS: {a}" for a in res.avisos)
        except Exception as exc:                         # noqa: BLE001
            rel.erros.append(f"SERVICOS ({caminho.name}): {exc}")

    # ------------------------------------------------------------ materiais
    if "MATERIAIS" in arquivos:
        caminho = arquivos["MATERIAIS"]
        try:
            reimportar, _info = _precisa_reimportar(con, "MATERIAIS", caminho, forcar)
            if not reimportar:
                rel.ignorados.append(f"MATERIAIS ({caminho.name}) — inalterada.")
                res = loaders.ResultadoCarga(papel="MATERIAIS")
            else:
                res, registros = loaders.carregar_materiais(
                    caminho, cfg.politica_preco_material)
                limpar_dados_origem(con, ["MATERIAIS"])
                con.executemany(
                    "INSERT INTO company_materials(codigo, item, familia, unidade,"
                    " unidade_orig, descricao, descricao_norm, tipo_item, preco,"
                    " preco_valor, preco_ultimo, data_ultimo, politica_preco, fonte,"
                    " linha_origem)"
                    " VALUES(:codigo,:item,:familia,:unidade,:unidade_orig,:descricao,"
                    ":descricao_norm,:tipo_item,:preco,:preco_valor,:preco_ultimo,"
                    ":data_ultimo,:politica_preco,:fonte,:linha_origem)", registros)
                historico = [
                    (r["codigo"], i, data, preco)
                    for r in registros
                    for i, (data, preco) in enumerate(r["_historico"])
                ]
                con.executemany(
                    "INSERT OR REPLACE INTO company_material_prices"
                    "(codigo, ordem, data, preco) VALUES(?,?,?,?)", historico)
                _gravar_fonte(con, "MATERIAIS", res)
                rel.cargas.append({"papel": "MATERIAIS", "arquivo": caminho.name,
                                   "registros": res.registros, "aba": res.aba,
                                   "precos_historicos": len(historico)})
            rel.avisos.extend(f"MATERIAIS: {a}" for a in res.avisos)
        except Exception as exc:                         # noqa: BLE001
            rel.erros.append(f"MATERIAIS ({caminho.name}): {exc}")

    # ------------------------------------------------------------ referências
    for papel in ("AUX", "EDIF", "INFRA"):
        if papel not in arquivos:
            continue
        caminho = arquivos[papel]
        try:
            reimportar, _info = _precisa_reimportar(con, papel, caminho, forcar)
            if not reimportar:
                rel.ignorados.append(f"{papel} ({caminho.name}) — inalterada.")
                continue
            forcada = cfg.origem_forcada.get(caminho.name, "")
            res, comps, insumos = loaders.carregar_referencia(
                caminho, codigos_aux, forcada)
            if res.origem and res.origem != papel:
                rel.avisos.append(
                    f"{caminho.name}: detectado como {res.origem} "
                    f"({res.detectado_por}).")
            origem = res.origem or papel
            if True:
                if _existe_fonte(con, origem):
                    rel.revisar.extend(_marcar_revisar(con, origem))
                limpar_dados_origem(con, [origem])
                con.executemany(
                    "INSERT INTO reference_compositions(origem, codigo, descricao,"
                    " descricao_norm, unidade, unidade_orig, custo_total, data_base,"
                    " linha_origem)"
                    " VALUES(:origem,:codigo,:descricao,:descricao_norm,:unidade,"
                    ":unidade_orig,:custo_total,:data_base,:linha_origem)", comps)
                con.executemany(
                    "INSERT INTO reference_inputs(origem, codigo, seq, codins, descricao,"
                    " descricao_norm, unidade, unidade_orig, custo_unitario, coeficiente,"
                    " valor_parcial, classe, origem_aux, linha_origem)"
                    " VALUES(:origem,:codigo,:seq,:codins,:descricao,:descricao_norm,"
                    ":unidade,:unidade_orig,:custo_unitario,:coeficiente,:valor_parcial,"
                    ":classe,:origem_aux,:linha_origem)", insumos)
                _gravar_fonte(con, origem, res)
                rel.cargas.append({
                    "papel": origem, "arquivo": caminho.name,
                    "registros": res.registros, "insumos": res.insumos,
                    "data_base": res.data_base, "aba": res.aba,
                    "detectado_por": res.detectado_por})
            rel.avisos.extend(f"{origem}: {a}" for a in res.avisos)
        except Exception as exc:                         # noqa: BLE001
            rel.erros.append(f"{papel} ({caminho.name}): {exc}")

    registrar_log(
        con, usuario=cfg.usuario_efetivo(), acao="ATUALIZAR_BASES",
        entidade="source_files",
        detalhe=f"cargas={len(rel.cargas)} ignorados={len(rel.ignorados)} "
                f"erros={len(rel.erros)}",
        sucesso=not rel.erros)
    con.commit()
    return rel


def _existe_fonte(con: sqlite3.Connection, papel: str) -> bool:
    return con.execute(
        "SELECT 1 FROM source_files WHERE papel = ?", (papel,)).fetchone() is not None
