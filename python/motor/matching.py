"""Motor de correspondência híbrido (itens 10 a 15, 24, 33 a 36).

O score final é uma média ponderada de quatro componentes independentes,
cada um explicável isoladamente:

    textual    similaridade lexical (RapidFuzz: token_set + partial + ratio)
    semantico  proximidade de sentido (embeddings locais)
    unidade    compatibilidade de unidade
    tecnico    atributos técnicos, já descontadas as penalizações por conflito

Regras não negociáveis:
  * Um conflito técnico GRAVE limita o score final — dois itens com
    dimensões ou materiais incompatíveis nunca chegam a "forte candidato",
    por mais parecidas que sejam as frases (item 11).
  * Nada é confirmado automaticamente, em nenhum score (item 14).
  * Um vínculo já validado pelo usuário é sinalizado como tal e tem
    prioridade sobre qualquer sugestão nova (itens 15, 33 e 34).
"""
from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from . import techspec, units
from .config import Config
from .normalize import normalizar_texto
from .semantic import MotorSemantico

try:
    from rapidfuzz import fuzz
    _TEM_RAPIDFUZZ = True
except ImportError:                              # pragma: no cover
    _TEM_RAPIDFUZZ = False
    import difflib

# Teto de score quando há conflito técnico grave: mantém o candidato
# visível para o usuário, mas fora da faixa de "forte candidato".
TETO_CONFLITO_GRAVE = 0.62

# Fator aplicado quando o termo que identifica o serviço não aparece na
# descrição da referência. Não zera o candidato — apenas o tira da frente
# de quem realmente fala do mesmo assunto.
FATOR_TERMO_AUSENTE = 0.55

ORIGEM_VINCULO_VALIDADO = "VINCULO_VALIDADO"
ORIGEM_SUGESTAO = "SUGESTAO_AUTOMATICA"


# ------------------------------------------------------ raridade de termos

# Palavras que abrem a descrição sem identificar o item — verbos de
# escopo, preposições e qualificadores genéricos.
_GENERICOS = {
    "FORNECIMENTO", "FORNECER", "INSTALACAO", "INSTALAR", "COLOCACAO",
    "ASSENTAMENTO", "MONTAGEM", "APLICACAO", "EXECUCAO", "EXECUTAR",
    "SERVICO", "SERVICOS", "MATERIAL", "MATERIAIS", "OBRA", "PARA",
    "COM", "SEM", "DE", "DO", "DA", "DOS", "DAS", "EM", "POR", "OU",
    "TIPO", "GERAL", "COMUM", "DIVERSOS", "DIVERSAS", "INCLUSIVE",
    "INCLUSO", "INCLUSA", "COMPLETO", "COMPLETA", "ESPECIALIZADA",
    "PADRAO", "NOVO", "NOVA", "UNICA", "UNICO",
}


