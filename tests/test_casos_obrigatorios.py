"""Os sete casos de teste exigidos pelo item 60, contra as bases reais."""
from __future__ import annotations

import pytest

from conftest import precisa_bases
from motor import techspec
from motor.compositions import ExpansorComposicoes
from motor.matching import chave_tecnica, vinculo_e_seguro_como_global


# ---------------------------------------------------------------- Caso 1
@precisa_bases
def test_caso1_alvenaria_bloco_concreto(buscador_servicos, con):
    """Caso 1: alvenaria de bloco de concreto encontra candidatos de alvenaria."""
    servico = con.execute(
        "SELECT * FROM company_services WHERE codigo = '140006'").fetchone()
    assert servico is not None

    candidatos = buscador_servicos.buscar(servico["descricao"], servico["unidade"],
                                          top_n=6)
    assert candidatos, "nenhum candidato para alvenaria"

    # Todo candidato do topo precisa ser de fato alvenaria — não algo que
    # apenas compartilha palavras genéricas com a descrição.
    assert all("ALVENARIA" in c.descricao.upper() for c in candidatos[:4])
    assert all(c.componentes["unidade"] == 1.0 for c in candidatos[:4])
    assert candidatos[0].score >= 0.75


# ---------------------------------------------------------------- Caso 2
@precisa_bases
def test_caso2_espessuras_diferentes_sao_distinguidas():
    """Caso 2: bloco de 9, 14 e 19 cm não são o mesmo serviço (item 11)."""
    b09 = techspec.extrair("ALVENARIA EM BLOCO DE CONCRETO 9CM", "M2")
    b14 = techspec.extrair("ALVENARIA EM BLOCO DE CONCRETO 14CM", "M2")
    b19 = techspec.extrair("ALVENARIA EM BLOCO DE CONCRETO 19CM", "M2")

    assert b09.espessura_cm == 9 and b14.espessura_cm == 14 and b19.espessura_cm == 19

    igual = techspec.comparar(b14, b14)
    diferente = techspec.comparar(b14, b19)
    muito_diferente = techspec.comparar(b09, b19)

    assert igual.score == 1.0
    assert diferente.score < igual.score
    assert muito_diferente.score < diferente.score
    assert any("Espessura divergente" in p for p in diferente.penalidades)


@precisa_bases
def test_caso2_dimensoes_de_porcelanato():
    """60x60 e 90x90 são semanticamente próximos e tecnicamente distintos."""
    c = techspec.comparar(techspec.extrair("PORCELANATO ACETINADO 60X60"),
                          techspec.extrair("PORCELANATO ACETINADO 90X90"))
    assert c.score < 0.55
    assert any("Dimensões divergentes" in p for p in c.penalidades)


def test_caso2_conflitos_tecnicos_reduzem_score():
    """Materiais, classes e ações incompatíveis derrubam o score."""
    casos = [
        ("ALVENARIA BLOCO CONCRETO 14CM", "ALVENARIA BLOCO CERAMICO 14CM"),
        ("EXECUCAO DE ALVENARIA", "DEMOLICAO DE ALVENARIA"),
        ("CONCRETO FCK=25MPA", "CONCRETO FCK=15MPA"),
        ("ACO CA 50 D 10MM", "ACO CA 25 D 10MM"),
        ("TUBO PVC DN 25MM", "TUBO PVC DN 50MM"),
    ]
    for a, b in casos:
        c = techspec.comparar(techspec.extrair(a), techspec.extrair(b))
        assert c.conflito_grave, f"deveria ser conflito grave: {a} x {b}"
        assert c.score < 0.60
        assert c.penalidades


# ---------------------------------------------------------------- Caso 3
@precisa_bases
def test_caso3_material_com_unidade_diferente(buscador_materiais):
    """Caso 3: cimento em Kg na referência x saco na base interna."""
    candidatos = buscador_materiais.buscar("CIMENTO PORTLAND CPII-E/F-32", "Kg",
                                           tipo="MATERIAL", top_n=5)
    assert candidatos
    melhor = candidatos[0]
    assert "CIMENTO" in melhor.descricao.upper()

    # A conversão saco -> kg tem de sair do conteúdo declarado no produto,
    # nunca de uma regra global de 50 kg (item 26).
    conversao = melhor.extra["conversao"]
    if melhor.unidade == "SC":
        assert conversao["ok"]
        assert conversao["metodo"] == "TEXTO_PRODUTO"
        assert conversao["fator"] in (40.0, 50.0, 25.0, 20.0)


