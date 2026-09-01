"""API local JSON (itens 48 e 49).

O VBA envia um JSON com uma AÇÃO e parâmetros; recebe um JSON de volta.
As ações são uma WHITELIST fechada: `_ACOES` mapeia nome -> função. Um
nome fora do dicionário é recusado. Não existe nenhum caminho que avalie
string como código — nada de eval, exec, import dinâmico ou nome de
função vindo do payload sendo resolvido por getattr sobre um módulo.
"""
from __future__ import annotations

import sqlite3
import traceback
from datetime import datetime
from typing import Any, Callable

from . import config as configmod
from . import database, ingest, units
from .compositions import ExpansorComposicoes
from .matching import BuscadorMateriais, BuscadorServicos
from .normalize import normalizar_unidade
from .own import (
    MontadorComposicaoPropria,
    confirmar_servico,
    preco_desatualizado,
)
from .semantic import MotorSemantico

VERSAO_API = "1.0.0"


class Contexto:
    """Recursos compartilhados entre chamadas, criados sob demanda."""

    def __init__(self, raiz: str | None = None) -> None:
        self.cfg = configmod.carregar(raiz)
        self.con: sqlite3.Connection = database.conectar(self.cfg.caminho_db)
        self.semantico = MotorSemantico(
            self.cfg.pasta_cache, self.cfg.backend_semantico,
            self.cfg.modelo_embeddings)
        self.servicos = BuscadorServicos(self.con, self.cfg, self.semantico)
        self.materiais = BuscadorMateriais(self.con, self.cfg, self.semantico)
        self.expansor = ExpansorComposicoes(self.con)
        self.montador = MontadorComposicaoPropria(
            self.con, self.cfg, self.expansor, self.materiais)

    @property
    def usuario(self) -> str:
        return self.cfg.usuario_efetivo()

    def fechar(self) -> None:
        try:
            self.con.close()
        except sqlite3.Error:
            pass


def _texto(p: dict[str, Any], chave: str, padrao: str = "") -> str:
    valor = p.get(chave, padrao)
    return "" if valor is None else str(valor).strip()


def _inteiro(p: dict[str, Any], chave: str, padrao: int) -> int:
    try:
        return int(p.get(chave, padrao))
    except (TypeError, ValueError):
        return padrao


def _sem_colisao_status(dados: dict[str, Any]) -> dict[str, Any]:
    """Move o 'status' do domínio para 'status_composicao'.

    A chave 'status' do JSON de resposta pertence ao envelope da API
    (ok/erro); o status da composição (COMPLETA/PENDENTE/...) viaja em
    chave própria para os dois não se atropelarem.
    """
    if "status" in dados:
        dados["status_composicao"] = dados.pop("status")
    return dados


def _origens(p: dict[str, Any], padrao: tuple[str, ...] = ("EDIF", "INFRA")) -> list[str]:
    bruto = p.get("origens") or p.get("origem") or ""
    if isinstance(bruto, str):
        bruto = bruto.replace(";", ",")
        itens = [b.strip().upper() for b in bruto.split(",") if b.strip()]
    else:
        itens = [str(b).strip().upper() for b in bruto]
    if not itens or "AMBOS" in itens or "TODOS" in itens:
        return list(padrao)
    return [i for i in itens if i in {"EDIF", "INFRA", "AUX"}] or list(padrao)


# ====================================================================== ações

