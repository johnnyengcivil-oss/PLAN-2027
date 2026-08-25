"""Regras da composição própria: dupla contagem, custeio e rastreabilidade."""
from __future__ import annotations

import pytest

from conftest import precisa_bases
from motor.config import politica_para


@precisa_bases
def test_mao_de_obra_interna_entra_com_coeficiente_um(montador):
    """Item 17."""
    comp = montador.montar("140006", "EDIF", "4001071")
    interna = [i for i in comp.itens
               if i.tipo == "MAO_DE_OBRA" and i.codigo_interno == "140006"]
    assert len(interna) == 1
    item = interna[0]
    assert item.coeficiente_final == 1.0
    assert item.custo_item == pytest.approx(1.0 * (item.preco_interno or 0))


@precisa_bases
def test_mao_de_obra_referencial_nao_e_somada_mas_e_preservada(montador):
    """Item 18: não incorporar ao custo, sem perder a informação."""
    comp = montador.montar("140006", "EDIF", "4001071")
    referencial = [i for i in comp.itens
                   if i.tipo == "MAO_DE_OBRA" and i.codins_ref]
    assert referencial, "a referência tem pedreiro e servente"
    for item in referencial:
        assert item.incluido_no_custo == 0
        assert item.custo_item == 0.0
        assert "dupla contagem" in item.motivo_exclusao.lower()
        # Preservado para rastreabilidade.
        assert item.descricao_ref and item.coeficiente_original > 0

    soma_mao_de_obra = comp.custo_mao_obra
    interna = next(i for i in comp.itens if i.codigo_interno == "140006")
    assert soma_mao_de_obra == pytest.approx(interna.custo_item)


@precisa_bases
def test_escopo_fornecimento_e_instalacao_nao_importa_materiais(montador, cfg):
    """O achado que motivou a política: 144 serviços já embutem material."""
    politica = politica_para(cfg, "FORNEC_E_INSTAL")
    assert politica["importar_materiais"] is False

    comp = montador.montar("140017", "EDIF", "4003052")
    assert comp.escopo_servico == "FORNEC_E_INSTAL"
    materiais = [i for i in comp.itens if i.tipo == "MATERIAL"]
    assert materiais, "o material da referência deve continuar registrado"
    for item in materiais:
        assert item.incluido_no_custo == 0
        assert item.pendencia == "ESCOPO_SOBREPOSTO"
    assert comp.custo_materiais == 0.0
    assert any(p["tipo"] == "ESCOPO_SOBREPOSTO" for p in comp.pendencias)


@precisa_bases
def test_custo_direto_e_a_soma_dos_incluidos(montador):
    """Item 30: matemática determinística, sem IA."""
    comp = montador.montar("140006", "EDIF", "4001071")
    esperado = sum(i.custo_item for i in comp.itens if i.incluido_no_custo)
    assert comp.custo_direto == pytest.approx(esperado)
    assert comp.custo_direto == pytest.approx(
        comp.custo_mao_obra + comp.custo_materiais + comp.custo_equipamentos)
    for item in comp.itens:
        if item.incluido_no_custo and not item.pendencia:
            assert item.custo_item == pytest.approx(
                item.coeficiente_final * (item.preco_interno or 0))


@precisa_bases
def test_rastreabilidade_completa_de_cada_item(montador):
    """Item 31: os dois lados, a conversão, o score e a origem."""
    comp = montador.montar("140006", "EDIF", "4001071")
    materiais = [i for i in comp.itens
                 if i.tipo == "MATERIAL" and i.codigo_interno]
    assert materiais
    for item in materiais:
        assert item.codigo_interno and item.descricao_interna and item.unidade_interna
        assert item.codins_ref and item.descricao_ref and item.unidade_ref
        assert item.coeficiente_original is not None
        assert item.fator_conversao > 0
        assert item.metodo_conversao
        assert item.coeficiente_final >= 0
        assert item.score is not None
        assert item.detalhe_score
    # E o caminho de expansão quando o insumo veio de uma auxiliar.
    de_auxiliar = [i for i in materiais if "AUX" in (i.caminho_expansao or "")]
    assert de_auxiliar, "esta composição usa argamassa auxiliar"


@precisa_bases
def test_status_completa_exige_tudo_resolvido(montador):
    """Item 59."""
    completa = montador.montar("140006", "EDIF", "4001071")
    assert completa.status()[0] == "COMPLETA"

    pendente = montador.montar("120006", "INFRA", "8051000")
    estado, motivo = pendente.status()
    assert estado == "PENDENTE" and motivo