class IndiceRaridade:
    """IDF por palavra sobre o corpus, para medir cobertura dos termos que
    identificam o item.

    Motivação medida nas bases: "CHAPISCO (PAREDES INTERNAS / EXTERNAS)"
    casava melhor com "RECOLOCAÇÃO DE PLACAS ... EM ÁREA INTERNA OU
    EXTERNA" do que com as composições de chapisco, porque as palavras
    genéricas ("INTERNA", "EXTERNA") são muitas e a que identifica o
    serviço ("CHAPISCO") é uma só. Ponderar por raridade corrige isso:
    o termo que aparece em poucas composições vale muito mais.
    """

    def __init__(self, textos: Sequence[str]) -> None:
        n = max(1, len(textos))
        freq: Counter[str] = Counter()
        for t in textos:
            freq.update(set(self.palavras(t)))
        self.idf = {p: math.log((n + 1) / (c + 1)) + 1.0 for p, c in freq.items()}
        self.idf_padrao = math.log(n + 1) + 1.0     # termo inédito: máxima raridade

    @staticmethod
    def palavras(texto: str) -> list[str]:
        return [p for p in re.split(r"[^0-9A-Z]+", normalizar_texto(texto))
                if len(p) >= 3]

    def determinante(self, consulta: str) -> str:
        """Termo NÚCLEO da descrição — o substantivo que nomeia o item.

        Nestas bases a descrição é sempre encabeçada pelo que o item É
        ("REBOCO - ARGAMASSA ÚNICA", "CHAPISCO (PAREDES INTERNAS)",
        "ALVENARIA EM BLOCOS..."); o resto qualifica. Por isso o núcleo é
        o primeiro termo significativo, e NÃO o mais raro: medido nestas
        bases, o mais raro tende a ser justamente o qualificador
        acidental ("EXTERNAS", "ÚNICA"), que não identifica nada.

        Verbos de escopo iniciais são pulados: em "FORNECIMENTO E
        INSTALAÇÃO DE DIVISÓRIA" o que identifica é DIVISÓRIA.
        """
        for palavra in self.palavras(consulta):
            if len(palavra) >= 4 and palavra.isalpha() and palavra not in _GENERICOS:
                return palavra
        return ""

    def contem(self, termo: str, alvo: str) -> bool:
        """Termo presente no alvo, aceitando flexão e abreviação."""
        if not termo:
            return True
        presentes = set(self.palavras(alvo))
        if termo in presentes:
            return True
        raiz = termo[:max(4, len(termo) - 2)]
        return any(p.startswith(raiz) or termo.startswith(p[:max(4, len(p) - 2)])
                   for p in presentes if len(p) >= 4)

    def cobertura(self, consulta: str, alvo: str) -> float:
        """Fração do "peso de identidade" da consulta presente no alvo.

        1,0 = todos os termos discriminantes aparecem no alvo.
        0,0 = nenhum aparece — descrições sobre coisas diferentes.
        """
        termos = set(self.palavras(consulta))
        if not termos:
            return 0.5                     # sem termos úteis: neutro
        presentes = set(self.palavras(alvo))
        total = sum(self.idf.get(t, self.idf_padrao) for t in termos)
        if total <= 0:
            return 0.5
        casado = 0.0
        for t in termos:
            peso = self.idf.get(t, self.idf_padrao)
            if t in presentes:
                casado += peso
            elif any(t in p or p in t for p in presentes if len(p) >= 4):
                casado += peso * 0.6        # casamento parcial (flexão/abreviação)
        return max(0.0, min(1.0, casado / total))


# ------------------------------------------------------------ similaridade textual

def similaridade_textual(a: str, b: str) -> float:
    """Combinação de métricas lexicais, normalizada em 0..1.

    `token_set_ratio` domina porque as descrições internas e referenciais
    dizem a mesma coisa em ordens e níveis de detalhe diferentes.
    """
    na, nb = normalizar_texto(a), normalizar_texto(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if _TEM_RAPIDFUZZ:
        token_set = fuzz.token_set_ratio(na, nb) / 100.0
        token_sort = fuzz.token_sort_ratio(na, nb) / 100.0
        parcial = fuzz.partial_ratio(na, nb) / 100.0
        simples = fuzz.ratio(na, nb) / 100.0
        return 0.45 * token_set + 0.25 * token_sort + 0.15 * parcial + 0.15 * simples
    return difflib.SequenceMatcher(None, na, nb).ratio()


# ------------------------------------------------------------------ resultado

@dataclass
class Candidato:
    """Um candidato pontuado, com o score decomposto (item 12)."""

    origem: str
    codigo: str
    descricao: str
    unidade: str
    score: float = 0.0
    componentes: dict[str, float] = field(default_factory=dict)
    penalidades: list[str] = field(default_factory=list)
    reforcos: list[str] = field(default_factory=list)
    conflito_grave: bool = False
    tipo_origem: str = ORIGEM_SUGESTAO
    confianca: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "origem": self.origem,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "score": round(self.score, 4),
            "score_pct": round(self.score * 100, 1),
            "componentes": {k: round(v, 4) for k, v in self.componentes.items()},
            "penalidades": self.penalidades,
            "reforcos": self.reforcos,
            "conflito_grave": self.conflito_grave,
            "tipo": self.tipo_origem,
            "vinculo_validado": self.tipo_origem == ORIGEM_VINCULO_VALIDADO,
            "confianca": self.confianca,
            **self.extra,
        }

    def explicacao(self) -> str:
        """Texto pronto para a interface (item 12)."""
        linhas = [f"{self.origem} {self.codigo}", f"  {self.descricao}"]
        rotulos = {"textual": "Descrição textual", "semantico": "Semântica",
                   "cobertura": "Termos-chave", "unidade": "Unidade",
                   "tecnico": "Técnico"}
        for chave, rotulo in rotulos.items():
            if chave in self.componentes:
                linhas.append(f"  {rotulo:<20} {self.componentes[chave] * 100:5.1f}%")
        linhas.append(f"  {'SCORE FINAL':<20} {self.score * 100:5.1f}%  ({self.confianca})")
        for r in self.reforcos:
            linhas.append(f"    + {r}")
        for p in self.penalidades:
            linhas.append(f"    - {p}")
        return "\n".join(linhas)