def acao_status(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Indicadores da tela INÍCIO (item 8)."""
    con = ctx.con
    def n(sql: str, params: tuple = ()) -> int:
        return int(database.escalar(con, sql, params) or 0)

    total_servicos = n("SELECT COUNT(*) FROM company_services")
    vinculados = n("SELECT COUNT(DISTINCT codigo_empresa) FROM service_mappings"
                   " WHERE status='ATUAL' AND confirmado=1")
    fontes = [dict(r) for r in con.execute(
        "SELECT papel, nome_arquivo, data_base, data_importacao, registros,"
        " detectado_por, hash_sha256 FROM source_files ORDER BY papel")]
    return {
        "versao_api": VERSAO_API,
        "backend_semantico": ctx.semantico.descricao_backend(),
        "usuario": ctx.usuario,
        "banco": str(ctx.cfg.caminho_db.name),
        "indicadores": {
            "servicos_empresa": total_servicos,
            "servicos_vinculados": vinculados,
            "servicos_pendentes": max(0, total_servicos - vinculados),
            "composicoes_proprias": n("SELECT COUNT(*) FROM own_compositions"),
            "composicoes_completas": n("SELECT COUNT(*) FROM own_compositions"
                                       " WHERE status='COMPLETA'"),
            "composicoes_pendentes": n("SELECT COUNT(*) FROM own_compositions"
                                       " WHERE status='PENDENTE'"),
            "composicoes_revisar": n("SELECT COUNT(*) FROM own_compositions"
                                     " WHERE status='REVISAR'"),
            "materiais_vinculados": n("SELECT COUNT(*) FROM material_mappings"
                                      " WHERE status='ATUAL' AND confirmado=1"
                                      " AND tipo='MATERIAL'"),
            "equipamentos_vinculados": n("SELECT COUNT(*) FROM material_mappings"
                                         " WHERE status='ATUAL' AND confirmado=1"
                                         " AND tipo='EQUIPAMENTO'"),
            "pendencias_abertas": n("SELECT COUNT(*) FROM pending_mappings"
                                    " WHERE status='ABERTA'"),
            "materiais_base": n("SELECT COUNT(*) FROM company_materials"),
            "composicoes_referencia": n("SELECT COUNT(*) FROM reference_compositions"),
        },
        "bases": fontes,
    }


def acao_atualizar_bases(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Relê as bases sem perder o conhecimento acumulado (item 53)."""
    relatorio = ingest.importar(ctx.con, ctx.cfg,
                                forcar=bool(p.get("forcar")))
    ctx.servicos = BuscadorServicos(ctx.con, ctx.cfg, ctx.semantico)
    ctx.materiais = BuscadorMateriais(ctx.con, ctx.cfg, ctx.semantico)
    ctx.expansor = ExpansorComposicoes(ctx.con)
    ctx.montador = MontadorComposicaoPropria(
        ctx.con, ctx.cfg, ctx.expansor, ctx.materiais)
    return relatorio.to_dict()


def acao_listar_servicos(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Lista os serviços internos, com filtros e situação do vínculo."""
    sql = ("SELECT s.*, m.origem AS ref_origem, m.codigo_referencia AS ref_codigo,"
           " m.score_original AS ref_score, o.codigo AS composicao_propria,"
           " o.status AS status_composicao"
           " FROM company_services s"
           " LEFT JOIN service_mappings m ON m.codigo_empresa = s.codigo"
           "   AND m.status='ATUAL' AND m.confirmado=1"
           " LEFT JOIN own_compositions o ON o.codigo_servico = s.codigo"
           " WHERE 1=1")
    params: list[Any] = []
    if _texto(p, "familia"):
        sql += " AND s.familia = ?"
        params.append(_texto(p, "familia"))
    if _texto(p, "unidade"):
        sql += " AND s.unidade = ?"
        params.append(normalizar_unidade(_texto(p, "unidade")))
    if _texto(p, "escopo"):
        sql += " AND s.escopo = ?"
        params.append(_texto(p, "escopo"))
    if p.get("somente_aprovados"):
        sql += " AND s.preco_aprovado = 1"
    situacao = _texto(p, "situacao").upper()
    if situacao == "PENDENTES":
        sql += " AND m.codigo_empresa IS NULL"
    elif situacao == "VINCULADOS":
        sql += " AND m.codigo_empresa IS NOT NULL"
    for palavra in _texto(p, "termo").upper().split():
        sql += " AND s.descricao_norm LIKE ?"
        params.append(f"%{palavra}%")
    sql += " ORDER BY s.familia, s.codigo LIMIT ?"
    params.append(_inteiro(p, "limite", 500))
    linhas = [dict(r) for r in ctx.con.execute(sql, tuple(params))]
    return {"total": len(linhas), "servicos": linhas}


def acao_listar_familias(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    return {
        "servicos": [dict(r) for r in ctx.con.execute(
            "SELECT familia, COUNT(*) AS total FROM company_services"
            " GROUP BY familia ORDER BY familia")],
        "materiais": [dict(r) for r in ctx.con.execute(
            "SELECT familia, tipo_item, COUNT(*) AS total FROM company_materials"
            " GROUP BY familia, tipo_item ORDER BY familia")],
    }


def acao_buscar_servico(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Busca candidatos EDIF/INFRA para um serviço interno (itens 9 e 13)."""
    codigo = _texto(p, "codigo_empresa")
    descricao = _texto(p, "descricao")
    unidade = _texto(p, "unidade")
    servico = None
    if codigo:
        servico = ctx.con.execute(
            "SELECT * FROM company_services WHERE codigo = ?", (codigo,)).fetchone()
        if servico is None and not descricao:
            return {"erro": f"Serviço interno {codigo} não encontrado."}
        if servico is not None:
            descricao = descricao or servico["descricao"]
            unidade = unidade or servico["unidade"]
    if not descricao:
        return {"erro": "Informe 'codigo_empresa' ou 'descricao'."}

    candidatos = ctx.servicos.buscar(
        descricao, unidade, origens=_origens(p),
        top_n=_inteiro(p, "top_n", ctx.cfg.top_n_padrao),
        codigo_empresa=codigo)
    return {
        "servico": dict(servico) if servico is not None else
                   {"descricao": descricao, "unidade": unidade},
        "total": len(candidatos),
        "resultados": [c.to_dict() for c in candidatos],
        "explicacao": [c.explicacao() for c in candidatos],
    }


def acao_pesquisa_manual(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Pesquisa livre nas bases de referência ou interna (item 36)."""
    alvo = _texto(p, "alvo", "REFERENCIA").upper()
    termo = _texto(p, "termo")
    limite = _inteiro(p, "limite", 50)
    if alvo in {"MATERIAL", "MATERIAIS", "EQUIPAMENTO", "INTERNA", "EMPRESA"}:
        tipo = "EQUIPAMENTO" if alvo == "EQUIPAMENTO" else _texto(p, "tipo")
        return {"resultados": ctx.materiais.pesquisa_manual(
            termo, tipo=tipo, familia=_texto(p, "familia"),
            unidade=_texto(p, "unidade"), limite=limite)}
    return {"resultados": ctx.servicos.pesquisa_manual(
        termo, origens=_origens(p, ("EDIF", "INFRA", "AUX")),
        unidade=_texto(p, "unidade"), limite=limite)}


def acao_ver_composicao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Abre a composição analítica da referência (item 16)."""
    origem = _texto(p, "origem").upper()
    codigo = _texto(p, "codigo")
    if not origem or not codigo:
        return {"erro": "Informe 'origem' e 'codigo'."}
    expandida = ctx.expansor.expandir(origem, codigo)
    if expandida is None:
        return {"erro": f"Composição {origem} {codigo} não encontrada."}
    return expandida.to_dict(incluir_arvore=bool(p.get("incluir_arvore", True)))


def acao_expandir_composicao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Expansão recursiva explícita, com hierárquico e consolidado (itens 21 e 22)."""
    resposta = acao_ver_composicao(ctx, {**p, "incluir_arvore": True})
    if "erro" in resposta:
        return resposta
    resposta["conferencia_custo"] = {
        "custo_publicado": resposta["custo_total_base"],
        "custo_recalculado": resposta["custo_calculado"],
        "diferenca": (round((resposta["custo_calculado"] or 0)
                            - (resposta["custo_total_base"] or 0), 4)),
    }
    return resposta


def acao_confirmar_servico(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Grava o vínculo serviço -> referência escolhido pelo usuário (item 14)."""
    codigo = _texto(p, "codigo_empresa")
    origem = _texto(p, "origem").upper()
    referencia = _texto(p, "codigo_referencia")
    if not (codigo and origem and referencia):
        return {"erro": "Informe 'codigo_empresa', 'origem' e 'codigo_referencia'."}
    if ctx.con.execute("SELECT 1 FROM company_services WHERE codigo = ?",
                       (codigo,)).fetchone() is None:
        return {"erro": f"Serviço interno {codigo} não existe."}
    if ctx.con.execute("SELECT 1 FROM reference_compositions"
                       " WHERE origem = ? AND codigo = ?",
                       (origem, referencia)).fetchone() is None:
        return {"erro": f"Referência {origem} {referencia} não existe."}
    score = p.get("score")
    novo = confirmar_servico(
        ctx.con, codigo_empresa=codigo, origem=origem,
        codigo_referencia=referencia,
        score=float(score) if isinstance(score, (int, float)) else None,
        detalhe=_texto(p, "detalhe"), usuario=ctx.usuario,
        observacao=_texto(p, "observacao"))
    return {"id": novo, "codigo_empresa": codigo,
            "origem": origem, "codigo_referencia": referencia,
            "confirmado": True}


def acao_buscar_material(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Candidatos internos para um insumo da referência (item 23)."""
    descricao = _texto(p, "descricao")
    if not descricao and _texto(p, "codins"):
        linha = ctx.con.execute(
            "SELECT descricao, unidade_orig FROM reference_inputs"
            " WHERE codins = ? LIMIT 1", (_texto(p, "codins"),)).fetchone()
        if linha is not None:
            descricao = linha["descricao"]
            p = {**p, "unidade": p.get("unidade") or linha["unidade_orig"]}
    if not descricao:
        return {"erro": "Informe 'descricao' ou 'codins'."}
    tipo = _texto(p, "tipo", "MATERIAL").upper()
    candidatos = ctx.materiais.buscar(
        descricao, _texto(p, "unidade"), tipo=tipo,
        top_n=_inteiro(p, "top_n", ctx.cfg.top_n_padrao),
        familia=_texto(p, "familia"))
    return {"consulta": {"descricao": descricao, "unidade": _texto(p, "unidade"),
                         "tipo": tipo},
            "total": len(candidatos),
            "resultados": [c.to_dict() for c in candidatos],
            "explicacao": [c.explicacao() for c in candidatos]}


def acao_buscar_equipamento(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Mesma lógica de material, restrita às famílias de equipamento (item 28)."""
    return acao_buscar_material(ctx, {**p, "tipo": "EQUIPAMENTO"})


def _confirmar_insumo(ctx: Contexto, p: dict[str, Any], tipo: str) -> dict[str, Any]:
    from .matching import chave_tecnica, vinculo_e_seguro_como_global
    codins = _texto(p, "codins")
    codigo_empresa = _texto(p, "codigo_empresa")
    descricao_ref = _texto(p, "descricao_ref")
    if not (codins and codigo_empresa):
        return {"erro": "Informe 'codins' e 'codigo_empresa'."}
    interno = ctx.con.execute(
        "SELECT codigo, descricao, unidade FROM company_materials WHERE codigo = ?",
        (codigo_empresa,)).fetchone()
    if interno is None:
        return {"erro": f"Item interno {codigo_empresa} não existe."}
    if not descricao_ref:
        linha = ctx.con.execute(
            "SELECT descricao, unidade_orig FROM reference_inputs"
            " WHERE codins = ? LIMIT 1", (codins,)).fetchone()
        if linha is not None:
            descricao_ref = linha["descricao"]
            p = {**p, "unidade_ref": p.get("unidade_ref") or linha["unidade_orig"]}
    unidade_ref = _texto(p, "unidade_ref")

    seguro, motivo = vinculo_e_seguro_como_global(descricao_ref, unidade_ref)
    escopo = "GLOBAL" if seguro and not _texto(p, "codigo_composicao") else "COMPOSICAO"
    fator = p.get("fator_conversao")
    if not isinstance(fator, (int, float)) or fator <= 0:
        conv = units.converter(interno["unidade"], unidade_ref,
                               descricao_produto=interno["descricao"])
        fator = conv.fator if conv.ok else 1.0
        metodo = conv.metodo if conv.ok else ""
    else:
        fator, metodo = float(fator), "REGRA_USUARIO"

    agora = datetime.now().isoformat(timespec="seconds")
    ctx.con.execute(
        "UPDATE material_mappings SET status='SUBSTITUIDO'"
        " WHERE codins = ? AND tipo = ? AND status='ATUAL' AND escopo_vinculo = ?",
        (codins, tipo, escopo))
    cur = ctx.con.execute(
        "INSERT INTO material_mappings(tipo, origem, codins, descricao_ref,"
        " unidade_ref, chave_tecnica, codigo_empresa, score_original, detalhe_score,"
        " fator_conversao, metodo_conversao, escopo_vinculo, codigo_composicao,"
        " confirmado, status, data, usuario, observacao)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,'ATUAL',?,?,?)",
        (tipo, _texto(p, "origem").upper(), codins, descricao_ref, unidade_ref,
         chave_tecnica(descricao_ref, unidade_ref), codigo_empresa,
         p.get("score") if isinstance(p.get("score"), (int, float)) else None,
         _texto(p, "detalhe"), fator, metodo, escopo,
         _texto(p, "codigo_composicao"), agora, ctx.usuario, motivo))
    database.registrar_log(ctx.con, usuario=ctx.usuario,
                           acao=f"CONFIRMAR_{tipo}", entidade="material_mappings",
                           chave=f"{codins}->{codigo_empresa}",
                           detalhe=f"escopo={escopo} fator={fator:g}")
    ctx.con.commit()
    return {"id": int(cur.lastrowid or 0), "codins": codins,
            "codigo_empresa": codigo_empresa, "escopo_vinculo": escopo,
            "fator_conversao": fator, "metodo_conversao": metodo,
            "observacao": motivo, "confirmado": True}


def acao_confirmar_material(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    return _confirmar_insumo(ctx, p, "MATERIAL")


def acao_confirmar_equipamento(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    return _confirmar_insumo(ctx, p, "EQUIPAMENTO")


def acao_montar_composicao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Monta a composição própria SEM gravar — para revisão do usuário."""
    codigo_servico = _texto(p, "codigo_empresa") or _texto(p, "codigo_servico")
    origem = _texto(p, "origem").upper()
    referencia = _texto(p, "codigo_referencia")
    if not codigo_servico:
        return {"erro": "Informe 'codigo_empresa'."}
    if not (origem and referencia):
        linha = ctx.con.execute(
            "SELECT origem, codigo_referencia FROM service_mappings"
            " WHERE codigo_empresa = ? AND status='ATUAL' AND confirmado=1",
            (codigo_servico,)).fetchone()
        if linha is None:
            return {"erro": ("Serviço sem vínculo confirmado. Informe 'origem' e "
                             "'codigo_referencia' ou confirme o vínculo antes.")}
        origem, referencia = linha["origem"], linha["codigo_referencia"]
    comp = ctx.montador.montar(
        codigo_servico, origem, referencia,
        top_sugestoes=_inteiro(p, "top_sugestoes", 5),
        auto_vincular=bool(p.get("auto_vincular", True)))
    if comp is None:
        return {"erro": f"Não foi possível montar {codigo_servico} "
                        f"com {origem} {referencia}."}
    return _sem_colisao_status(comp.to_dict())


def acao_salvar_composicao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Grava a composição própria após validação humana (itens 14 e 29).

    `itens` permite ao VBA devolver as escolhas do usuário, substituindo
    as sugestões automáticas item a item.
    """
    resposta = acao_montar_composicao(ctx, p)
    if "erro" in resposta:
        return resposta
    codigo_servico = _texto(p, "codigo_empresa") or _texto(p, "codigo_servico")
    comp = ctx.montador.montar(
        codigo_servico, resposta["origem_referencia"],
        resposta["codigo_referencia"],
        top_sugestoes=1, auto_vincular=bool(p.get("auto_vincular", True)))
    if comp is None:
        return {"erro": "Falha ao remontar a composição para gravação."}

    _aplicar_escolhas(ctx, comp, p.get("itens"))

    codigo = ctx.montador.salvar(comp, usuario=ctx.usuario)
    saida = _sem_colisao_status(comp.to_dict())
    saida["codigo"] = codigo
    return saida


def _aplicar_escolhas(ctx: Contexto, comp, escolhas: Any) -> None:
    """Aplica ao objeto montado as decisões que o usuário tomou na tela.

    Cada escolha pode trocar o item interno, fixar o coeficiente final, ou
    as duas coisas. O cálculo continua sendo feito aqui, em código
    determinístico — a tela só informa o que o usuário decidiu.
    """
    if not isinstance(escolhas, list):
        return
    for escolha in escolhas:
        if not isinstance(escolha, dict):
            continue
        codins = str(escolha.get("codins_ref") or escolha.get("codins") or "")
        if not codins:
            continue
        alvo = next((i for i in comp.itens if i.codins_ref == codins), None)
        if alvo is None:
            continue

        codigo_interno = str(escolha.get("codigo_interno") or "")
        if codigo_interno and codigo_interno != alvo.codigo_interno:
            interno = ctx.con.execute(
                "SELECT codigo, descricao, unidade, unidade_orig, preco"
                " FROM company_materials WHERE codigo = ?",
                (codigo_interno,)).fetchone()
            if interno is not None:
                conv = units.converter(
                    interno["unidade"], alvo.unidade_ref,
                    descricao_produto=interno["descricao"],
                    regra_produto=(escolha.get("fator_conversao")
                                   if isinstance(escolha.get("fator_conversao"),
                                                 (int, float)) else None))
                ctx.montador.aplicar_vinculo(alvo, {
                    "codigo": interno["codigo"], "descricao": interno["descricao"],
                    "unidade": interno["unidade"],
                    "unidade_orig": interno["unidade_orig"],
                    "preco": interno["preco"],
                    "score": escolha.get("score"),
                    "confianca": "ESCOLHA_MANUAL",
                    "vinculo_validado": False,
                    "conversao": {"ok": conv.ok, "fator": conv.fator,
                                  "metodo": conv.metodo or "REGRA_USUARIO",
                                  "justificativa": conv.justificativa,
                                  "pendencia": conv.pendencia},
                }, alvo.coeficiente_original or 0.0)

        # Coeficiente digitado manda sobre o calculado — é decisão do
        # engenheiro sobre o consumo real da empresa.
        novo_coef = escolha.get("coeficiente_final")
        if isinstance(novo_coef, (int, float)) and novo_coef >= 0:
            alvo.coeficiente_final = float(novo_coef)
            alvo.custo_item = alvo.coeficiente_final * (alvo.preco_interno or 0.0)
            if alvo.pendencia == "CONVERSAO_PENDENTE":
                alvo.pendencia = ""
                alvo.metodo_conversao = "COEFICIENTE_MANUAL"
                alvo.justificativa_conv = (
                    "Coeficiente informado diretamente pelo usuário, "
                    "dispensando a conversão automática de unidade.")

        if escolha.get("excluir"):
            alvo.incluido_no_custo = 0
            alvo.custo_item = 0.0
            alvo.motivo_exclusao = str(
                escolha.get("motivo_exclusao")
                or "Excluído pelo usuário na revisão da composição.")


def acao_recalcular_composicao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Remonta a composição aplicando as edições, sem gravar nada.

    É o que permite a tela mostrar o custo mudando enquanto o usuário
    digita um coeficiente, mantendo a matemática no Python.
    """
    resposta = acao_montar_composicao(ctx, p)
    if "erro" in resposta:
        return resposta
    codigo_servico = _texto(p, "codigo_empresa") or _texto(p, "codigo_servico")
    comp = ctx.montador.montar(
        codigo_servico, resposta["origem_referencia"],
        resposta["codigo_referencia"], top_sugestoes=1,
        auto_vincular=bool(p.get("auto_vincular", True)))
    if comp is None:
        return {"erro": "Não foi possível remontar a composição."}
    _aplicar_escolhas(ctx, comp, p.get("itens"))
    return _sem_colisao_status(comp.to_dict())


def acao_listar_composicoes(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Aba BANCO_COMPOSIÇÕES (item 37)."""
    sql = ("SELECT o.*,"
           " (SELECT COUNT(*) FROM own_composition_items i"
           "   WHERE i.codigo_composicao = o.codigo AND i.tipo='MATERIAL'"
           "     AND i.incluido_no_custo=1) AS qtd_materiais,"
           " (SELECT COUNT(*) FROM own_composition_items i"
           "   WHERE i.codigo_composicao = o.codigo AND i.tipo='EQUIPAMENTO'"
           "     AND i.incluido_no_custo=1) AS qtd_equipamentos"
           " FROM own_compositions o WHERE 1=1")
    params: list[Any] = []
    if _texto(p, "status"):
        sql += " AND o.status = ?"
        params.append(_texto(p, "status").upper())
    if _texto(p, "codigo_servico"):
        sql += " AND o.codigo_servico = ?"
        params.append(_texto(p, "codigo_servico"))
    sql += " ORDER BY o.codigo LIMIT ?"
    params.append(_inteiro(p, "limite", 500))
    linhas = [dict(r) for r in ctx.con.execute(sql, tuple(params))]
    if _texto(p, "codigo"):
        codigo = _texto(p, "codigo")
        itens = [dict(r) for r in ctx.con.execute(
            "SELECT * FROM own_composition_items WHERE codigo_composicao = ?"
            " ORDER BY seq", (codigo,))]
        return {"total": len(linhas), "composicoes": linhas, "itens": itens}
    return {"total": len(linhas), "composicoes": linhas}


def acao_listar_pendencias(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Central de pendências (item 38)."""
    sql = "SELECT * FROM pending_mappings WHERE status = ?"
    params: list[Any] = [_texto(p, "status", "ABERTA").upper()]
    if _texto(p, "tipo"):
        sql += " AND tipo = ?"
        params.append(_texto(p, "tipo").upper())
    if _texto(p, "codigo_composicao"):
        sql += " AND codigo_composicao = ?"
        params.append(_texto(p, "codigo_composicao"))
    sql += " ORDER BY prioridade, tipo, id LIMIT ?"
    params.append(_inteiro(p, "limite", 500))
    linhas = [dict(r) for r in ctx.con.execute(sql, tuple(params))]
    resumo = [dict(r) for r in ctx.con.execute(
        "SELECT tipo, COUNT(*) AS total FROM pending_mappings"
        " WHERE status='ABERTA' GROUP BY tipo ORDER BY total DESC")]
    return {"total": len(linhas), "pendencias": linhas, "resumo": resumo}


def acao_resolver_pendencia(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    ident = _inteiro(p, "id", 0)
    if not ident:
        return {"erro": "Informe 'id'."}
    novo = _texto(p, "novo_status", "RESOLVIDA").upper()
    if novo not in {"RESOLVIDA", "IGNORADA", "ABERTA"}:
        return {"erro": "novo_status deve ser RESOLVIDA, IGNORADA ou ABERTA."}
    ctx.con.execute(
        "UPDATE pending_mappings SET status = ?, data_resolucao = ?, usuario = ?"
        " WHERE id = ?",
        (novo, datetime.now().isoformat(timespec="seconds"), ctx.usuario, ident))
    ctx.con.commit()
    return {"id": ident, "status_pendencia": novo}


def acao_registrar_pendencia(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Registra uma pendência aberta explicitamente pelo usuário (item 38).

    Usada, entre outros, pelo botão NENHUM CORRESPONDE: registrar que um
    serviço não tem equivalente é informação útil, não ausência de dado.
    """
    tipo = _texto(p, "tipo").upper()
    if not tipo:
        return {"erro": "Informe 'tipo'."}
    cur = ctx.con.execute(
        "INSERT INTO pending_mappings(tipo, codigo_servico, codigo_composicao,"
        " origem, codigo_referencia, codins, descricao, detalhe, prioridade,"
        " status, data, usuario) VALUES(?,?,?,?,?,?,?,?,?,'ABERTA',?,?)",
        (tipo, _texto(p, "codigo_servico"), _texto(p, "codigo_composicao"),
         _texto(p, "origem").upper(), _texto(p, "codigo_referencia"),
         _texto(p, "codins"), _texto(p, "descricao"), _texto(p, "detalhe"),
         _inteiro(p, "prioridade", 5),
         datetime.now().isoformat(timespec="seconds"), ctx.usuario))
    database.registrar_log(ctx.con, usuario=ctx.usuario, acao="REGISTRAR_PENDENCIA",
                           entidade="pending_mappings", chave=tipo,
                           detalhe=_texto(p, "codigo_servico"))
    ctx.con.commit()
    return {"id": int(cur.lastrowid or 0), "tipo": tipo, "status_pendencia": "ABERTA"}


def acao_cadastrar_conversao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Cadastra conversão dependente do produto (itens 26 e 27)."""
    origem_un = normalizar_unidade(_texto(p, "unidade_origem"))
    destino_un = normalizar_unidade(_texto(p, "unidade_destino"))
    try:
        fator = float(p.get("fator"))
    except (TypeError, ValueError):
        return {"erro": "Informe 'fator' numérico."}
    if not (origem_un and destino_un) or fator <= 0:
        return {"erro": "Informe 'unidade_origem', 'unidade_destino' e 'fator' > 0."}
    escopo = _texto(p, "escopo", "MATERIAL").upper()
    if escopo not in {"MATERIAL", "FAMILIA", "GLOBAL"}:
        return {"erro": "escopo deve ser MATERIAL, FAMILIA ou GLOBAL."}
    chave = _texto(p, "chave")
    ctx.con.execute(
        "INSERT INTO conversion_rules(escopo, chave, unidade_origem, unidade_destino,"
        " fator, justificativa, data, usuario) VALUES(?,?,?,?,?,?,?,?)"
        " ON CONFLICT(escopo, chave, unidade_origem, unidade_destino) DO UPDATE SET"
        "  fator=excluded.fator, justificativa=excluded.justificativa,"
        "  data=excluded.data, usuario=excluded.usuario",
        (escopo, chave, origem_un, destino_un, fator, _texto(p, "justificativa"),
         datetime.now().isoformat(timespec="seconds"), ctx.usuario))
    database.registrar_log(ctx.con, usuario=ctx.usuario, acao="CADASTRAR_CONVERSAO",
                           entidade="conversion_rules", chave=f"{chave}:{origem_un}>{destino_un}",
                           detalhe=f"fator={fator:g}")
    ctx.con.commit()
    return {"escopo": escopo, "chave": chave, "unidade_origem": origem_un,
            "unidade_destino": destino_un, "fator": fator}


def acao_analisar_lote(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Pré-calcula sugestões para a fila de validação (itens 50 e 51).

    NÃO confirma nada. Devolve a fila já priorizada: os casos fáceis
    primeiro, porque são os que o usuário valida mais rápido.
    """
    limite = _inteiro(p, "limite", 100)
    sql = ("SELECT s.* FROM company_services s"
           " LEFT JOIN service_mappings m ON m.codigo_empresa = s.codigo"
           "   AND m.status='ATUAL' AND m.confirmado=1"
           " WHERE m.codigo_empresa IS NULL")
    params: list[Any] = []
    if _texto(p, "familia"):
        sql += " AND s.familia = ?"
        params.append(_texto(p, "familia"))
    if p.get("somente_aprovados"):
        sql += " AND s.preco_aprovado = 1"
    sql += " ORDER BY s.familia, s.codigo LIMIT ?"
    params.append(limite)

    fila: list[dict[str, Any]] = []
    for servico in ctx.con.execute(sql, tuple(params)):
        candidatos = ctx.servicos.buscar(
            servico["descricao"], servico["unidade"],
            origens=_origens(p), top_n=_inteiro(p, "top_n", 5))
        melhor = candidatos[0] if candidatos else None
        fila.append({
            "codigo_empresa": servico["codigo"],
            "familia": servico["familia"],
            "unidade": servico["unidade_orig"],
            "descricao": servico["descricao"],
            "escopo": servico["escopo"],
            "melhor_score": round(melhor.score, 4) if melhor else 0.0,
            "confianca": melhor.confianca if melhor else "SEM_CANDIDATO",
            "sugestoes": [c.to_dict() for c in candidatos],
        })
    ordem = {"FORTE": 0, "PROVAVEL": 1, "BAIXA": 2, "MUITO_BAIXA": 3,
             "SEM_CANDIDATO": 4}
    fila.sort(key=lambda f: (ordem.get(f["confianca"], 9), -f["melhor_score"]))
    resumo: dict[str, int] = {}
    for f in fila:
        resumo[f["confianca"]] = resumo.get(f["confianca"], 0) + 1
    return {"total": len(fila), "resumo": resumo, "fila": fila,
            "aviso": "Sugestões pré-calculadas. Nenhuma foi confirmada "
                     "automaticamente — cada uma exige validação do usuário."}


def acao_historico_vinculos(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Histórico de vínculos, inclusive substituídos (item 57)."""
    codigo = _texto(p, "codigo_empresa")
    codins = _texto(p, "codins")
    servicos = [dict(r) for r in ctx.con.execute(
        "SELECT * FROM service_mappings WHERE (? = '' OR codigo_empresa = ?)"
        " ORDER BY codigo_empresa, id DESC LIMIT ?",
        (codigo, codigo, _inteiro(p, "limite", 200)))]
    materiais = [dict(r) for r in ctx.con.execute(
        "SELECT * FROM material_mappings WHERE (? = '' OR codins = ?)"
        " ORDER BY codins, id DESC LIMIT ?",
        (codins, codins, _inteiro(p, "limite", 200)))]
    return {"servicos": servicos, "materiais": materiais}


def acao_alterar_vinculo_material(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Troca um vínculo de material preservando o anterior (item 57)."""
    return _confirmar_insumo(ctx, p, _texto(p, "tipo", "MATERIAL").upper())


def acao_ver_log(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    linhas = [dict(r) for r in ctx.con.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
        (_inteiro(p, "limite", 200),))]
    return {"total": len(linhas), "log": linhas}


def acao_configuracao(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Lê ou grava a configuração (aba CONFIGURAÇÃO)."""
    if p.get("salvar"):
        dados = p.get("config") or {}
        if isinstance(dados, dict):
            for campo in ("arquivo_servicos", "arquivo_materiais", "arquivo_edif",
                          "arquivo_infra", "arquivo_auxiliares",
                          "politica_preco_material", "backend_semantico", "usuario"):
                if isinstance(dados.get(campo), str):
                    setattr(ctx.cfg, campo, dados[campo])
            if isinstance(dados.get("origem_forcada"), dict):
                ctx.cfg.origem_forcada.update(
                    {str(k): str(v) for k, v in dados["origem_forcada"].items()})
            if isinstance(dados.get("politica_escopo"), dict):
                for esc, regra in dados["politica_escopo"].items():
                    if isinstance(regra, dict):
                        ctx.cfg.politica_escopo.setdefault(esc, {}).update(regra)
            for campo in ("pesos_servico", "pesos_material", "faixas_confianca"):
                if isinstance(dados.get(campo), dict):
                    getattr(ctx.cfg, campo).update(
                        {k: float(v) for k, v in dados[campo].items()
                         if isinstance(v, (int, float))})
            ctx.cfg.salvar()
            database.registrar_log(ctx.con, usuario=ctx.usuario,
                                   acao="SALVAR_CONFIGURACAO", entidade="config.json")
            ctx.con.commit()
    return {"config": ctx.cfg.to_dict(),
            "raiz": str(ctx.cfg.raiz),
            "pasta_bases": str(ctx.cfg.pasta_bases),
            "arquivos_detectados": {
                papel: caminho.name for papel, caminho
                in ingest.descobrir_arquivos(ctx.cfg, ctx.con).items()},
            "backend_semantico": ctx.semantico.descricao_backend()}


def acao_ver_material(ctx: Contexto, p: dict[str, Any]) -> dict[str, Any]:
    """Ficha de um material interno, com histórico de preços (item 52)."""
    codigo = _texto(p, "codigo")
    linha = ctx.con.execute(
        "SELECT * FROM company_materials WHERE codigo = ?", (codigo,)).fetchone()
    if linha is None:
        return {"erro": f"Material {codigo} não encontrado."}
    historico = [dict(r) for r in ctx.con.execute(
        "SELECT ordem, data, preco FROM company_material_prices"
        " WHERE codigo = ? ORDER BY ordem", (codigo,))]
    dados = dict(linha)
    dados["historico"] = historico
    dados["preco_desatualizado"] = preco_desatualizado(
        linha["data_ultimo"], ctx.cfg.meses_preco_desatualizado)
    return dados


# ------------------------------------------------------------- WHITELIST

_ACOES: dict[str, Callable[[Contexto, dict[str, Any]], dict[str, Any]]] = {
    "status": acao_status,
    "atualizar_bases": acao_atualizar_bases,
    "listar_servicos": acao_listar_servicos,
    "listar_familias": acao_listar_familias,
    "buscar_servico": acao_buscar_servico,
    "pesquisa_manual": acao_pesquisa_manual,
    "ver_composicao": acao_ver_composicao,
    "expandir_composicao": acao_expandir_composicao,
    "confirmar_servico": acao_confirmar_servico,
    "buscar_material": acao_buscar_material,
    "buscar_equipamento": acao_buscar_equipamento,
    "confirmar_material": acao_confirmar_material,
    "confirmar_equipamento": acao_confirmar_equipamento,
    "alterar_vinculo_material": acao_alterar_vinculo_material,
    "montar_composicao": acao_montar_composicao,
    "salvar_composicao": acao_salvar_composicao,
    "recalcular_composicao": acao_recalcular_composicao,
    "listar_composicoes": acao_listar_composicoes,
    "listar_pendencias": acao_listar_pendencias,
    "resolver_pendencia": acao_resolver_pendencia,
    "registrar_pendencia": acao_registrar_pendencia,
    "cadastrar_conversao": acao_cadastrar_conversao,
    "analisar_lote": acao_analisar_lote,
    "historico_vinculos": acao_historico_vinculos,
    "ver_material": acao_ver_material,
    "ver_log": acao_ver_log,
    "configuracao": acao_configuracao,
}


def acoes_disponiveis() -> list[str]:
    return sorted(_ACOES)


def executar(pedido: dict[str, Any], ctx: Contexto | None = None) -> dict[str, Any]:
    """Executa uma ação da whitelist.

    Nome desconhecido é recusado — não há despacho dinâmico por getattr,
    eval, exec ou import a partir do payload (item 49).
    """
    proprio = ctx is None
    nome = str(pedido.get("acao", "")).strip().lower()
    if nome not in _ACOES:
        return {"status": "erro",
                "erro": f"Ação não permitida: {nome!r}.",
                "acoes_disponiveis": acoes_disponiveis()}
    try:
        if ctx is None:
            ctx = Contexto(pedido.get("raiz"))
        resultado = _ACOES[nome](ctx, pedido)
        # O envelope é a autoridade sobre "status": uma ação que devolvesse
        # essa chave sobrescreveria o "ok"/"erro" que o VBA testa. Ações com
        # status próprio expõem-no sob nome distinto (ex.: status_composicao).
        if isinstance(resultado, dict) and "erro" in resultado:
            return {**resultado, "status": "erro", "acao": nome}
        return {**resultado, "status": "ok", "acao": nome}
    except Exception as exc:                             # noqa: BLE001
        return {"status": "erro", "acao": nome, "erro": str(exc),
                "traceback": traceback.format_exc(limit=6)}
    finally:
        if proprio and ctx is not None:
            ctx.fechar()
