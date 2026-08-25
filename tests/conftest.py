"""Fixtures compartilhadas.

Os testes rodam contra as BASES REAIS quando elas estão presentes, porque
o valor da suíte está justamente em provar o comportamento sobre os dados
de verdade. Quando não estão, os testes que dependem delas são pulados com
motivo explícito, e os testes de unidade continuam rodando.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "python"))

from motor import config, database, ingest                      # noqa: E402
from motor.compositions import ExpansorComposicoes              # noqa: E402
from motor.matching import BuscadorMateriais, BuscadorServicos  # noqa: E402
from motor.own import MontadorComposicaoPropria                 # noqa: E402
from motor.semantic import MotorSemantico                       # noqa: E402


def _tem_bases() -> bool:
    cfg = config.carregar(RAIZ)
    achados = ingest.descobrir_arquivos(cfg)
    return {"SERVICOS", "MATERIAIS", "EDIF", "INFRA", "AUX"} <= set(achados)


precisa_bases = pytest.mark.skipif(
    not _tem_bases(),
    reason="Bases originais ausentes em BASES/ — teste de integração pulado.")


@pytest.fixture(scope="session")
def cfg():
    return config.carregar(RAIZ)


@pytest.fixture(scope="session")
def con(cfg):
    conexao = database.conectar(cfg.caminho_db)
    if database.escalar(conexao, "SELECT COUNT(*) FROM company_services") in (0, None):
        ingest.importar(conexao, cfg)
    yield conexao
    conexao.close()


@pytest.fixture(scope="session")
def semantico(cfg):
    return MotorSemantico(cfg.pasta_cache, cfg.backend_semantico,
                          cfg.modelo_embeddings)


@pytest.fixture(scope="session")
def buscador_servicos(con, cfg, semantico):
    b = BuscadorServicos(con, cfg, semantico)
    b.carregar()
    return b


@pytest.fixture(scope="session")
def buscador_materiais(con, cfg, semantico):
    return BuscadorMateriais(con, cfg, semantico)


@pytest.fixture(scope="session")
def expansor(con):
    return ExpansorComposicoes(con)


@pytest.fixture(scope="session")
def montador(con, cfg, expansor, buscador_materiais):
    return MontadorComposicaoPropria(con, cfg, expansor, buscador_materiais)