def classificar_confianca(score: float, faixas: dict[str, float]) -> str:
    """Faixa de confiança (item 35). Nunca implica confirmação automática."""
    if score >= faixas.get("forte", 0.90):
        return "FORTE"
    if score >= faixas.get("provavel", 0.75):
        return "PROVAVEL"
    if score >= faixas.get("baixa", 0.50):
        return "BAIXA"
    return "MUITO_BAIXA"


def _combinar(componentes: dict[str, float], pesos: dict[str, float]) -> float:
    total = sum(pesos.get(k, 0.0) for k in componentes)
    if total <= 0:
        return 0.0
    return sum(v * pesos.get(k, 0.0) for k, v in componentes.items()) / total


def pontuar(
    consulta_desc: str,
    consulta_un: str,
    alvo_desc: str,
    alvo_un: str,
    *,
    pesos: dict[str, float],
    faixas: dict[str, float],
    sim_semantica: float = 0.0,
    cobertura: float | None = None,
    spec_consulta: techspec.Spec | None = None,
    spec_alvo: techspec.Spec | None = None,
) -> tuple[float, dict[str, float], techspec.Comparacao]:
    """Calcula o score decomposto entre uma consulta e um alvo."""
    sc = spec_consulta if spec_consulta is not None else techspec.extrair(
        consulta_desc, consulta_un)
    sa = spec_alvo if spec_alvo is not None else techspec.extrair(alvo_desc, alvo_un)
    comp_tec = techspec.comparar(sc, sa)

    componentes = {
        "textual": similaridade_textual(consulta_desc, alvo_desc),
        "semantico": max(0.0, min(1.0, sim_semantica)),
        "unidade": units.compativel(consulta_un, alvo_un),
        "tecnico": comp_tec.score,
    }
    if cobertura is not None:
        componentes["cobertura"] = max(0.0, min(1.0, cobertura))
    score = _combinar(componentes, pesos)
    if comp_tec.conflito_grave:
        score = min(score, TETO_CONFLITO_GRAVE)
    return max(0.0, min(1.0, score)), componentes, comp_tec


# ------------------------------------------------------------------ serviços

