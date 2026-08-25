"""Leitura das bases, detecção de origem e regra de preço."""
from __future__ import annotations

import shutil

import pytest

from conftest import RAIZ, precisa_bases
from motor import ingest, loaders
from motor.loaders import (
    classificar_escopo,
    classificar_insumo,
    localizar_cabecalho,
    parsear_historico_precos,
    preco_vigente,
)


def test_cabecalho_nao_e_presumido_na_primeira_linha():
    """Item 41: o cabeçalho é procurado, não assumido em A1."""
    linhas = [
        ["SECRETARIA DE INFRAESTRUTURA URBANA E OBRAS", "", ""],
        ["COMPOSIÇÕES DE EDIFICAÇÕES", "", ""],
        ["CÓDIGO", "NOME DO SERVIÇO", "UNID"],
        ["", "", "CODINS"],
    ]
    assert localizar_cabecalho(linhas, ("CODIGO", "NOME DO SERVICO")) == 2
    assert localizar_cabecalho(linhas, ("INEXISTENTE",)) is None


def test_cabecalho_ignora_no_break_space():
    """A base de serviços traz '\\xa0\\xa0UN\\xa0\\xa0' no cabeçalho."""
    linhas = [["Família", "CÓDIGO", "\xa0\xa0UN\xa0\xa0", "DESCRIÇÃO"]]
    assert localizar_cabecalho(linhas, ("CODIGO", "DESCRICAO")) == 0
    colunas = loaders.mapear_colunas(linhas[0], loaders.COLUNAS_SERVICOS)
    assert colunas["unidade"] == 2


@pytest.mark.parametrize("codins,descricao,unidade,esperado", [
    ("2099", "SERVENTE (SGSP)", "H", "MAO_DE_OBRA"),
    ("2020", "PEDREIRO (SGSP)", "H", "MAO_DE_OBRA"),
    ("94001", "BETONEIRA 400 LITROS", "H", "EQUIPAMENTO"),
    ("94531", "CÂMARA NOVA DE PNEU R13 165", "Un", "MATERIAL"),
    ("95021", "CONJUNTO MOTOR BOMBA 1/2 HP", "Un", "MATERIAL"),
    ("10517", "CIMENTO PORTLAND CPII-E/F-32", "Kg", "MATERIAL"),
    ("12580", "TIJOLO MAÇICO DE BARRO COMUM", "Un", "MATERIAL"),
])
def test_classificacao_de_insumo_pela_estrutura(codins, descricao, unidade, esperado):
    """Item 19: a classe vem da faixa do CODINS, não do texto."""
    classe, _ = classificar_insumo(codins, descricao, unidade, set())
    assert classe == esperado


def test_auxiliar_reconhecida_por_estar_na_base_aux():
    """Uma auxiliar é reconhecida por aparecer como CÓDIGO na base AUX."""
    classe, origem = classificar_insumo("10630", "ARGAMASSA DE CIMENTO", "M3",
                                        {"10630"})
    assert classe == "COMPOSICAO_AUXILIAR" and origem == "AUX"
    # Sem a base AUX carregada, o mesmo código seria só um material.
    classe, _ = classificar_insumo("10630", "ARGAMASSA DE CIMENTO", "M3", set())
    assert classe == "MATERIAL"


@pytest.mark.parametrize("descricao,esperado", [
    ("MÃO DE OBRA ESPECIALIZADA PARA INSTALAÇÃO DE DIVISÓRIAS", "MAO_DE_OBRA"),
    ("FORNECIMENTO E INSTALAÇÃO DE DIVISÓRIA EM GESSO DRYWALL", "FORNEC_E_INSTAL"),
    ("FORNECIMENTO E COLOCAÇÃO DE PORTA SANFONADA", "FORNEC_E_INSTAL"),
    ("DEMOLIÇÃO DE ALVENARIA EM GERAL", "DEMOLICAO_REMOCAO"),
    ("LOCAÇÃO DE ANDAIME METÁLICO", "LOCACAO"),
    ("ALVENARIA EM BLOCOS CERÂMICOS", "EXECUCAO_INDEFINIDO"),
])
def test_classificacao_de_escopo(descricao, esperado):
    """A ordem importa: 'MÃO DE OBRA PARA INSTALAÇÃO' é mão de obra."""
    assert classificar_escopo(descricao) == esperado


def test_historico_de_precos():
    texto = ("    R$ 5.84   DATA : 06/03/26 --       R$ 1.00   DATA : 08/07/24 "
             "--       R$ 8.00   DATA : 05/04/24 --  ")
    historico = parsear_historico_precos(texto)
    assert len(historico) == 3
    assert historico[0] == ("2026-03-06", 5.84)
    assert historico[2] == ("2024-04-05", 8.0)