@precisa_bases
def test_caso3_coeficiente_convertido_corretamente(montador, con):
    """4,8867 kg de cal, em sacos de 20 kg, dá 0,2443 sacos."""
    comp = montador.montar("140006", "EDIF", "4001071")
    assert comp is not None
    cal = [i for i in comp.itens if i.codins_ref == "10508"]
    assert cal, "a composição deveria conter cal hidratada"
    item = cal[0]
    if item.fator_conversao != 1.0:
        esperado = item.coeficiente_original / item.fator_conversao
        assert item.coeficiente_final == pytest.approx(esperado)
        assert item.custo_item == pytest.approx(
            item.coeficiente_final * (item.preco_interno or 0))


# ---------------------------------------------------------------- Caso 4
@precisa_bases
def test_caso4_composicao_auxiliar_expande_recursivamente(expansor):
    """Caso 4: a auxiliar é aberta e os coeficientes se acumulam (item 21).

    AUX 10580 usa 0,2200 m³ da auxiliar 10630, que consome 486 kg de
    cimento por m³. O consolidado deve trazer 0,2200 x 486 = 106,92 kg.
    """
    comp = expansor.expandir("AUX", "10580")
    assert comp is not None
    assert comp.auxiliares_expandidas >= 1
    assert comp.profundidade >= 1

    cimento = [i for i in comp.consolidado if i.codins == "10517"]
    assert cimento, "cimento deveria aparecer no consolidado"
    assert cimento[0].coeficiente == pytest.approx(0.22 * 486.0)
    assert "AUX 10630" in cimento[0].caminhos[0]

    # A auxiliar não entra no consolidado: quem entra são as folhas dela.
    assert not any(i.codins == "10630" for i in comp.consolidado)


@precisa_bases
def test_caso4_custo_recalculado_bate_com_o_publicado(expansor, con):
    """A expansão é verificada contra o custo publicado em TODA a base."""
    linhas = con.execute(
        "SELECT origem, codigo, custo_total FROM reference_compositions"
        " WHERE custo_total IS NOT NULL AND custo_total > 0").fetchall()
    assert len(linhas) > 3000

    # O custo publicado vem arredondado em 2 casas, e cada Vparc da base
    # também. Numa composição de R$ 0,45 esse arredondamento sozinho já
    # vale ~2% — por isso a tolerância é relativa E absoluta.
    TOLERANCIA_RELATIVA = 0.01
    TOLERANCIA_ABSOLUTA = 0.02      # dois centavos

    dentro, fora = 0, []
    for linha in linhas:
        comp = expansor.expandir(linha["origem"], linha["codigo"])
        diferenca = abs(comp.custo_calculado() - linha["custo_total"])
        erro = diferenca / linha["custo_total"]
        if erro <= TOLERANCIA_RELATIVA or diferenca <= TOLERANCIA_ABSOLUTA:
            dentro += 1
        else:
            fora.append((linha["origem"], linha["codigo"], erro, diferenca,
                         comp.pendencias))

    # 99%+ das composições precisam fechar com o custo publicado.
    assert dentro / len(linhas) >= 0.99, f"apenas {dentro}/{len(linhas)} fecharam"

    # Toda divergência de valor material precisa ter explicação registrada:
    # não pode existir erro silencioso de cálculo.
    for origem, codigo, erro, diferenca, pendencias in fora:
        assert pendencias, (f"{origem} {codigo} divergiu {erro:.2%} "
                            f"(R$ {diferenca:.4f}) sem pendência registrada")

    # E as que divergem de verdade são exatamente as auxiliares percentuais.
    assert all(any(p["tipo"] == "AUXILIAR_PERCENTUAL" for p in pend)
               for *_, pend in fora)


@precisa_bases
def test_caso4_auxiliar_percentual_vira_pendencia(expansor):
    """Auxiliar com unidade '%' não é expansível por multiplicação (item 67)."""
    comp = expansor.expandir("INFRA", "8062000")
    assert comp is not None
    assert any(p["tipo"] == "AUXILIAR_PERCENTUAL" for p in comp.pendencias)