class BuscadorServicos:
    """Busca composições EDIF/INFRA para um serviço interno (itens 9 e 10).

    Pesquisa as duas bases simultaneamente. Auxiliares ficam de fora: são
    insumos de composição, não serviços de contrato.
    """

    NOME_INDICE = "referencia_servicos"

    def __init__(self, con: sqlite3.Connection, cfg: Config,
                 semantico: MotorSemantico) -> None:
        self.con = con
        self.cfg = cfg
        self.semantico = semantico
        self._linhas: list[sqlite3.Row] = []
        self._specs: list[techspec.Spec] = []
        self._por_chave: dict[tuple[str, str], int] = {}
        self._raridade: IndiceRaridade | None = None
        self._carregado = False

    def carregar(self, origens: Sequence[str] = ("EDIF", "INFRA"),
                 forcar: bool = False) -> None:
        if self._carregado and not forcar:
            return
        marcadores = ",".join("?" for _ in origens)
        self._linhas = self.con.execute(
            f"SELECT origem, codigo, descricao, descricao_norm, unidade, unidade_orig,"
            f" custo_total FROM reference_compositions WHERE origem IN ({marcadores})"
            f" ORDER BY origem, codigo", tuple(origens)).fetchall()
        self._specs = [techspec.extrair(r["descricao"], r["unidade"])
                       for r in self._linhas]
        self._por_chave = {(r["origem"], r["codigo"]): i
                           for i, r in enumerate(self._linhas)}
        self._raridade = IndiceRaridade([r["descricao"] for r in self._linhas])
        self.semantico.indexar(
            self.NOME_INDICE,
            [r["descricao"] for r in self._linhas],
            [f"{r['origem']}|{r['codigo']}" for r in self._linhas],
            forcar=forcar)
        self._carregado = True

    # ------------------------------------------------------- pré-filtro
    def _candidatos(self, descricao: str, unidade: str, origens: set[str],
                    limite: int) -> list[int]:
        """Reduz o universo antes de pontuar.

        Pontuar 3.475 composições por consulta é desperdício: o pré-filtro
        semântico + lexical entrega as poucas centenas que importam.
        """
        semelhantes = self.semantico.similaridades(self.NOME_INDICE, descricao)
        ordenados = sorted(semelhantes.items(), key=lambda kv: -kv[1])
        selecao = [i for i, _ in ordenados[:limite]]
        vistos = set(selecao)

        # Rede lexical de segurança: descrições muito curtas ou muito
        # atípicas podem escapar do índice semântico.
        alvo = normalizar_texto(descricao)
        if _TEM_RAPIDFUZZ and alvo:
            lexicais = []
            for i, linha in enumerate(self._linhas):
                if i in vistos:
                    continue
                escore = fuzz.token_set_ratio(alvo, linha["descricao_norm"])
                if escore >= 60:
                    lexicais.append((escore, i))
            lexicais.sort(reverse=True)
            for _, i in lexicais[:limite]:
                vistos.add(i)
                selecao.append(i)

        if origens:
            selecao = [i for i in selecao if self._linhas[i]["origem"] in origens]
        if not selecao:
            selecao = [i for i, r in enumerate(self._linhas)
                       if not origens or r["origem"] in origens]
        return selecao

    # ------------------------------------------------------------ busca
    def buscar(
        self,
        descricao: str,
        unidade: str = "",
        *,
        origens: Iterable[str] = ("EDIF", "INFRA"),
        top_n: int = 10,
        codigo_empresa: str = "",
        score_minimo: float | None = None,
        largura_prefiltro: int = 220,
    ) -> list[Candidato]:
        """Devolve os melhores candidatos, ordenados por score."""
        self.carregar()
        origens_set = {o.upper() for o in origens}
        minimo = (self.cfg.score_minimo_sugestao
                  if score_minimo is None else score_minimo)
        spec_consulta = techspec.extrair(descricao, unidade)

        indices = self._candidatos(descricao, unidade, origens_set, largura_prefiltro)
        semelhancas = self.semantico.similaridades(
            self.NOME_INDICE, descricao, indices)
        determinante = self._raridade.determinante(descricao) if self._raridade else ""

        candidatos: list[Candidato] = []
        for i in indices:
            linha = self._linhas[i]
            score, componentes, comp = pontuar(
                descricao, unidade, linha["descricao"], linha["unidade"],
                pesos=self.cfg.pesos_servico, faixas=self.cfg.faixas_confianca,
                sim_semantica=semelhancas.get(i, 0.0),
                cobertura=(self._raridade.cobertura(descricao, linha["descricao"])
                           if self._raridade else None),
                spec_consulta=spec_consulta, spec_alvo=self._specs[i])
            penalidades = list(comp.penalidades)
            if determinante and not self._raridade.contem(
                    determinante, linha["descricao"]):
                score *= FATOR_TERMO_AUSENTE
                penalidades.append(
                    f"Termo determinante \"{determinante}\" ausente na referência.")
            if score < minimo:
                continue
            candidatos.append(Candidato(
                origem=linha["origem"], codigo=linha["codigo"],
                descricao=linha["descricao"], unidade=linha["unidade"],
                score=score, componentes=componentes,
                penalidades=penalidades, reforcos=comp.reforcos,
                conflito_grave=comp.conflito_grave,
                confianca=classificar_confianca(score, self.cfg.faixas_confianca),
                extra={"custo_total": linha["custo_total"],
                       "unidade_orig": linha["unidade_orig"]}))

        candidatos.sort(key=lambda c: -c.score)
        candidatos = candidatos[:top_n]

        if codigo_empresa:
            candidatos = self._promover_vinculo(codigo_empresa, candidatos, top_n)
        return candidatos

    def _promover_vinculo(self, codigo_empresa: str,
                          candidatos: list[Candidato], top_n: int) -> list[Candidato]:
        """Traz o vínculo já confirmado para o topo, marcado (itens 15 e 33)."""
        linha = self.con.execute(
            "SELECT origem, codigo_referencia, score_original FROM service_mappings"
            " WHERE codigo_empresa = ? AND status = 'ATUAL' AND confirmado = 1",
            (codigo_empresa,)).fetchone()
        if linha is None:
            return candidatos

        chave = (linha["origem"], linha["codigo_referencia"])
        existente = next((c for c in candidatos
                          if (c.origem, c.codigo) == chave), None)
        if existente is None:
            idx = self._por_chave.get(chave)
            if idx is None:
                return candidatos
            ref = self._linhas[idx]
            existente = Candidato(
                origem=ref["origem"], codigo=ref["codigo"],
                descricao=ref["descricao"], unidade=ref["unidade"],
                score=linha["score_original"] or 1.0,
                componentes={}, extra={"custo_total": ref["custo_total"]})
        else:
            candidatos = [c for c in candidatos if c is not existente]

        existente.tipo_origem = ORIGEM_VINCULO_VALIDADO
        existente.confianca = "VALIDADO"
        existente.reforcos = ["Vínculo já confirmado pelo usuário."] + existente.reforcos
        return [existente] + candidatos[:max(0, top_n - 1)]

    def por_chave(self, origem: str, codigo: str) -> sqlite3.Row | None:
        self.carregar()
        idx = self._por_chave.get((origem, codigo))
        return self._linhas[idx] if idx is not None else None

    def pesquisa_manual(
        self,
        termo: str,
        *,
        origens: Iterable[str] = ("EDIF", "INFRA", "AUX"),
        unidade: str = "",
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """Pesquisa livre por palavra-chave, com filtros (item 36)."""
        origens_set = [o.upper() for o in origens]
        marcadores = ",".join("?" for _ in origens_set)
        sql = (f"SELECT origem, codigo, descricao, unidade, custo_total"
               f" FROM reference_compositions WHERE origem IN ({marcadores})")
        params: list[Any] = list(origens_set)
        if unidade:
            sql += " AND unidade = ?"
            params.append(units.normalizar_unidade(unidade))
        palavras = [p for p in normalizar_texto(termo).split() if p]
        for palavra in palavras:
            sql += " AND descricao_norm LIKE ?"
            params.append(f"%{palavra}%")
        linhas = self.con.execute(sql, tuple(params)).fetchall()
        saida = [dict(l) for l in linhas]
        if palavras:
            alvo = normalizar_texto(termo)
            saida.sort(key=lambda d: -similaridade_textual(alvo, d["descricao"]))
        return saida[:limite]


# ------------------------------------------------------------ materiais

def chave_tecnica(descricao: str, unidade: str = "") -> str:
    """Chave que identifica um insumo com seus discriminantes técnicos.

    Existe por causa do item 58: "AREIA MÉDIA" pode virar vínculo global,
    mas "BLOCO DE CONCRETO" sem dimensão não pode. Incluindo os atributos
    técnicos na chave, o vínculo confirmado para o bloco de 14 cm não é
    reaproveitado para o de 19 cm.
    """
    spec = techspec.extrair(descricao, unidade)
    partes: list[str] = []
    if spec.materiais:
        partes.append("MAT:" + "+".join(sorted(spec.materiais)))
    if spec.espessura_cm is not None:
        partes.append(f"ESP:{spec.espessura_cm:g}")
    if spec.diametro_mm is not None:
        partes.append(f"DIA:{spec.diametro_mm:g}")
    if spec.fck_mpa is not None:
        partes.append(f"FCK:{spec.fck_mpa:g}")
    if spec.classe_aco:
        partes.append(f"CA:{spec.classe_aco}")
    if spec.dimensoes_cm:
        partes.append("DIM:" + "x".join(f"{d:g}" for d in spec.dimensoes_cm))
    if spec.tracos:
        partes.append("TR:" + "+".join(sorted(spec.tracos)))
    nucleo = "|".join(partes)
    base = normalizar_texto(descricao)
    return f"{nucleo}||{base}" if nucleo else base


def vinculo_e_seguro_como_global(descricao: str, unidade: str = "") -> tuple[bool, str]:
    """Decide se um vínculo pode valer globalmente (item 58).

    Um insumo cujo nome sugere variantes dimensionais mas não traz a
    dimensão é ambíguo: vincular globalmente propagaria um erro para
    todas as composições que o usam.
    """
    spec = techspec.extrair(descricao, unidade)
    sem_dimensao = (spec.espessura_cm is None and spec.diametro_mm is None
                    and not spec.dimensoes_cm and spec.fck_mpa is None
                    and not spec.classe_aco)
    exige_dimensao = bool(spec.materiais & {
        "BLOCO_CONCRETO", "BLOCO_CERAMICO", "TIJOLO", "ACO", "PVC",
        "COBRE", "GALVANIZADO", "CERAMICO", "MADEIRA", "VIDRO"})
    if sem_dimensao and exige_dimensao:
        return False, ("Insumo admite variantes dimensionais mas a descrição não "
                       "traz a dimensão. O vínculo fica restrito a esta composição "
                       "até que o usuário defina a característica técnica.")
    return True, ""


class BuscadorMateriais:
    """Busca itens internos equivalentes a um insumo da referência (itens 23, 24, 28).

    Materiais e equipamentos usam o mesmo algoritmo, mudando o universo:
    equipamento só é procurado nas famílias de equipamento da base interna.
    """

    def __init__(self, con: sqlite3.Connection, cfg: Config,
                 semantico: MotorSemantico) -> None:
        self.con = con
        self.cfg = cfg
        self.semantico = semantico
        self._linhas: dict[str, list[sqlite3.Row]] = {}
        self._specs: dict[str, list[techspec.Spec]] = {}
        self._raridade: dict[str, IndiceRaridade] = {}
        self._indice_por_codigo: dict[str, int] = {}

    def _nome_indice(self, tipo: str) -> str:
        return f"materiais_{tipo.lower()}"

    def carregar(self, tipo: str = "MATERIAL", forcar: bool = False) -> None:
        if tipo in self._linhas and not forcar:
            return
        self._linhas[tipo] = self.con.execute(
            "SELECT codigo, familia, unidade, unidade_orig, descricao,"
            " descricao_norm, tipo_item, preco, preco_ultimo, data_ultimo"
            " FROM company_materials WHERE tipo_item = ? ORDER BY codigo",
            (tipo,)).fetchall()
        linhas = self._linhas[tipo]
        self._specs[tipo] = [techspec.extrair(r["descricao"], r["unidade"])
                             for r in linhas]
        self._raridade[tipo] = IndiceRaridade([r["descricao"] for r in linhas])
        self.semantico.indexar(
            self._nome_indice(tipo),
            [r["descricao"] for r in linhas],
            [r["codigo"] for r in linhas], forcar=forcar)

    def buscar(
        self,
        descricao: str,
        unidade: str = "",
        *,
        tipo: str = "MATERIAL",
        top_n: int = 10,
        score_minimo: float | None = None,
        familia: str = "",
        largura_prefiltro: int = 260,
        usar_vinculo: bool = True,
    ) -> list[Candidato]:
        """Melhores candidatos internos para um insumo da referência."""
        self.carregar(tipo)
        linhas = self._linhas[tipo]
        specs = self._specs[tipo]
        raridade = self._raridade[tipo]
        minimo = (self.cfg.score_minimo_sugestao
                  if score_minimo is None else score_minimo)
        nome_indice = self._nome_indice(tipo)

        semelhantes = self.semantico.similaridades(nome_indice, descricao)
        ordenados = sorted(semelhantes.items(), key=lambda kv: -kv[1])
        indices = [i for i, _ in ordenados[:largura_prefiltro]]
        vistos = set(indices)
        alvo = normalizar_texto(descricao)
        if _TEM_RAPIDFUZZ and alvo:
            lexicais = []
            for i, linha in enumerate(linhas):
                if i in vistos:
                    continue
                escore = fuzz.token_set_ratio(alvo, linha["descricao_norm"])
                if escore >= 65:
                    lexicais.append((escore, i))
            lexicais.sort(reverse=True)
            indices.extend(i for _, i in lexicais[:largura_prefiltro])
        if familia:
            alvo_familia = normalizar_texto(familia)
            indices = [i for i in indices
                       if normalizar_texto(linhas[i]["familia"]) == alvo_familia]

        spec_consulta = techspec.extrair(descricao, unidade)
        nucleo = raridade.determinante(descricao)
        semelhancas = self.semantico.similaridades(nome_indice, descricao, indices)

        candidatos: list[Candidato] = []
        for i in indices:
            linha = linhas[i]
            score, componentes, comp = pontuar(
                descricao, unidade, linha["descricao"], linha["unidade"],
                pesos=self.cfg.pesos_material, faixas=self.cfg.faixas_confianca,
                sim_semantica=semelhancas.get(i, 0.0),
                cobertura=raridade.cobertura(descricao, linha["descricao"]),
                spec_consulta=spec_consulta, spec_alvo=specs[i])
            penalidades = list(comp.penalidades)
            if nucleo and not raridade.contem(nucleo, linha["descricao"]):
                score *= FATOR_TERMO_AUSENTE
                penalidades.append(
                    f"Termo determinante \"{nucleo}\" ausente no item interno.")
            if score < minimo:
                continue
            conversao = units.converter(
                linha["unidade"], unidade,
                descricao_produto=linha["descricao"],
                regra_produto=self._regra_cadastrada(
                    linha["codigo"], linha["unidade"], unidade))
            candidatos.append(Candidato(
                origem="EMPRESA", codigo=linha["codigo"],
                descricao=linha["descricao"], unidade=linha["unidade"],
                score=score, componentes=componentes,
                penalidades=penalidades, reforcos=comp.reforcos,
                conflito_grave=comp.conflito_grave,
                confianca=classificar_confianca(score, self.cfg.faixas_confianca),
                extra={
                    "familia": linha["familia"],
                    "unidade_orig": linha["unidade_orig"],
                    "preco": linha["preco"],
                    "preco_ultimo": linha["preco_ultimo"],
                    "data_ultimo": linha["data_ultimo"],
                    "tipo_item": linha["tipo_item"],
                    "conversao": {
                        "ok": conversao.ok,
                        "fator": conversao.fator,
                        "metodo": conversao.metodo,
                        "justificativa": conversao.justificativa,
                        "pendencia": conversao.pendencia,
                    },
                }))

        candidatos.sort(key=lambda c: -c.score)
        candidatos = candidatos[:top_n]
        if usar_vinculo:
            candidatos = self._promover_vinculo(descricao, unidade, tipo,
                                                candidatos, top_n)
        return candidatos

    def _regra_cadastrada(self, codigo: str, origem_un: str,
                          destino_un: str) -> float | None:
        """Fator já cadastrado para este material (item 26)."""
        from .normalize import normalizar_unidade
        linha = self.con.execute(
            "SELECT fator FROM conversion_rules WHERE escopo = 'MATERIAL'"
            " AND chave = ? AND unidade_origem = ? AND unidade_destino = ?",
            (codigo, normalizar_unidade(origem_un),
             normalizar_unidade(destino_un))).fetchone()
        return linha["fator"] if linha else None

    def _promover_vinculo(self, descricao: str, unidade: str, tipo: str,
                          candidatos: list[Candidato], top_n: int) -> list[Candidato]:
        """Reaproveita vínculo já validado para o mesmo insumo (itens 33 e 34).

        Casa pela chave técnica — não pelo nome — para não reaproveitar o
        vínculo do bloco de 14 cm no de 19 cm (item 58).
        """
        chave = chave_tecnica(descricao, unidade)
        linha = self.con.execute(
            "SELECT codigo_empresa, score_original, fator_conversao,"
            " metodo_conversao FROM material_mappings"
            " WHERE chave_tecnica = ? AND tipo = ? AND status = 'ATUAL'"
            " AND confirmado = 1 AND escopo_vinculo = 'GLOBAL'"
            " ORDER BY data DESC LIMIT 1", (chave, tipo)).fetchone()
        if linha is None:
            return candidatos

        codigo = linha["codigo_empresa"]
        existente = next((c for c in candidatos if c.codigo == codigo), None)
        if existente is None:
            interno = self.con.execute(
                "SELECT codigo, familia, unidade, unidade_orig, descricao, preco,"
                " preco_ultimo, data_ultimo, tipo_item FROM company_materials"
                " WHERE codigo = ?", (codigo,)).fetchone()
            if interno is None:
                return candidatos
            existente = Candidato(
                origem="EMPRESA", codigo=interno["codigo"],
                descricao=interno["descricao"], unidade=interno["unidade"],
                score=linha["score_original"] or 1.0,
                extra={"familia": interno["familia"], "preco": interno["preco"],
                       "unidade_orig": interno["unidade_orig"],
                       "preco_ultimo": interno["preco_ultimo"],
                       "data_ultimo": interno["data_ultimo"],
                       "tipo_item": interno["tipo_item"],
                       "conversao": {"ok": True,
                                     "fator": linha["fator_conversao"],
                                     "metodo": linha["metodo_conversao"],
                                     "justificativa": "Conversão do vínculo validado.",
                                     "pendencia": ""}})
        else:
            candidatos = [c for c in candidatos if c is not existente]

        existente.tipo_origem = ORIGEM_VINCULO_VALIDADO
        existente.confianca = "VALIDADO"
        existente.reforcos = ["Vínculo já confirmado pelo usuário para este insumo."
                              ] + existente.reforcos
        return [existente] + candidatos[:max(0, top_n - 1)]

    def pesquisa_manual(self, termo: str, *, tipo: str = "", familia: str = "",
                        unidade: str = "", limite: int = 50) -> list[dict[str, Any]]:
        """Pesquisa livre na base interna, com filtros (item 36)."""
        sql = ("SELECT codigo, familia, unidade, unidade_orig, descricao, preco,"
               " tipo_item FROM company_materials WHERE 1=1")
        params: list[Any] = []
        if tipo:
            sql += " AND tipo_item = ?"
            params.append(tipo)
        if familia:
            sql += " AND familia = ?"
            params.append(familia)
        if unidade:
            sql += " AND unidade = ?"
            params.append(units.normalizar_unidade(unidade))
        for palavra in (p for p in normalizar_texto(termo).split() if p):
            sql += " AND descricao_norm LIKE ?"
            params.append(f"%{palavra}%")
        linhas = [dict(l) for l in self.con.execute(sql, tuple(params)).fetchall()]
        if termo:
            alvo = normalizar_texto(termo)
            linhas.sort(key=lambda d: -similaridade_textual(alvo, d["descricao"]))
        return linhas[:limite]
