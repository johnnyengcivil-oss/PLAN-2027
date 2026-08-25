"""Score explicável, penalizações e reaproveitamento de vínculos."""
from __future__ import annotations

import pytest

from conftest import precisa_bases
from motor import techspec
from motor.matching import (
    IndiceRaridade,
    TETO_CONFLITO_GRAVE,
    classificar_confianca,
    pontuar,
    similaridade_textual,
)

PESOS = {"textual": 0.26, "semantico": 0.18, "cobertura": 0.18,
         "unidade": 0.16, "tecnico": 0.22}
FAIXAS = {"forte": 0.90, "provavel": 0.75, "baixa": 0.50}


def test_score_e_decomposto_em_componentes():
    """Item 12: o score precisa ser explicável, não um número opaco."""
    score, componentes, _ = pontuar(
        "ALVENARIA DE BLOCO DE CONCRETO 14 CM", "M2",
        "ALVENARIA DE BLOCO DE CONCRETO 14 CM", "M2",
        pesos=PESOS, faixas=FAIXAS, sim_semantica=1.0, cobertura=1.0)
    assert set(componentes) == {"textual", "semantico", "unidade",
                                "tecnico", "cobertura"}
    assert all(0.0 <= v <= 1.0 for v in componentes.values())
    assert score == pytest.approx(1.0)


def test_conflito_grave_limita_o_score():
    """Item 11: por mais parecida que seja a frase, conflito técnico grave
    não pode chegar a 'forte candidato'."""
    score, _, comparacao = pontuar(
        "ALVENARIA DE BLOCO DE CONCRETO 14 CM", "M2",
        "ALVENARIA DE BLOCO CERAMICO 14 CM", "M2",
        pesos=PESOS, faixas=FAIXAS, sim_semantica=1.0, cobertura=1.0)
    assert comparacao.conflito_grave
    assert score <= TETO_CONFLITO_GRAVE
    assert classificar_confianca(score, FAIXAS) in {"BAIXA", "MUITO_BAIXA"}


def test_unidade_incompativel_derruba_o_score():
    score_igual, _, _ = pontuar("PINTURA LATEX", "M2", "PINTURA LATEX", "M2",
                                pesos=PESOS, faixas=FAIXAS, sim_semantica=1.0,
                                cobertura=1.0)
    score_diferente, _, _ = pontuar("PINTURA LATEX", "M2", "PINTURA LATEX", "H",
                                    pesos=PESOS, faixas=FAIXAS,
                                    sim_semantica=1.0, cobertura=1.0)
    assert score_diferente < score_igual


@pytest.mark.parametrize("score,esperado", [
    (0.97, "FORTE"), (0.90, "FORTE"), (0.82, "PROVAVEL"),
    (0.75, "PROVAVEL"), (0.60, "BAIXA"), (0.30, "MUITO_BAIXA"),
])
def test_faixas_de_confianca(score, esperado):
    """Item 35 — e nenhuma delas implica confirmação automática."""
    assert classificar_confianca(score, FAIXAS) == esperado


def test_similaridade_textual_normaliza_acento_e_caixa():
    assert similaridade_textual("ALVENARIA", "alvenaria") == 1.0
    assert similaridade_textual("DEMOLIÇÃO", "DEMOLICAO") == 1.0
    assert similaridade_textual("ALVENARIA", "") == 0.0


def test_termo_nucleo_e_o_primeiro_significativo():
    """O que identifica o item é o substantivo que encabeça a descrição.
    O termo mais RARO seria o qualificador acidental."""
    indice = IndiceRaridade([
        "CHAPISCO COM ARGAMASSA DE CIMENTO E AREIA",
        "REBOCO INTERNO ARGAMASSA PRE-FABRICADA",
        "RECOLOCACAO DE PLACAS DE PISO ELEVADO EM AREA INTERNA OU EXTERNA",
        "ALVENARIA EM BLOCO CERAMICO COMUM",
    ])
    assert indice.determinante("CHAPISCO (PAREDES INTERNAS / EXTERNAS)") == "CHAPISCO"
    assert indice.determinante("REBOCO - ARGAMASSA ÚNICA") == "REBOCO"
    # Verbo de escopo inicial é pulado: o que identifica é o objeto.
    assert indice.determinante(
        "FORNECIMENTO E INSTALAÇÃO DE DIVISÓRIA") == "DIVISORIA"


def test_cobertura_de_termos():
    indice = IndiceRaridade(["CHAPISCO COM ARGAMASSA", "REBOCO INTERNO",
                             "PISO ELEVADO AREA INTERNA OU EXTERNA"])
    completa = indice.cobertura("CHAPISCO COM ARGAMASSA", "CHAPISCO COM ARGAMASSA")
    nenhuma = indice.cobertura("CHAPISCO", "REBOCO INTERNO")
    assert completa == pytest.approx(1.0)
    assert nenhuma < 0.2


