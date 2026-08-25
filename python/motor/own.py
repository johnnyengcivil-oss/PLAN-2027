"""Montagem da composição própria da empresa (itens 17 a 19, 29 a 31, 39, 59).

Princípio central (item 17): o serviço interno JÁ representa a execução, e
entra com coeficiente 1,0000 por unidade. A composição de referência serve
para descobrir QUAIS materiais e equipamentos são consumidos, e em que
quantidade — não para trazer de volta a mão de obra (item 18), que
duplicaria o custo.

A mão de obra referencial não é descartada: é gravada com
`incluido_no_custo = 0` e o motivo, preservando a rastreabilidade.

Uma composição nunca é bloqueada por um insumo problemático (item 39):
os demais são montados normalmente e o item aberto vira pendência.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from . import units
from .compositions import ComposicaoExpandida, ExpansorComposicoes
from .config import Config, politica_para
from .database import registrar_log
from .matching import (
    BuscadorMateriais,
    chave_tecnica,
    vinculo_e_seguro_como_global,
)

MOTIVO_MAO_DE_OBRA_REFERENCIAL = (
    "Mão de obra da composição referencial. Não incorporada ao custo: o "
    "serviço interno já representa a execução completa (evita dupla contagem)."
)


@dataclass
class ItemProprio:
    """Uma linha da composição própria, com rastreabilidade completa (item 31)."""

    seq: int
    tipo: str
    codigo_interno: str = ""
    descricao_interna: str = ""
    unidade_interna: str = ""
    preco_interno: float | None = None
    origem_ref: str = ""
    codins_ref: str = ""
    descricao_ref: str = ""
    unidade_ref: str = ""
    coeficiente_original: float | None = None
    caminho_expansao: str = ""
    fator_conversao: float = 1.0
    metodo_conversao: str = ""
    justificativa_conv: str = ""
    coeficiente_final: float = 0.0
    custo_item: float = 0.0
    score: float | None = None
    detalhe_score: str = ""
    incluido_no_custo: int = 1
    motivo_exclusao: str = ""
    pendencia: str = ""
    sugestoes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "tipo": self.tipo,
            "codigo_interno": self.codigo_interno,
            "descricao_interna": self.descricao_interna,
            "unidade_interna": self.unidade_interna,
            "preco_interno": self.preco_interno,
            "origem_ref": self.origem_ref,
            "codins_ref": self.codins_ref,
            "descricao_ref": self.descricao_ref,
            "unidade_ref": self.unidade_ref,
            "coeficiente_original": self.coeficiente_original,
            "caminho_expansao": self.caminho_expansao,
            "fator_conversao": self.fator_conversao,
            "metodo_conversao": self.metodo_conversao,
            "justificativa_conv": self.justificativa_conv,
            "coeficiente_final": round(self.coeficiente_final, 8),
            "custo_item": round(self.custo_item, 4),
            "score": self.score,
            "detalhe_score": self.detalhe_score,
            "incluido_no_custo": bool(self.incluido_no_custo),
            "motivo_exclusao": self.motivo_exclusao,
            "pendencia": self.pendencia,
            "sugestoes": self.sugestoes,
        }


@dataclass
class ComposicaoPropria:
    """Composição própria montada, ainda NÃO gravada como definitiva."""

    codigo_servico: str
    descricao: str
    unidade: str
    escopo_servico: str
    origem_referencia: str = ""
    codigo_referencia: str = ""
    descricao_referencia: str = ""
    data_base_ref: str = ""
    arquivo_referencia: str = ""
    hash_ref: str = ""
    itens: list[ItemProprio] = field(default_factory=list)
    pendencias: list[dict[str, str]] = field(default_factory=list)
    codigo: str = ""
    politica_aplicada: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------- custos
    def custo_por_tipo(self, tipo: str) -> float:
        return sum(i.custo_item for i in self.itens
                   if i.tipo == tipo and i.incluido_no_custo)

    @property
    def custo_mao_obra(self) -> float:
        return self.custo_por_tipo("MAO_DE_OBRA")

    @property
    def custo_materiais(self) -> float:
        return self.custo_por_tipo("MATERIAL")

    @property
    def custo_equipamentos(self) -> float:
        return self.custo_por_tipo("EQUIPAMENTO")

    @property
    def custo_direto(self) -> float:
        """Custo direto = mão de obra + materiais + equipamentos (item 30)."""
        return self.custo_mao_obra + self.custo_materiais + self.custo_equipamentos

    # ------------------------------------------------------------- status
    def status(self) -> tuple[str, str]:
        """Classifica o status conforme os critérios do item 59."""
        if not self.codigo_referencia:
            return "PENDENTE", "Referência EDIF/INFRA ainda não escolhida."
        abertas = [p for p in self.pendencias if p.get("tipo")]
        sem_vinculo = [i for i in self.itens
                       if i.tipo in {"MATERIAL", "EQUIPAMENTO"}
                       and not i.codigo_interno and i.incluido_no_custo]
        conversoes = [i for i in self.itens if i.pendencia == "CONVERSAO_PENDENTE"]
        if sem_vinculo:
            return "PENDENTE", (f"{len(sem_vinculo)} insumo(s) sem correspondente "
                                f"na base interna.")
        if conversoes:
            return "PENDENTE", f"{len(conversoes)} conversão(ões) de unidade não resolvida(s)."
        if abertas:
            return "PENDENTE", f"{len(abertas)} pendência(s) em aberto."
        if not any(i.tipo == "MAO_DE_OBRA" and i.incluido_no_custo for i in self.itens):
            return "PENDENTE", "Mão de obra interna não definida."
        return "COMPLETA", ""

    def to_dict(self) -> dict[str, Any]:
        status, motivo = self.status()
        return {
            "codigo": self.codigo,
            "codigo_servico": self.codigo_servico,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "escopo_servico": self.escopo_servico,
            "origem_referencia": self.origem_referencia,
            "codigo_referencia": self.codigo_referencia,
            "descricao_referencia": self.descricao_referencia,
            "data_base_ref": self.data_base_ref,
            "arquivo_referencia": self.arquivo_referencia,
            "politica_aplicada": self.politica_aplicada,
            "itens": [i.to_dict() for i in self.itens],
            "pendencias": self.pendencias,
            "custo_mao_obra": round(self.custo_mao_obra, 4),
            "custo_materiais": round(self.custo_materiais, 4),
            "custo_equipamentos": round(self.custo_equipamentos, 4),
            "custo_direto": round(self.custo_direto, 4),
            "status": status,
            "motivo_status": motivo,
        }


class MontadorComposicaoPropria:
    """Monta a composição própria a partir do serviço e da referência."""

    def __init__(self, con: sqlite3.Connection, cfg: Config,
                 expansor: ExpansorComposicoes,
                 buscador_materiais: BuscadorMateriais) -> None:
        self.con = con
        self.cfg = cfg
        self.expansor = expansor
        self.materiais = buscador_materiais

    # ------------------------------------------------------------ montagem
    def montar(
        self,
        codigo_servico: str,
        origem_ref: str,
        codigo_ref: str,
        *,
        top_sugestoes: int = 5,
        auto_vincular: bool = True,
    ) -> ComposicaoPropria | None:
        """Monta a composição própria (sem gravar).

        `auto_vincular` apenas PRÉ-SELECIONA o melhor candidato para o
        usuário avaliar. Nada aqui confirma vínculo: a gravação definitiva
        só ocorre em `salvar`, chamada após a validação humana (item 14).
        """
        servico = self.con.execute(
            "SELECT * FROM company_services WHERE codigo = ?",
            (codigo_servico,)).fetchone()
        if servico is None:
            return None

        expandida = self.expansor.expandir(origem_ref, codigo_ref)
        if expandida is None:
            return None

        politica = politica_para(self.cfg, servico["escopo"])
        fonte = self.con.execute(
            "SELECT nome_arquivo, hash_sha256, data_base FROM source_files"
            " WHERE papel = ?", (origem_ref,)).fetchone()

        comp = ComposicaoPropria(
            codigo_servico=servico["codigo"],
            descricao=servico["descricao"],
            unidade=servico["unidade"],
            escopo_servico=servico["escopo"],
            origem_referencia=expandida.origem,
            codigo_referencia=expandida.codigo,
            descricao_referencia=expandida.descricao,
            data_base_ref=expandida.data_base,
            arquivo_referencia=fonte["nome_arquivo"] if fonte else "",
            hash_ref=fonte["hash_sha256"] if fonte else "",
            politica_aplicada=dict(politica))

        # Pendências herdadas da expansão (auxiliares não resolvidas).
        comp.pendencias.extend(expandida.pendencias)

        seq = 0
        # ------------------------------------------------ 1) mão de obra interna
        if politica.get("mao_obra_interna", True):
            seq += 1
            preco = servico["preco"]
            comp.itens.append(ItemProprio(
                seq=seq, tipo="MAO_DE_OBRA",
                codigo_interno=servico["codigo"],
                descricao_interna=servico["descricao"],
                unidade_interna=servico["unidade"],
                preco_interno=preco,
                coeficiente_original=1.0,
                coeficiente_final=1.0,
                metodo_conversao="IDENTIDADE",
                justificativa_conv=(
                    "Item interno de execução: 1,0000 por unidade do serviço "
                    "(item 17). O preço interno já cobre a execução completa."),
                custo_item=1.0 * (preco or 0.0),
                detalhe_score="Serviço interno selecionado pelo usuário."))
            if not preco:
                comp.pendencias.append({
                    "tipo": "PRECO_INTERNO_AUSENTE", "codins": servico["codigo"],
                    "descricao": servico["descricao"],
                    "detalhe": "Serviço interno sem preço cadastrado.",
                    "caminho": ""})
            if not servico["preco_aprovado"]:
                comp.pendencias.append({
                    "tipo": "PRECO_NAO_APROVADO", "codins": servico["codigo"],
                    "descricao": servico["descricao"],
                    "detalhe": ("Preço do serviço interno não está marcado como "
                                "aprovado na base de origem."),
                    "caminho": ""})

        # ------------------------ 2) mão de obra referencial: registrada, não somada
        for item in expandida.por_classe("MAO_DE_OBRA"):
            seq += 1
            comp.itens.append(ItemProprio(
                seq=seq, tipo="MAO_DE_OBRA",
                origem_ref=expandida.origem, codins_ref=item.codins,
                descricao_ref=item.descricao, unidade_ref=item.unidade_orig,
                coeficiente_original=item.coeficiente,
                caminho_expansao=" ; ".join(item.caminhos),
                coeficiente_final=0.0, custo_item=0.0,
                incluido_no_custo=0,
                motivo_exclusao=MOTIVO_MAO_DE_OBRA_REFERENCIAL))

        # ------------------------------------ 3) materiais e equipamentos
        for classe, chave_politica in (("MATERIAL", "importar_materiais"),
                                       ("EQUIPAMENTO", "importar_equipamentos")):
            importar = politica.get(chave_politica, True)
            for item in expandida.por_classe(classe):
                seq += 1
                proprio = self._montar_insumo(
                    item, classe, expandida.origem, seq,
                    top_sugestoes=top_sugestoes, auto_vincular=auto_vincular)
                if not importar:
                    proprio.incluido_no_custo = 0
                    proprio.custo_item = 0.0
                    proprio.motivo_exclusao = politica.get("motivo", "") or (
                        f"Política de escopo '{servico['escopo']}' não importa "
                        f"{classe.lower()}s da referência.")
                    proprio.pendencia = "ESCOPO_SOBREPOSTO"
                    comp.pendencias.append({
                        "tipo": "ESCOPO_SOBREPOSTO", "codins": item.codins,
                        "descricao": item.descricao,
                        "detalhe": proprio.motivo_exclusao,
                        "caminho": " ; ".join(item.caminhos)})
                elif proprio.pendencia:
                    comp.pendencias.append({
                        "tipo": proprio.pendencia, "codins": item.codins,
                        "descricao": item.descricao,
                        "detalhe": proprio.justificativa_conv or
                                   "Sem correspondente na base interna.",
                        "caminho": " ; ".join(item.caminhos)})
                comp.itens.append(proprio)

        return comp

    def _montar_insumo(self, item, classe: str, origem: str, seq: int, *,
                       top_sugestoes: int, auto_vincular: bool) -> ItemProprio:
        """Busca o equivalente interno de um insumo e resolve a conversão."""
        proprio = ItemProprio(
            seq=seq, tipo=classe,
            origem_ref=origem, codins_ref=item.codins,
            descricao_ref=item.descricao, unidade_ref=item.unidade_orig,
            coeficiente_original=item.coeficiente,
            caminho_expansao=" ; ".join(item.caminhos))

        candidatos = self.materiais.buscar(
            item.descricao, item.unidade, tipo=classe, top_n=top_sugestoes)
        proprio.sugestoes = [c.to_dict() for c in candidatos]

        if not candidatos:
            proprio.pendencia = ("MATERIAL_SEM_CORRESPONDENTE"
                                 if classe == "MATERIAL"
                                 else "EQUIPAMENTO_SEM_CORRESPONDENTE")
            proprio.coeficiente_final = item.coeficiente
            return proprio

        if not auto_vincular:
            proprio.pendencia = "AGUARDANDO_VALIDACAO"
            proprio.coeficiente_final = item.coeficiente
            return proprio

        melhor = candidatos[0]
        self.aplicar_vinculo(proprio, melhor.to_dict(), item.coeficiente)
        return proprio

    @staticmethod
    def aplicar_vinculo(proprio: ItemProprio, candidato: dict[str, Any],
                        coeficiente_ref: float) -> ItemProprio:
        """Aplica um candidato ao item, resolvendo conversão e custo (item 30).

        A matemática é feita aqui, em código determinístico — nunca por IA.
        """
        proprio.codigo_interno = candidato["codigo"]
        proprio.descricao_interna = candidato["descricao"]
        proprio.unidade_interna = candidato.get("unidade_orig") or candidato["unidade"]
        proprio.preco_interno = candidato.get("preco")
        proprio.score = candidato.get("score")
        proprio.detalhe_score = (
            "VÍNCULO VALIDADO" if candidato.get("vinculo_validado")
            else f"Sugestão automática ({candidato.get('confianca', '')})")

        conversao = candidato.get("conversao") or {}
        if conversao.get("ok"):
            proprio.fator_conversao = float(conversao.get("fator", 1.0))
            proprio.metodo_conversao = conversao.get("metodo", "")
            proprio.justificativa_conv = conversao.get("justificativa", "")
            proprio.pendencia = ""
        else:
            proprio.fator_conversao = 1.0
            proprio.metodo_conversao = ""
            proprio.justificativa_conv = conversao.get("justificativa", "")
            proprio.pendencia = conversao.get("pendencia") or "CONVERSAO_PENDENTE"

        # O fator converte 1 unidade interna -> N unidades da referência.
        # Para saber quantas unidades internas são consumidas, divide-se.
        fator = proprio.fator_conversao or 1.0
        proprio.coeficiente_final = (coeficiente_ref / fator if fator else coeficiente_ref)
        if proprio.pendencia == "CONVERSAO_PENDENTE":
            proprio.custo_item = 0.0
        else:
            proprio.custo_item = proprio.coeficiente_final * (proprio.preco_interno or 0.0)
        return proprio

    # -------------------------------------------------------------- gravação
    def proximo_codigo(self) -> str:
        linha = self.con.execute(
            "SELECT codigo FROM own_compositions WHERE codigo LIKE 'CP-%'"
            " ORDER BY codigo DESC LIMIT 1").fetchone()
        proximo = 1
        if linha:
            try:
                proximo = int(str(linha["codigo"]).split("-", 1)[1]) + 1
            except (IndexError, ValueError):
                proximo = 1
        return f"CP-{proximo:06d}"

    def salvar(self, comp: ComposicaoPropria, *, usuario: str,
               confirmar_vinculos: bool = True) -> str:
        """Grava a composição própria e os vínculos confirmados pelo usuário.

        Só deve ser chamada DEPOIS da validação humana — é ela que
        transforma sugestão em conhecimento da empresa (itens 14 e 15).
        """
        agora = datetime.now().isoformat(timespec="seconds")
        status, motivo = comp.status()

        existente = self.con.execute(
            "SELECT codigo, data_criacao FROM own_compositions"
            " WHERE codigo_servico = ?", (comp.codigo_servico,)).fetchone()
        if existente:
            comp.codigo = existente["codigo"]
            criacao = existente["data_criacao"]
            self.con.execute("DELETE FROM own_composition_items"
                             " WHERE codigo_composicao = ?", (comp.codigo,))
        else:
            comp.codigo = comp.codigo or self.proximo_codigo()
            criacao = agora

        self.con.execute(
            "INSERT INTO own_compositions(codigo, codigo_servico, descricao, unidade,"
            " origem_referencia, codigo_referencia, arquivo_referencia, data_base_ref,"
            " hash_ref, escopo_servico, custo_mao_obra, custo_materiais,"
            " custo_equipamentos, custo_direto, status, motivo_status,"
            " data_criacao, data_atualizacao, usuario)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(codigo) DO UPDATE SET"
            "  descricao=excluded.descricao, unidade=excluded.unidade,"
            "  origem_referencia=excluded.origem_referencia,"
            "  codigo_referencia=excluded.codigo_referencia,"
            "  arquivo_referencia=excluded.arquivo_referencia,"
            "  data_base_ref=excluded.data_base_ref, hash_ref=excluded.hash_ref,"
            "  escopo_servico=excluded.escopo_servico,"
            "  custo_mao_obra=excluded.custo_mao_obra,"
            "  custo_materiais=excluded.custo_materiais,"
            "  custo_equipamentos=excluded.custo_equipamentos,"
            "  custo_direto=excluded.custo_direto, status=excluded.status,"
            "  motivo_status=excluded.motivo_status,"
            "  data_atualizacao=excluded.data_atualizacao, usuario=excluded.usuario",
            (comp.codigo, comp.codigo_servico, comp.descricao, comp.unidade,
             comp.origem_referencia, comp.codigo_referencia,
             comp.arquivo_referencia, comp.data_base_ref, comp.hash_ref,
             comp.escopo_servico, comp.custo_mao_obra, comp.custo_materiais,
             comp.custo_equipamentos, comp.custo_direto, status, motivo,
             criacao, agora, usuario))

        self.con.executemany(
            "INSERT INTO own_composition_items(codigo_composicao, seq, tipo,"
            " codigo_interno, descricao_interna, unidade_interna, preco_interno,"
            " origem_ref, codins_ref, descricao_ref, unidade_ref,"
            " coeficiente_original, caminho_expansao, fator_conversao,"
            " metodo_conversao, justificativa_conv, coeficiente_final, custo_item,"
            " score, detalhe_score, incluido_no_custo, motivo_exclusao, pendencia,"
            " data_validacao, usuario)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(comp.codigo, i.seq, i.tipo, i.codigo_interno, i.descricao_interna,
              i.unidade_interna, i.preco_interno, i.origem_ref, i.codins_ref,
              i.descricao_ref, i.unidade_ref, i.coeficiente_original,
              i.caminho_expansao, i.fator_conversao, i.metodo_conversao,
              i.justificativa_conv, i.coeficiente_final, i.custo_item, i.score,
              i.detalhe_score, i.incluido_no_custo, i.motivo_exclusao,
              i.pendencia, agora, usuario) for i in comp.itens])

        if confirmar_vinculos:
            self._confirmar_vinculos(comp, usuario=usuario, agora=agora)
        self._gravar_pendencias(comp, usuario=usuario, agora=agora)

        registrar_log(self.con, usuario=usuario, acao="SALVAR_COMPOSICAO",
                      entidade="own_compositions", chave=comp.codigo,
                      detalhe=f"servico={comp.codigo_servico} "
                              f"ref={comp.origem_referencia} {comp.codigo_referencia} "
                              f"status={status} custo={comp.custo_direto:.4f}")
        self.con.commit()
        return comp.codigo

    def _confirmar_vinculos(self, comp: ComposicaoPropria, *, usuario: str,
                            agora: str) -> None:
        """Registra os vínculos de material/equipamento como confirmados."""
        for item in comp.itens:
            if item.tipo == "MAO_DE_OBRA" or not item.codigo_interno:
                continue
            if not item.codins_ref:
                continue
            seguro, motivo = vinculo_e_seguro_como_global(
                item.descricao_ref, item.unidade_ref)
            escopo = "GLOBAL" if seguro else "COMPOSICAO"
            self.con.execute(
                "UPDATE material_mappings SET status='SUBSTITUIDO'"
                " WHERE codins = ? AND tipo = ? AND status = 'ATUAL'"
                "  AND escopo_vinculo = ? AND codigo_composicao = ?"
                "  AND codigo_empresa <> ?",
                (item.codins_ref, item.tipo, escopo,
                 "" if seguro else comp.codigo, item.codigo_interno))
            self.con.execute(
                "INSERT INTO material_mappings(tipo, origem, codins, descricao_ref,"
                " unidade_ref, chave_tecnica, codigo_empresa, score_original,"
                " detalhe_score, fator_conversao, metodo_conversao, escopo_vinculo,"
                " codigo_composicao, confirmado, status, data, usuario, observacao)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,'ATUAL',?,?,?)",
                (item.tipo, comp.origem_referencia, item.codins_ref,
                 item.descricao_ref, item.unidade_ref,
                 chave_tecnica(item.descricao_ref, item.unidade_ref),
                 item.codigo_interno, item.score, item.detalhe_score,
                 item.fator_conversao, item.metodo_conversao, escopo,
                 "" if seguro else comp.codigo, agora, usuario, motivo))

    def _gravar_pendencias(self, comp: ComposicaoPropria, *, usuario: str,
                           agora: str) -> None:
        """Atualiza a central de pendências desta composição (item 38)."""
        self.con.execute(
            "UPDATE pending_mappings SET status='RESOLVIDA', data_resolucao=?"
            " WHERE codigo_composicao = ? AND status='ABERTA'", (agora, comp.codigo))
        prioridades = {
            "MATERIAL_SEM_CORRESPONDENTE": 1,
            "EQUIPAMENTO_SEM_CORRESPONDENTE": 2,
            "CONVERSAO_PENDENTE": 2,
            "UNIDADE_INCOMPATIVEL": 3,
            "AUXILIAR_NAO_LOCALIZADA": 1,
            "AUXILIAR_PERCENTUAL": 3,
            "ESCOPO_SOBREPOSTO": 4,
            "PRECO_NAO_APROVADO": 6,
            "PRECO_INTERNO_AUSENTE": 5,
        }
        for p in comp.pendencias:
            self.con.execute(
                "INSERT INTO pending_mappings(tipo, codigo_servico, codigo_composicao,"
                " origem, codigo_referencia, codins, descricao, detalhe, prioridade,"
                " status, data, usuario)"
                " VALUES(?,?,?,?,?,?,?,?,?,'ABERTA',?,?)",
                (p.get("tipo", ""), comp.codigo_servico, comp.codigo,
                 comp.origem_referencia, comp.codigo_referencia,
                 p.get("codins", ""), p.get("descricao", ""), p.get("detalhe", ""),
                 prioridades.get(p.get("tipo", ""), 5), agora, usuario))


def confirmar_servico(con: sqlite3.Connection, *, codigo_empresa: str,
                      origem: str, codigo_referencia: str, score: float | None,
                      detalhe: str, usuario: str, observacao: str = "") -> int:
    """Confirma o vínculo serviço interno -> referência (itens 14, 15 e 57).

    A decisão anterior não é apagada: fica como SUBSTITUIDO, preservando
    o histórico exigido pelo item 57.
    """
    agora = datetime.now().isoformat(timespec="seconds")
    con.execute(
        "UPDATE service_mappings SET status='SUBSTITUIDO'"
        " WHERE codigo_empresa = ? AND status='ATUAL'", (codigo_empresa,))
    cur = con.execute(
        "INSERT INTO service_mappings(codigo_empresa, origem, codigo_referencia,"
        " score_original, detalhe_score, confirmado, status, data, usuario, observacao)"
        " VALUES(?,?,?,?,?,1,'ATUAL',?,?,?)",
        (codigo_empresa, origem, codigo_referencia, score, detalhe,
         agora, usuario, observacao))
    novo_id = int(cur.lastrowid or 0)
    con.execute(
        "UPDATE service_mappings SET substituido_por = ?"
        " WHERE codigo_empresa = ? AND status='SUBSTITUIDO' AND substituido_por IS NULL",
        (novo_id, codigo_empresa))
    registrar_log(con, usuario=usuario, acao="CONFIRMAR_SERVICO",
                  entidade="service_mappings", chave=codigo_empresa,
                  detalhe=f"{origem} {codigo_referencia}", score=score)
    con.commit()
    return novo_id


def preco_desatualizado(data_iso: str | None, meses: int) -> bool:
    """Sinaliza cotação antiga (ver diagnóstico §6.2)."""
    if not data_iso:
        return True
    try:
        d = date.fromisoformat(data_iso)
    except ValueError:
        return True
    hoje = date.today()
    return (hoje.year - d.year) * 12 + (hoje.month - d.month) > meses
