"""Esquema e acesso ao SQLite (item 32).

Duas classes de tabela, com ciclos de vida diferentes:

  * DADOS DE ORIGEM (`company_*`, `reference_*`) — reconstruídos a cada
    "ATUALIZAR BASES". Podem ser apagados e reimportados sem perda.
  * CONHECIMENTO DA EMPRESA (`*_mappings`, `own_*`, `conversion_rules`,
    `pending_mappings`, `audit_log`) — NUNCA são apagados por uma
    reimportação (item 53). É o ativo que o sistema constrói.

Chave de referência é sempre o par (origem, codigo) — ver diagnóstico §2.1.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

ESQUEMA_VERSAO = 1

DDL = """
PRAGMA foreign_keys = ON;

-- ====================================================================
-- CONTROLE
-- ====================================================================
CREATE TABLE IF NOT EXISTS schema_info (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Detecção de alteração das bases (itens 54 e 55).
CREATE TABLE IF NOT EXISTS source_files (
    papel            TEXT PRIMARY KEY,   -- SERVICOS|MATERIAIS|EDIF|INFRA|AUX
    nome_arquivo     TEXT NOT NULL,
    hash_sha256      TEXT NOT NULL,
    tamanho_bytes    INTEGER NOT NULL,
    data_modificacao TEXT,
    data_base        TEXT,               -- ex.: JAN/2026, lido do cabeçalho
    data_importacao  TEXT NOT NULL,
    registros        INTEGER NOT NULL DEFAULT 0,
    detectado_por    TEXT NOT NULL DEFAULT ''
);

-- ====================================================================
-- DADOS DE ORIGEM — recriados a cada atualização de bases
-- ====================================================================
CREATE TABLE IF NOT EXISTS company_services (
    codigo         TEXT PRIMARY KEY,
    familia        TEXT NOT NULL DEFAULT '',
    unidade        TEXT NOT NULL DEFAULT '',
    unidade_orig   TEXT NOT NULL DEFAULT '',
    descricao      TEXT NOT NULL,
    descricao_norm TEXT NOT NULL DEFAULT '',
    preco          REAL,
    preco_texto    TEXT NOT NULL DEFAULT '',
    preco_aprovado INTEGER NOT NULL DEFAULT 0,
    escopo         TEXT NOT NULL DEFAULT 'EXECUCAO_INDEFINIDO',
    linha_origem   INTEGER
);
CREATE INDEX IF NOT EXISTS ix_cs_familia ON company_services(familia);
CREATE INDEX IF NOT EXISTS ix_cs_unidade ON company_services(unidade);

CREATE TABLE IF NOT EXISTS company_materials (
    codigo         TEXT PRIMARY KEY,
    item           INTEGER,
    familia        TEXT NOT NULL DEFAULT '',
    unidade        TEXT NOT NULL DEFAULT '',
    unidade_orig   TEXT NOT NULL DEFAULT '',
    descricao      TEXT NOT NULL,
    descricao_norm TEXT NOT NULL DEFAULT '',
    tipo_item      TEXT NOT NULL DEFAULT 'MATERIAL',   -- MATERIAL|EQUIPAMENTO
    preco          REAL,                                -- preço vigente aplicado
    preco_valor    REAL,                                -- coluna VALOR da base
    preco_ultimo   REAL,                                -- cotação mais recente
    data_ultimo    TEXT,
    politica_preco TEXT NOT NULL DEFAULT 'VALOR_APROVADO',
    fonte          TEXT NOT NULL DEFAULT 'MATERIAIS',
    linha_origem   INTEGER
);
CREATE INDEX IF NOT EXISTS ix_cm_familia ON company_materials(familia);
CREATE INDEX IF NOT EXISTS ix_cm_tipo    ON company_materials(tipo_item);

-- Histórico de preços normalizado (item 52).
CREATE TABLE IF NOT EXISTS company_material_prices (
    codigo TEXT NOT NULL,
    ordem  INTEGER NOT NULL,      -- 0 = mais recente
    data   TEXT,
    preco  REAL NOT NULL,
    PRIMARY KEY (codigo, ordem),
    FOREIGN KEY (codigo) REFERENCES company_materials(codigo) ON DELETE CASCADE
);

-- Composições de referência. Chave composta: EDIF e INFRA colidem em 37 códigos.
CREATE TABLE IF NOT EXISTS reference_compositions (
    origem         TEXT NOT NULL,        -- EDIF|INFRA|AUX
    codigo         TEXT NOT NULL,
    descricao      TEXT NOT NULL,
    descricao_norm TEXT NOT NULL DEFAULT '',
    unidade        TEXT NOT NULL DEFAULT '',
    unidade_orig   TEXT NOT NULL DEFAULT '',
    custo_total    REAL,
    data_base      TEXT NOT NULL DEFAULT '',
    linha_origem   INTEGER,
    PRIMARY KEY (origem, codigo)
);
CREATE INDEX IF NOT EXISTS ix_rc_unidade ON reference_compositions(unidade);

CREATE TABLE IF NOT EXISTS reference_inputs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    origem         TEXT NOT NULL,
    codigo         TEXT NOT NULL,        -- composição-pai
    seq            INTEGER NOT NULL,
    codins         TEXT NOT NULL,
    descricao      TEXT NOT NULL,
    descricao_norm TEXT NOT NULL DEFAULT '',
    unidade        TEXT NOT NULL DEFAULT '',
    unidade_orig   TEXT NOT NULL DEFAULT '',
    custo_unitario REAL,
    coeficiente    REAL NOT NULL DEFAULT 0,
    valor_parcial  REAL,
    classe         TEXT NOT NULL,        -- MATERIAL|EQUIPAMENTO|MAO_DE_OBRA|COMPOSICAO_AUXILIAR|OUTRO
    origem_aux     TEXT NOT NULL DEFAULT '',  -- origem da auxiliar referenciada
    linha_origem   INTEGER,
    FOREIGN KEY (origem, codigo)
        REFERENCES reference_compositions(origem, codigo) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_ri_pai    ON reference_inputs(origem, codigo);
CREATE INDEX IF NOT EXISTS ix_ri_codins ON reference_inputs(codins);
CREATE INDEX IF NOT EXISTS ix_ri_classe ON reference_inputs(classe);

-- ====================================================================
-- CONHECIMENTO DA EMPRESA — preservado entre atualizações (item 53)
-- ====================================================================

-- Vínculo serviço interno -> composição de referência (item 15).
CREATE TABLE IF NOT EXISTS service_mappings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_empresa    TEXT NOT NULL,
    origem            TEXT NOT NULL,
    codigo_referencia TEXT NOT NULL,
    score_original    REAL,
    detalhe_score     TEXT NOT NULL DEFAULT '',
    confirmado        INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'ATUAL',   -- ATUAL|SUBSTITUIDO|REJEITADO
    substituido_por   INTEGER,
    data              TEXT NOT NULL,
    usuario           TEXT NOT NULL DEFAULT '',
    observacao        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_sm_empresa ON service_mappings(codigo_empresa, status);
CREATE UNIQUE INDEX IF NOT EXISTS ux_sm_atual
    ON service_mappings(codigo_empresa) WHERE status = 'ATUAL';

-- Vínculo insumo de referência -> item interno (materiais e equipamentos).
-- `chave_tecnica` evita vínculos globais indevidos (item 58): quando o
-- insumo tem discriminantes técnicos, eles entram na chave.
CREATE TABLE IF NOT EXISTS material_mappings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL DEFAULT 'MATERIAL',  -- MATERIAL|EQUIPAMENTO
    origem            TEXT NOT NULL DEFAULT '',
    codins            TEXT NOT NULL,
    descricao_ref     TEXT NOT NULL DEFAULT '',
    unidade_ref       TEXT NOT NULL DEFAULT '',
    chave_tecnica     TEXT NOT NULL DEFAULT '',
    codigo_empresa    TEXT NOT NULL,
    score_original    REAL,
    detalhe_score     TEXT NOT NULL DEFAULT '',
    fator_conversao   REAL NOT NULL DEFAULT 1.0,
    metodo_conversao  TEXT NOT NULL DEFAULT '',
    escopo_vinculo    TEXT NOT NULL DEFAULT 'GLOBAL',    -- GLOBAL|COMPOSICAO
    codigo_composicao TEXT NOT NULL DEFAULT '',
    confirmado        INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'ATUAL',
    substituido_por   INTEGER,
    data              TEXT NOT NULL,
    usuario           TEXT NOT NULL DEFAULT '',
    observacao        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_mm_codins ON material_mappings(codins, status);
CREATE INDEX IF NOT EXISTS ix_mm_chave  ON material_mappings(chave_tecnica, status);

-- Visão dedicada a equipamentos (item 32) sobre o mesmo armazenamento,
-- para consulta direta sem duplicar dados.
CREATE VIEW IF NOT EXISTS equipment_mappings AS
    SELECT * FROM material_mappings WHERE tipo = 'EQUIPAMENTO';

-- Composição própria da empresa (item 29).
CREATE TABLE IF NOT EXISTS own_compositions (
    codigo             TEXT PRIMARY KEY,          -- CP-000001
    codigo_servico     TEXT NOT NULL,
    descricao          TEXT NOT NULL,
    unidade            TEXT NOT NULL DEFAULT '',
    origem_referencia  TEXT NOT NULL DEFAULT '',
    codigo_referencia  TEXT NOT NULL DEFAULT '',
    -- Versionamento da referência (item 55).
    arquivo_referencia TEXT NOT NULL DEFAULT '',
    data_base_ref      TEXT NOT NULL DEFAULT '',
    hash_ref           TEXT NOT NULL DEFAULT '',
    escopo_servico     TEXT NOT NULL DEFAULT '',
    custo_mao_obra     REAL NOT NULL DEFAULT 0,
    custo_materiais    REAL NOT NULL DEFAULT 0,
    custo_equipamentos REAL NOT NULL DEFAULT 0,
    custo_direto       REAL NOT NULL DEFAULT 0,
    status             TEXT NOT NULL DEFAULT 'PENDENTE',  -- COMPLETA|PENDENTE|REVISAR|DESATUALIZADA
    motivo_status      TEXT NOT NULL DEFAULT '',
    data_criacao       TEXT NOT NULL,
    data_atualizacao   TEXT NOT NULL,
    usuario            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_oc_servico ON own_compositions(codigo_servico);
CREATE INDEX IF NOT EXISTS ix_oc_status  ON own_compositions(status);

-- Itens da composição própria, com rastreabilidade completa (item 31).
CREATE TABLE IF NOT EXISTS own_composition_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_composicao   TEXT NOT NULL,
    seq                 INTEGER NOT NULL,
    tipo                TEXT NOT NULL,     -- MAO_DE_OBRA|MATERIAL|EQUIPAMENTO
    -- lado interno
    codigo_interno      TEXT NOT NULL DEFAULT '',
    descricao_interna   TEXT NOT NULL DEFAULT '',
    unidade_interna     TEXT NOT NULL DEFAULT '',
    preco_interno       REAL,
    -- lado referencial
    origem_ref          TEXT NOT NULL DEFAULT '',
    codins_ref          TEXT NOT NULL DEFAULT '',
    descricao_ref       TEXT NOT NULL DEFAULT '',
    unidade_ref         TEXT NOT NULL DEFAULT '',
    coeficiente_original REAL,
    caminho_expansao    TEXT NOT NULL DEFAULT '',   -- árvore de auxiliares
    -- conversão e resultado
    fator_conversao     REAL NOT NULL DEFAULT 1.0,
    metodo_conversao    TEXT NOT NULL DEFAULT '',
    justificativa_conv  TEXT NOT NULL DEFAULT '',
    coeficiente_final   REAL NOT NULL DEFAULT 0,
    custo_item          REAL NOT NULL DEFAULT 0,
    -- proveniência da decisão
    score               REAL,
    detalhe_score       TEXT NOT NULL DEFAULT '',
    incluido_no_custo   INTEGER NOT NULL DEFAULT 1,
    motivo_exclusao     TEXT NOT NULL DEFAULT '',
    pendencia           TEXT NOT NULL DEFAULT '',
    data_validacao      TEXT NOT NULL DEFAULT '',
    usuario             TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (codigo_composicao)
        REFERENCES own_compositions(codigo) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_oci_comp ON own_composition_items(codigo_composicao);

-- Regras de conversão dependentes do produto (itens 26 e 27).
CREATE TABLE IF NOT EXISTS conversion_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    escopo          TEXT NOT NULL DEFAULT 'MATERIAL',  -- MATERIAL|FAMILIA|GLOBAL
    chave           TEXT NOT NULL,      -- código do material, família, ou ''
    unidade_origem  TEXT NOT NULL,
    unidade_destino TEXT NOT NULL,
    fator           REAL NOT NULL,
    justificativa   TEXT NOT NULL DEFAULT '',
    data            TEXT NOT NULL,
    usuario         TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_cr
    ON conversion_rules(escopo, chave, unidade_origem, unidade_destino);

-- Central de pendências (item 38).
CREATE TABLE IF NOT EXISTS pending_mappings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL,
    codigo_servico    TEXT NOT NULL DEFAULT '',
    codigo_composicao TEXT NOT NULL DEFAULT '',
    origem            TEXT NOT NULL DEFAULT '',
    codigo_referencia TEXT NOT NULL DEFAULT '',
    codins            TEXT NOT NULL DEFAULT '',
    descricao         TEXT NOT NULL DEFAULT '',
    detalhe           TEXT NOT NULL DEFAULT '',
    prioridade        INTEGER NOT NULL DEFAULT 5,
    status            TEXT NOT NULL DEFAULT 'ABERTA',   -- ABERTA|RESOLVIDA|IGNORADA
    data              TEXT NOT NULL,
    data_resolucao    TEXT NOT NULL DEFAULT '',
    usuario           TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_pm_status ON pending_mappings(status, tipo);

-- Log de auditoria (item 56).
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    data      TEXT NOT NULL,
    usuario   TEXT NOT NULL DEFAULT '',
    acao      TEXT NOT NULL,
    entidade  TEXT NOT NULL DEFAULT '',
    chave     TEXT NOT NULL DEFAULT '',
    detalhe   TEXT NOT NULL DEFAULT '',
    score     REAL,
    sucesso   INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_al_data ON audit_log(data);
"""

# Tabelas recriadas em cada "ATUALIZAR BASES". As demais são preservadas.
TABELAS_ORIGEM = (
    "reference_inputs",
    "reference_compositions",
    "company_material_prices",
    "company_materials",
    "company_services",
)


def conectar(caminho: Path | str) -> sqlite3.Connection:
    """Abre a conexão com o banco, criando o esquema se necessário."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(caminho))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript(DDL)
    con.execute(
        "INSERT INTO schema_info(chave, valor) VALUES('versao', ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (str(ESQUEMA_VERSAO),),
    )
    con.commit()
    return con


def limpar_dados_origem(con: sqlite3.Connection, papeis: Iterable[str] | None = None) -> None:
    """Apaga apenas os dados de origem. O conhecimento da empresa fica intacto.

    `papeis` permite reimportar somente as bases que mudaram (item 54).
    """
    papeis = set(papeis) if papeis is not None else None
    if papeis is None:
        for tabela in TABELAS_ORIGEM:
            con.execute(f"DELETE FROM {tabela}")
        con.commit()
        return

    if "SERVICOS" in papeis:
        con.execute("DELETE FROM company_services")
    if "MATERIAIS" in papeis:
        con.execute("DELETE FROM company_material_prices")
        con.execute("DELETE FROM company_materials")
    origens = {p for p in papeis if p in {"EDIF", "INFRA", "AUX"}}
    for origem in origens:
        con.execute("DELETE FROM reference_inputs WHERE origem = ?", (origem,))
        con.execute("DELETE FROM reference_compositions WHERE origem = ?", (origem,))
    con.commit()


def registrar_log(
    con: sqlite3.Connection,
    *,
    usuario: str,
    acao: str,
    entidade: str = "",
    chave: str = "",
    detalhe: str = "",
    score: float | None = None,
    sucesso: bool = True,
) -> None:
    """Grava uma linha de auditoria (item 56)."""
    from datetime import datetime

    con.execute(
        "INSERT INTO audit_log(data, usuario, acao, entidade, chave, detalhe, score, sucesso)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), usuario, acao,
         entidade, chave, detalhe, score, 1 if sucesso else 0),
    )


def escalar(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    linha = con.execute(sql, params).fetchone()
    return linha[0] if linha else None