def test_politicas_de_preco():
    """Item 52: o banco fica pronto para as demais políticas."""
    historico = [("2026-03-06", 5.84), ("2024-07-08", 1.0), ("2024-04-05", 8.0)]
    assert preco_vigente(historico, 8.0, "VALOR_APROVADO") == 8.0
    assert preco_vigente(historico, 8.0, "ULTIMO") == 5.84
    assert preco_vigente(historico, 8.0, "MAX") == 8.0
    assert preco_vigente(historico, 8.0, "MEDIANA") == 5.84
    assert preco_vigente(historico, 8.0, "MEDIA_RECENTE") == pytest.approx(4.946667)


@precisa_bases
def test_valor_e_o_maximo_do_historico(con):
    """Regra confirmada na auditoria: VALOR = máximo das cotações, em 100%
    dos registros. É a base da decisão de usá-lo como preço vigente."""
    linhas = con.execute(
        "SELECT m.codigo, m.preco_valor, MAX(p.preco) AS maximo"
        " FROM company_materials m JOIN company_material_prices p"
        "   ON p.codigo = m.codigo GROUP BY m.codigo").fetchall()
    assert len(linhas) > 10000
    divergentes = [l["codigo"] for l in linhas
                   if abs((l["preco_valor"] or 0) - l["maximo"]) > 0.005]
    assert not divergentes, f"{len(divergentes)} registros fora da regra"


@precisa_bases
def test_origem_detectada_pelo_conteudo_e_nao_pelo_nome(tmp_path):
    """Item 4: nomes sem significado, ordem alfabética e tamanho invertidos."""
    bases = tmp_path / "BASES"
    bases.mkdir()
    cfg_real = __import__("motor.config", fromlist=["carregar"]).carregar(RAIZ)
    achados = ingest.descobrir_arquivos(cfg_real)

    disfarces = {"EDIF": "zzz_grande.xls", "INFRA": "aaa_medio.xls",
                 "AUX": "mmm_pequeno.xls"}
    for papel, novo_nome in disfarces.items():
        shutil.copy(achados[papel], bases / novo_nome)

    for papel, novo_nome in disfarces.items():
        caminho = bases / novo_nome
        aba, linhas = loaders.ler_planilha(caminho)
        origem, como = loaders.detectar_origem(aba, linhas, caminho.name)
        assert origem == papel, f"{novo_nome} deveria ser {papel}, veio {origem}"
        assert "conteúdo" in como or "aba" in como


@precisa_bases
def test_importacao_e_idempotente(con, cfg):
    """Reimportar sem mudança não reprocessa e não duplica nada."""
    antes = {
        t: __import__("motor.database", fromlist=["escalar"]).escalar(
            con, f"SELECT COUNT(*) FROM {t}")
        for t in ("company_services", "company_materials",
                  "reference_compositions", "reference_inputs")}
    relatorio = ingest.importar(con, cfg)
    assert relatorio.cargas == []
    assert len(relatorio.ignorados) == 5
    depois = {
        t: __import__("motor.database", fromlist=["escalar"]).escalar(
            con, f"SELECT COUNT(*) FROM {t}")
        for t in antes}
    assert antes == depois


@precisa_bases
def test_contagens_conferem_com_a_auditoria(con):
    from motor.database import escalar
    assert escalar(con, "SELECT COUNT(*) FROM company_services") == 949
    assert escalar(con, "SELECT COUNT(*) FROM company_materials") == 10610
    assert escalar(con, "SELECT COUNT(*) FROM reference_compositions") == 3589
    assert escalar(con, "SELECT COUNT(*) FROM reference_inputs") == 14268
    assert escalar(con, "SELECT COUNT(*) FROM reference_compositions"
                        " WHERE origem='EDIF'") == 2632
    assert escalar(con, "SELECT COUNT(*) FROM reference_compositions"
                        " WHERE origem='INFRA'") == 843
    assert escalar(con, "SELECT COUNT(*) FROM reference_compositions"
                        " WHERE origem='AUX'") == 114


@precisa_bases
def test_codigo_colide_entre_edif_e_infra(con):
    """A razão de a chave ser (origem, codigo): 37 códigos colidem, e em
    100% dos casos designam serviços diferentes."""
    colisoes = con.execute(
        "SELECT e.codigo, e.descricao AS de, i.descricao AS di"
        " FROM reference_compositions e JOIN reference_compositions i"
        "   ON i.codigo = e.codigo AND i.origem = 'INFRA'"
        " WHERE e.origem = 'EDIF'").fetchall()
    assert len(colisoes) == 37
    assert all(l["de"] != l["di"] for l in colisoes)