@precisa_bases
def test_chapisco_nao_casa_com_piso_elevado(buscador_servicos, con):
    """Caso real que motivou o termo-núcleo: 'CHAPISCO (PAREDES INTERNAS /
    EXTERNAS)' casava melhor com 'PISO ELEVADO EM ÁREA INTERNA OU EXTERNA'
    do que com as composições de chapisco."""
    servico = con.execute(
        "SELECT * FROM company_services WHERE codigo = '1110002'").fetchone()
    candidatos = buscador_servicos.buscar(servico["descricao"],
                                          servico["unidade"], top_n=5)
    assert candidatos
    assert "CHAPISCO" in candidatos[0].descricao.upper()
    assert not any("PISO ELEVADO" in c.descricao.upper() for c in candidatos[:3])


@precisa_bases
def test_correspondencia_exata_chega_a_100(buscador_servicos, con):
    servico = con.execute(
        "SELECT * FROM company_services WHERE codigo = '140010'").fetchone()
    candidatos = buscador_servicos.buscar(servico["descricao"],
                                          servico["unidade"], top_n=3)
    assert candidatos[0].score == pytest.approx(1.0)
    assert candidatos[0].confianca == "FORTE"


@precisa_bases
def test_busca_cobre_edif_e_infra_simultaneamente(buscador_servicos):
    """Item 9: as duas bases são pesquisadas ao mesmo tempo."""
    candidatos = buscador_servicos.buscar("DEMOLIÇÃO DE ALVENARIA", "M3",
                                          top_n=20)
    origens = {c.origem for c in candidatos}
    assert "EDIF" in origens and "INFRA" in origens
    # Auxiliares não são serviços de contrato e ficam fora.
    assert "AUX" not in origens


@precisa_bases
def test_vinculo_validado_tem_prioridade_e_e_sinalizado(
        buscador_servicos, con, cfg):
    """Itens 15, 33 e 34: o vínculo confirmado sobe ao topo e é distinguido
    de uma sugestão automática."""
    from motor.own import confirmar_servico
    codigo = "140006"
    consulta = "ALVENARIA EM BLOCOS CERÂMICOS OU CONCRETO"
    antes = buscador_servicos.buscar(consulta, "M2", top_n=5,
                                     codigo_empresa=codigo)
    assert len(antes) >= 3
    # Escolhe deliberadamente um candidato que NÃO é o mais bem pontuado,
    # para provar que é a confirmação humana que manda, não o score.
    escolhido = (antes[-1].origem, antes[-1].codigo)
    assert (antes[0].origem, antes[0].codigo) != escolhido

    try:
        confirmar_servico(con, codigo_empresa=codigo, origem=escolhido[0],
                          codigo_referencia=escolhido[1], score=0.76,
                          detalhe="teste", usuario="pytest")
        depois = buscador_servicos.buscar(consulta, "M2", top_n=5,
                                          codigo_empresa=codigo)
        assert (depois[0].origem, depois[0].codigo) == escolhido
        assert depois[0].tipo_origem == "VINCULO_VALIDADO"
        assert depois[0].confianca == "VALIDADO"
        assert depois[0].to_dict()["vinculo_validado"] is True
        # As sugestões automáticas continuam marcadas como tal.
        assert all(c.tipo_origem == "SUGESTAO_AUTOMATICA" for c in depois[1:])
    finally:
        con.execute("DELETE FROM service_mappings WHERE codigo_empresa = ?",
                    (codigo,))
        con.commit()


@precisa_bases
def test_pesquisa_manual_com_filtros(buscador_servicos):
    """Item 36."""
    resultados = buscador_servicos.pesquisa_manual(
        "bloco concreto", origens=("EDIF",), unidade="M2", limite=20)
    assert resultados
    assert all(r["origem"] == "EDIF" for r in resultados)
    assert all(r["unidade"] == "M2" for r in resultados)


@precisa_bases
def test_equipamento_busca_apenas_familias_de_equipamento(buscador_materiais):
    """Item 28 — e a arquitetura fica pronta para uma base separada."""
    candidatos = buscador_materiais.buscar("BETONEIRA 400 LITROS", "H",
                                           tipo="EQUIPAMENTO", top_n=5)
    assert candidatos
    assert all(c.extra["tipo_item"] == "EQUIPAMENTO" for c in candidatos)
    assert "BETONEIRA" in candidatos[0].descricao.upper()


@precisa_bases
def test_indice_semantico_e_persistido(cfg, semantico, buscador_servicos):
    """Item 43: o índice é salvo e não recalculado a cada pesquisa."""
    arquivos = list(cfg.pasta_cache.glob("*.pkl"))
    assert arquivos, "o índice deveria ter sido gravado em disco"
    assert semantico.tem_indice(buscador_servicos.NOME_INDICE)


def test_sistema_funciona_sem_camada_semantica(cfg, con, tmp_path):
    """Item 44: sem LLM e sem embeddings, o matching continua funcionando."""
    from motor.matching import BuscadorServicos
    from motor.semantic import MotorSemantico
    desligado = MotorSemantico(tmp_path, backend="off")
    assert desligado.similaridades("qualquer", "consulta") == {}
    buscador = BuscadorServicos(con, cfg, desligado)
    buscador.carregar()
    candidatos = buscador.buscar("DEMOLIÇÃO DE ALVENARIA EM GERAL", "M3", top_n=3)
    assert candidatos
    assert candidatos[0].componentes["semantico"] == 0.0
    assert candidatos[0].score > 0.5