def test_caso4_recursao_tem_guarda_de_ciclo(con):
    """Um ciclo é detectado e vira pendência, sem estouro de pilha."""
    con.execute("INSERT OR REPLACE INTO reference_compositions"
                "(origem, codigo, descricao, unidade, custo_total)"
                " VALUES('AUX','999001','CICLO A','M3', 1.0)")
    con.execute("INSERT OR REPLACE INTO reference_compositions"
                "(origem, codigo, descricao, unidade, custo_total)"
                " VALUES('AUX','999002','CICLO B','M3', 1.0)")
    con.execute("DELETE FROM reference_inputs WHERE codigo IN ('999001','999002')")
    con.execute("INSERT INTO reference_inputs(origem, codigo, seq, codins, descricao,"
                " unidade, coeficiente, classe) VALUES"
                "('AUX','999001',1,'999002','CICLO B','M3',1.0,'COMPOSICAO_AUXILIAR')")
    con.execute("INSERT INTO reference_inputs(origem, codigo, seq, codins, descricao,"
                " unidade, coeficiente, classe) VALUES"
                "('AUX','999002',1,'999001','CICLO A','M3',1.0,'COMPOSICAO_AUXILIAR')")
    con.commit()
    try:
        comp = ExpansorComposicoes(con).expandir("AUX", "999001")
        assert comp is not None
        assert any(p["tipo"] == "CICLO_DE_COMPOSICAO" for p in comp.pendencias)
    finally:
        con.execute("DELETE FROM reference_inputs WHERE codigo IN ('999001','999002')")
        con.execute("DELETE FROM reference_compositions"
                    " WHERE codigo IN ('999001','999002')")
        con.commit()


# ---------------------------------------------------------------- Caso 5
@precisa_bases
def test_caso5_material_sem_correspondente_nao_bloqueia(montador, buscador_materiais):
    """Caso 5: item 39 — os outros insumos são montados assim mesmo."""
    candidatos = buscador_materiais.buscar(
        "INSUMO INEXISTENTE XYZQWK 12345 SEM PAR NA BASE", "KG",
        tipo="MATERIAL", top_n=5)
    assert candidatos == [] or candidatos[0].score < 0.75


@precisa_bases
def test_caso5_composicao_com_pendencia_preserva_os_demais(montador):
    """Uma conversão pendente zera aquele item, não a composição."""
    comp = montador.montar("120006", "INFRA", "8051000")
    assert comp is not None
    pendentes = [i for i in comp.itens if i.pendencia == "CONVERSAO_PENDENTE"]
    resolvidos = [i for i in comp.itens
                  if i.incluido_no_custo and i.custo_item > 0]
    assert pendentes, "esperava ao menos uma conversão pendente neste caso"
    assert resolvidos, "os demais itens deveriam continuar montados"
    assert comp.custo_direto > 0
    assert comp.status()[0] == "PENDENTE"
    # O item pendente não contamina o custo com um número inventado.
    assert all(i.custo_item == 0 for i in pendentes)


# ---------------------------------------------------------------- Caso 6
@precisa_bases
def test_caso6_servico_sem_correspondente(buscador_servicos):
    """Caso 6: sem candidato plausível, não se força um vínculo."""
    candidatos = buscador_servicos.buscar(
        "ZZZQWX SERVICO COMPLETAMENTE INEXISTENTE 998877", "M2", top_n=5)
    assert all(c.score < 0.75 for c in candidatos)


# ---------------------------------------------------------------- Caso 7
@precisa_bases
def test_caso7_mesmo_material_em_muitas_composicoes(expansor, con):
    """Caso 7: o mesmo insumo aparece em dezenas de composições.

    A chave técnica precisa ser estável, para que o vínculo validado uma
    vez seja reaproveitado em todas as demais.
    """
    linhas = con.execute(
        "SELECT origem, codigo FROM reference_inputs WHERE codins = '10517'"
        " LIMIT 40").fetchall()
    assert len(linhas) >= 20, "cimento deveria aparecer em muitas composições"

    chaves = set()
    for linha in linhas:
        comp = expansor.expandir(linha["origem"], linha["codigo"])
        for item in comp.consolidado:
            if item.codins == "10517":
                chaves.add(chave_tecnica(item.descricao, item.unidade))
    assert len(chaves) == 1, "a mesma descrição deve gerar sempre a mesma chave"


def test_caso7_chave_tecnica_separa_variantes():
    """Item 58: o vínculo do bloco de 14 cm não vale para o de 19 cm."""
    k14 = chave_tecnica("BLOCO DE CONCRETO 14 CM", "UN")
    k19 = chave_tecnica("BLOCO DE CONCRETO 19 CM", "UN")
    assert k14 != k19

    # Areia média não tem variante dimensional: pode ser vínculo global.
    seguro, _ = vinculo_e_seguro_como_global("AREIA LAVADA MEDIA", "M3")
    assert seguro

    # Bloco sem dimensão é ambíguo: o vínculo não pode ser global.
    seguro, motivo = vinculo_e_seguro_como_global("BLOCO DE CONCRETO", "UN")
    assert not seguro and motivo