@precisa_bases
def test_salvar_grava_composicao_vinculos_e_pendencias(montador, con):
    """A gravação é o que transforma escolha em conhecimento da empresa."""
    comp = montador.montar("1110006", "EDIF", "11080006")
    codigo = montador.salvar(comp, usuario="pytest")
    try:
        assert codigo.startswith("CP-")
        gravada = con.execute(
            "SELECT * FROM own_compositions WHERE codigo = ?", (codigo,)).fetchone()
        assert gravada is not None
        assert gravada["custo_direto"] == pytest.approx(comp.custo_direto)
        # Versionamento da referência (item 55).
        assert gravada["data_base_ref"] == "JAN/2026"
        assert gravada["arquivo_referencia"]
        assert gravada["hash_ref"]

        itens = con.execute(
            "SELECT * FROM own_composition_items WHERE codigo_composicao = ?"
            " ORDER BY seq", (codigo,)).fetchall()
        assert len(itens) == len(comp.itens)

        vinculos = con.execute(
            "SELECT * FROM material_mappings WHERE status='ATUAL'"
            " AND confirmado=1").fetchall()
        assert vinculos, "os materiais escolhidos viram vínculos validados"
        for v in vinculos:
            assert v["chave_tecnica"]
            assert v["escopo_vinculo"] in {"GLOBAL", "COMPOSICAO"}
    finally:
        con.execute("DELETE FROM own_compositions WHERE codigo = ?", (codigo,))
        con.execute("DELETE FROM material_mappings WHERE usuario = 'pytest'")
        con.execute("DELETE FROM pending_mappings WHERE usuario = 'pytest'")
        con.commit()


@precisa_bases
def test_atualizar_bases_preserva_conhecimento(con, cfg):
    """Item 53: reimportar não pode apagar o que a empresa construiu."""
    from motor import ingest
    from motor.database import escalar
    from motor.own import confirmar_servico

    confirmar_servico(con, codigo_empresa="140006", origem="EDIF",
                      codigo_referencia="4001071", score=0.9,
                      detalhe="teste", usuario="pytest")
    con.execute(
        "INSERT OR REPLACE INTO conversion_rules(escopo, chave, unidade_origem,"
        " unidade_destino, fator, justificativa, data, usuario)"
        " VALUES('MATERIAL','738','SC','KG',50,'teste','2026-01-01','pytest')")
    con.commit()
    try:
        ingest.importar(con, cfg, forcar=True)
        assert escalar(con, "SELECT COUNT(*) FROM service_mappings"
                            " WHERE usuario='pytest'") == 1
        assert escalar(con, "SELECT COUNT(*) FROM conversion_rules"
                            " WHERE usuario='pytest'") == 1
        # E os dados de origem foram de fato recarregados.
        assert escalar(con, "SELECT COUNT(*) FROM company_services") == 949
    finally:
        con.execute("DELETE FROM service_mappings WHERE usuario='pytest'")
        con.execute("DELETE FROM conversion_rules WHERE usuario='pytest'")
        con.commit()


@precisa_bases
def test_alterar_vinculo_preserva_historico(con):
    """Item 57: trocar a decisão não apaga a anterior."""
    from motor.own import confirmar_servico
    try:
        confirmar_servico(con, codigo_empresa="140006", origem="EDIF",
                          codigo_referencia="4001070", score=0.8,
                          detalhe="primeira", usuario="pytest")
        confirmar_servico(con, codigo_empresa="140006", origem="EDIF",
                          codigo_referencia="4001071", score=0.9,
                          detalhe="segunda", usuario="pytest")
        linhas = con.execute(
            "SELECT * FROM service_mappings WHERE codigo_empresa='140006'"
            " ORDER BY id", ()).fetchall()
        assert len(linhas) == 2
        assert linhas[0]["status"] == "SUBSTITUIDO"
        assert linhas[0]["codigo_referencia"] == "4001070"
        assert linhas[0]["substituido_por"] == linhas[1]["id"]
        assert linhas[1]["status"] == "ATUAL"
        assert linhas[1]["codigo_referencia"] == "4001071"
    finally:
        con.execute("DELETE FROM service_mappings WHERE usuario='pytest'")
        con.commit()
