"""Conversão de unidades (itens 25 a 27)."""
from __future__ import annotations

import pytest

from motor import units
from motor.normalize import normalizar_unidade, para_numero


@pytest.mark.parametrize("bruta,esperada", [
    ("M2", "M2"), ("M²", "M2"), ("m 2", "M2"), ("MT2", "M2"),
    ("M3", "M3"), ("M³", "M3"), ("m³", "M3"),
    ("\xa0\xa0UN\xa0\xa0", "UN"), ("Un", "UN"), ("und", "UN"),
    ("t", "TON"), ("TN", "TON"), ("Ton", "TON"),
    ("%", "PCT"), ("vb", "VB"), ("SC", "SC"), ("saco", "SC"),
])
def test_canonicalizacao_de_unidade(bruta, esperada):
    assert normalizar_unidade(bruta) == esperada


def test_dd_e_diaria_e_nao_duzia():
    """Nestas bases DD é DIÁRIA: a família DIÁRIAS usa DD e 152 dos 187
    materiais em DD são locação. A referência escreve DÚZIA por extenso."""
    assert normalizar_unidade("DD") == "DIA"
    assert normalizar_unidade("MS") == "MES"
    assert normalizar_unidade("DÚZIA") == "DZ"


@pytest.mark.parametrize("valor,esperado", [
    ("R$ 1.234,56", 1234.56), ("R$ 16,00", 16.0), ("5.84", 5.84),
    ("1,5", 1.5), ("0.0098", 0.0098), ("", None), (None, None),
])
def test_parse_de_numero_pt_br(valor, esperado):
    assert para_numero(valor) == esperado


@pytest.mark.parametrize("origem,destino,fator", [
    ("T", "KG", 1000.0), ("KG", "TON", 0.001),
    ("M3", "L", 1000.0), ("CM", "M", 0.01),
    ("MIL", "UN", 1000.0), ("DZ", "UN", 12.0),
])
def test_conversao_dimensional_determinista(origem, destino, fator):
    c = units.converter(origem, destino)
    assert c.ok
    assert c.fator == pytest.approx(fator)
    assert c.metodo in {"DIMENSIONAL", "CONTAGEM"}


def test_embalagem_sem_produto_vira_pendencia():
    """Item 26: 1 saco = 50 kg NÃO vale para todo produto."""
    c = units.converter("SC", "KG")
    assert not c.ok
    assert c.pendencia == "CONVERSAO_PENDENTE"


@pytest.mark.parametrize("descricao,fator", [
    ("Cimento Portland CP-II E32 50kgs NBR11578", 50.0),
    ("Cimento Portland CP-V E32 40kgs NBR5733", 40.0),
    ("Cal Hidratado CH-III 20kgs NBR7175", 20.0),
])
def test_embalagem_com_conteudo_declarado(descricao, fator):
    c = units.converter("SC", "KG", descricao_produto=descricao)
    assert c.ok
    assert c.fator == pytest.approx(fator)
    assert c.metodo == "TEXTO_PRODUTO"


def test_regra_cadastrada_tem_prioridade():
    c = units.converter("SC", "KG", descricao_produto="Cimento 50kg",
                        regra_produto=25.0, origem_regra="cadastro")
    assert c.ok and c.fator == 25.0 and c.metodo == "REGRA_PRODUTO"


@pytest.mark.parametrize("descricao,area", [
    ("PORCELANATO ACETINADO 60X60 CM", 0.36),
    ("PISO CERAMICO 0,45 X 0,45 M", 0.2025),
    ("PORCELANATO 90X90", 0.81),
])
def test_conversao_dimensional_de_peca_para_m2(descricao, area):
    """Item 27: peça -> m² usa largura x comprimento, em código."""
    c = units.converter("UN", "M2", descricao_produto=descricao)
    assert c.ok
    assert c.fator == pytest.approx(area)


def test_periodo_de_locacao_nao_converte_para_hora():
    """Quantas horas produtivas há numa diária é decisão da empresa."""
    c = units.converter("DIA", "H")
    assert not c.ok
    assert c.pendencia == "CONVERSAO_PENDENTE"
    assert "locação" in c.justificativa.lower()


def test_ambiguidade_vira_pendencia_e_nao_chute():
    """'Aço CA 50 Ø10mm x 12,00m' tem dois comprimentos candidatos.
    Escolher um seria adivinhar."""
    c = units.converter("BR", "M",
                        descricao_produto="ACO CA 50 D 10,0MM X 12,00M NBR7480")
    assert not c.ok
    assert c.pendencia == "CONVERSAO_PENDENTE"


def test_unidades_incompativeis():
    assert not units.converter("H", "KG").ok
    assert not units.converter("VB", "KG").ok
    assert not units.converter("M3XKM", "M3").ok


def test_compatibilidade_para_score():
    assert units.compativel("M2", "M²") == 1.0
    assert units.compativel("KG", "TON") == pytest.approx(0.85)
    assert units.compativel("H", "M2") == 0.0
