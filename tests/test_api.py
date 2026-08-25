"""API local: whitelist de ações e contrato do JSON (itens 48 e 49)."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from conftest import RAIZ, precisa_bases
from motor import api


@pytest.fixture(scope="module")
def ctx():
    contexto = api.Contexto(str(RAIZ))
    yield contexto
    contexto.fechar()


def test_acao_fora_da_whitelist_e_recusada(ctx):
    for nome in ["os.system", "eval", "__import__", "exec", "",
                 "acao_status", "motor.api.acao_status", "../../etc/passwd"]:
        r = api.executar({"acao": nome}, ctx)
        assert r["status"] == "erro"
        assert "não permitida" in r["erro"].lower()
        assert "acoes_disponiveis" in r


def test_whitelist_e_um_dicionario_fechado():
    """Não há despacho dinâmico: a ação vem de um dicionário, não de
    getattr sobre um módulo."""
    assert isinstance(api._ACOES, dict)
    assert all(callable(f) for f in api._ACOES.values())
    for proibido in ("eval", "exec", "system", "import", "open", "subprocess"):
        assert not any(proibido in nome for nome in api._ACOES)


def test_codigo_nao_avalia_string_como_codigo():
    """Varredura defensiva: nenhuma construção que execute texto (item 49).

    `re.compile` e `open(..., "rb")` são leitura, não execução, e por isso
    ficam de fora — a busca é por avaliação de código propriamente dita.
    """
    import re as _re
    padroes = {
        "eval": _re.compile(r"\beval\s*\("),
        "exec": _re.compile(r"\bexec\s*\("),
        "__import__": _re.compile(r"\b__import__\s*\("),
        "compile (de código)": _re.compile(r"(?<!re\.)(?<!\w)compile\s*\("
                                           r"(?!r?[\"'])"),
        "os.system": _re.compile(r"\bos\.system\s*\("),
        "os.popen": _re.compile(r"\bos\.popen\s*\("),
        "subprocess": _re.compile(r"\bsubprocess\b"),
        "pickle.loads de fonte externa": _re.compile(r"\bmarshal\b"),
    }
    for arquivo in sorted((RAIZ / "python" / "motor").glob("*.py")):
        fonte = arquivo.read_text(encoding="utf-8")
        for nome, padrao in padroes.items():
            achados = [m for m in padrao.finditer(fonte)
                       if not _re.match(r"\s*#", fonte[
                           fonte.rfind("\n", 0, m.start()) + 1:m.start()])]
            assert not achados, f"{arquivo.name} usa {nome}"


def test_gravacao_de_arquivo_nao_toca_nas_bases():
    """As bases originais só são abertas em modo de leitura."""
    fonte = (RAIZ / "python" / "motor" / "loaders.py").read_text(encoding="utf-8")
    assert 'open(caminho, "rb")' in fonte          # hash: leitura binária
    assert "read_only=True" in fonte               # openpyxl
    for escrita in ('open(caminho, "w', "'w'", '"w"', '"a"', ".save(", ".write("):
        assert escrita not in fonte, f"loaders.py grava algo: {escrita}"


def test_envelope_status_nao_e_sobrescrito(ctx):
    """Uma ação com 'status' próprio não pode atropelar o ok/erro que o
    VBA testa."""
    r = api.executar({"acao": "registrar_pendencia", "tipo": "TESTE_PYTEST",
                      "codigo_servico": "000000"}, ctx)
    assert r["status"] == "ok"
    assert r["status_pendencia"] == "ABERTA"
    ctx.con.execute("DELETE FROM pending_mappings WHERE tipo='TESTE_PYTEST'")
    ctx.con.commit()


@precisa_bases
def test_status_traz_os_indicadores_da_tela_inicio(ctx):
    r = api.executar({"acao": "status"}, ctx)
    assert r["status"] == "ok"
    ind = r["indicadores"]
    for chave in ("servicos_empresa", "servicos_vinculados", "servicos_pendentes",
                  "composicoes_proprias", "materiais_vinculados",
                  "pendencias_abertas", "materiais_base",
                  "composicoes_referencia"):
        assert chave in ind
    assert ind["servicos_empresa"] == 949
    assert len(r["bases"]) == 5
    # Cada base informa COMO foi identificada.
    assert all(b["detectado_por"] for b in r["bases"] if b["papel"] in
               {"EDIF", "INFRA", "AUX"})


@precisa_bases
def test_buscar_servico_devolve_score_decomposto(ctx):
    r = api.executar({"acao": "buscar_servico", "codigo_empresa": "140010",
                      "top_n": 3}, ctx)
    assert r["status"] == "ok"
    assert r["resultados"]
    primeiro = r["resultados"][0]
    for chave in ("origem", "codigo", "descricao", "score", "score_pct",
                  "componentes", "confianca", "vinculo_validado"):
        assert chave in primeiro
    assert primeiro["vinculo_validado"] is False
    assert r["explicacao"], "a API devolve a explicação pronta para a interface"


@precisa_bases
def test_expandir_composicao_traz_hierarquia_e_consolidado(ctx):
    """Item 22: as duas representações ao mesmo tempo."""
    r = api.executar({"acao": "expandir_composicao", "origem": "AUX",
                      "codigo": "10580"}, ctx)
    assert r["status"] == "ok"
    assert r["arvore"] and r["consolidado"]
    assert r["auxiliares_expandidas"] >= 1
    assert "conferencia_custo" in r
    assert abs(r["conferencia_custo"]["diferenca"]) < 0.05


@precisa_bases
def test_analisar_lote_nao_confirma_nada(ctx):
    """Itens 50 e 51: pré-calcula e prioriza, sem confirmar."""
    r = api.executar({"acao": "analisar_lote", "limite": 12}, ctx)
    assert r["status"] == "ok"
    assert r["fila"]
    assert "resumo" in r
    assert "nenhuma foi confirmada automaticamente" in r["aviso"].lower()
    ordem = {"FORTE": 0, "PROVAVEL": 1, "BAIXA": 2, "MUITO_BAIXA": 3,
             "SEM_CANDIDATO": 4}
    valores = [ordem[f["confianca"]] for f in r["fila"]]
    assert valores == sorted(valores), "a fila vem dos casos fáceis para os difíceis"
    vinculados = ctx.con.execute(
        "SELECT COUNT(*) FROM service_mappings WHERE confirmado=1").fetchone()[0]
    assert vinculados == 0


@precisa_bases
def test_confirmar_servico_valida_as_entradas(ctx):
    r = api.executar({"acao": "confirmar_servico", "codigo_empresa": "000000",
                      "origem": "EDIF", "codigo_referencia": "4001071"}, ctx)
    assert r["status"] == "erro" and "não existe" in r["erro"]

    r = api.executar({"acao": "confirmar_servico", "codigo_empresa": "140006",
                      "origem": "EDIF", "codigo_referencia": "000000"}, ctx)
    assert r["status"] == "erro" and "não existe" in r["erro"]


@precisa_bases
def test_ponte_por_arquivo_como_o_vba_usa(tmp_path):
    """Modo de invocação real do VBA: pedido e resposta em arquivo UTF-8."""
    pedido = tmp_path / "pedido.json"
    resposta = tmp_path / "resposta.json"
    pedido.write_text(json.dumps({"acao": "status"}, ensure_ascii=False),
                      encoding="utf-8")
    processo = subprocess.run(
        [sys.executable, str(RAIZ / "python" / "main.py"),
         "--pedido", str(pedido), "--resposta", str(resposta),
         "--raiz", str(RAIZ)],
        capture_output=True, text=True, timeout=180)
    assert processo.returncode == 0, processo.stderr
    dados = json.loads(resposta.read_text(encoding="utf-8"))
    assert dados["status"] == "ok"
    assert dados["indicadores"]["servicos_empresa"] == 949


def test_cli_recusa_acao_invalida_com_codigo_de_saida(tmp_path):
    resposta = tmp_path / "r.json"
    processo = subprocess.run(
        [sys.executable, str(RAIZ / "python" / "main.py"),
         "--json", json.dumps({"acao": "rm -rf"}),
         "--resposta", str(resposta), "--raiz", str(RAIZ)],
        capture_output=True, text=True, timeout=120)
    assert processo.returncode == 1
    assert json.loads(resposta.read_text(encoding="utf-8"))["status"] == "erro"


def test_listar_acoes():
    acoes = api.acoes_disponiveis()
    esperadas = {"status", "atualizar_bases", "listar_servicos", "buscar_servico",
                 "ver_composicao", "confirmar_servico", "buscar_material",
                 "confirmar_material", "buscar_equipamento",
                 "confirmar_equipamento", "expandir_composicao",
                 "salvar_composicao", "listar_pendencias", "listar_composicoes"}
    assert esperadas <= set(acoes), f"faltam: {esperadas - set(acoes)}"
