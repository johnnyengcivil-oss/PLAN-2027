"""Composições de referência e expansão recursiva (itens 16 a 22).

Duas representações são produzidas e guardadas ao mesmo tempo (item 22):

  * HIERÁRQUICA — a árvore como está na base, preservando quais insumos
    vieram de qual composição auxiliar e em que nível.
  * CONSOLIDADA — as folhas (materiais e equipamentos) com o coeficiente
    acumulado, que é o produto dos coeficientes ao longo do caminho.

Exemplo do item 21, verificado contra a base real:

    10580 ALVENARIA DE TIJOLOS (M3)
      └── 10630 ARGAMASSA DE CIMENTO E AREIA 1:3  coef 0,2200  [auxiliar]
            └── 10517 CIMENTO PORTLAND CPII-E/F-32  coef 486,0000 Kg
    consolidado: CIMENTO = 0,2200 × 486,0000 = 106,9200 Kg
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterator

PROFUNDIDADE_MAXIMA = 12

CLASSES_FOLHA = {"MATERIAL", "EQUIPAMENTO", "MAO_DE_OBRA", "OUTRO"}

# Unidade de composição auxiliar que representa percentual sobre material e
# mão de obra, não quantidade física. Não é expansível por multiplicação de
# coeficiente — vira pendência para decisão do usuário (item 67).
UNIDADE_PERCENTUAL = "PCT"


@dataclass
class NoInsumo:
    """Um nó da árvore de composição."""

    codins: str
    descricao: str
    unidade: str
    unidade_orig: str
    classe: str
    coeficiente: float                 # coeficiente local, como está na base
    coeficiente_acumulado: float       # produto do caminho até a raiz
    custo_unitario: float | None
    nivel: int
    caminho: tuple[str, ...]           # códigos das composições atravessadas
    origem_pai: str
    codigo_pai: str
    filhos: list["NoInsumo"] = field(default_factory=list)
    expandido: bool = False
    pendencia: str = ""
    detalhe_pendencia: str = ""

    @property
    def e_folha(self) -> bool:
        return not self.filhos

    def descricao_caminho(self) -> str:
        """Caminho legível da raiz até este nó (rastreabilidade, item 31)."""
        return " > ".join(self.caminho) if self.caminho else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "codins": self.codins,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "unidade_orig": self.unidade_orig,
            "classe": self.classe,
            "coeficiente": self.coeficiente,
            "coeficiente_acumulado": self.coeficiente_acumulado,
            "custo_unitario": self.custo_unitario,
            "nivel": self.nivel,
            "caminho": list(self.caminho),
            "expandido": self.expandido,
            "pendencia": self.pendencia,
            "detalhe_pendencia": self.detalhe_pendencia,
            "filhos": [f.to_dict() for f in self.filhos],
        }

    def percorrer(self) -> Iterator["NoInsumo"]:
        yield self
        for filho in self.filhos:
            yield from filho.percorrer()


@dataclass
class ItemConsolidado:
    """Uma folha da árvore, com o coeficiente já acumulado."""

    codins: str
    descricao: str
    unidade: str
    unidade_orig: str
    classe: str
    coeficiente: float
    custo_unitario: float | None
    ocorrencias: int = 1
    caminhos: list[str] = field(default_factory=list)

    @property
    def custo(self) -> float:
        return self.coeficiente * (self.custo_unitario or 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "codins": self.codins,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "unidade_orig": self.unidade_orig,
            "classe": self.classe,
            "coeficiente": round(self.coeficiente, 8),
            "custo_unitario": self.custo_unitario,
            "custo": round(self.custo, 4),
            "ocorrencias": self.ocorrencias,
            "caminhos": self.caminhos,
        }


@dataclass
class ComposicaoExpandida:
    """Resultado completo da expansão de uma composição de referência."""

    origem: str
    codigo: str
    descricao: str
    unidade: str
    unidade_orig: str
    custo_total: float | None
    data_base: str
    arvore: list[NoInsumo] = field(default_factory=list)
    consolidado: list[ItemConsolidado] = field(default_factory=list)
    pendencias: list[dict[str, str]] = field(default_factory=list)
    profundidade: int = 0
    auxiliares_expandidas: int = 0

    def por_classe(self, classe: str) -> list[ItemConsolidado]:
        return [i for i in self.consolidado if i.classe == classe]

    def custo_calculado(self) -> float:
        """Soma dos insumos folha. Comparável ao custo publicado na base."""
        return sum(i.custo for i in self.consolidado)

    def to_dict(self, incluir_arvore: bool = True) -> dict[str, Any]:
        saida: dict[str, Any] = {
            "origem": self.origem,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "unidade_orig": self.unidade_orig,
            "custo_total_base": self.custo_total,
            "custo_calculado": round(self.custo_calculado(), 4),
            "data_base": self.data_base,
            "profundidade": self.profundidade,
            "auxiliares_expandidas": self.auxiliares_expandidas,
            "consolidado": [i.to_dict() for i in self.consolidado],
            "pendencias": self.pendencias,
            "resumo_classes": self.resumo_classes(),
        }
        if incluir_arvore:
            saida["arvore"] = [n.to_dict() for n in self.arvore]
        return saida

    def resumo_classes(self) -> dict[str, int]:
        resumo: dict[str, int] = {}
        for item in self.consolidado:
            resumo[item.classe] = resumo.get(item.classe, 0) + 1
        return resumo


class ExpansorComposicoes:
    """Lê composições da base e expande as auxiliares recursivamente."""

    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con
        self._cache_comp: dict[tuple[str, str], sqlite3.Row | None] = {}
        self._cache_insumos: dict[tuple[str, str], list[sqlite3.Row]] = {}

    # -------------------------------------------------------------- leitura
    def composicao(self, origem: str, codigo: str) -> sqlite3.Row | None:
        chave = (origem, codigo)
        if chave not in self._cache_comp:
            self._cache_comp[chave] = self.con.execute(
                "SELECT * FROM reference_compositions WHERE origem = ? AND codigo = ?",
                chave).fetchone()
        return self._cache_comp[chave]

    def insumos(self, origem: str, codigo: str) -> list[sqlite3.Row]:
        chave = (origem, codigo)
        if chave not in self._cache_insumos:
            self._cache_insumos[chave] = self.con.execute(
                "SELECT * FROM reference_inputs WHERE origem = ? AND codigo = ?"
                " ORDER BY seq", chave).fetchall()
        return self._cache_insumos[chave]

    def localizar_auxiliar(self, codins: str) -> sqlite3.Row | None:
        """Resolve um CODINS que é composição auxiliar.

        Procura primeiro em AUX — que é onde 92/92 das auxiliares
        referenciadas realmente estão — e só depois em EDIF/INFRA, para o
        caso de uma atualização futura da base passar a encadeá-las.
        """
        for origem in ("AUX", "EDIF", "INFRA"):
            linha = self.composicao(origem, codins)
            if linha is not None:
                return linha
        return None

    # ------------------------------------------------------------ expansão
    def expandir(self, origem: str, codigo: str, *,
                 profundidade_maxima: int = PROFUNDIDADE_MAXIMA) -> ComposicaoExpandida | None:
        """Expande uma composição, resolvendo auxiliares recursivamente."""
        raiz = self.composicao(origem, codigo)
        if raiz is None:
            return None

        resultado = ComposicaoExpandida(
            origem=raiz["origem"], codigo=raiz["codigo"],
            descricao=raiz["descricao"], unidade=raiz["unidade"],
            unidade_orig=raiz["unidade_orig"], custo_total=raiz["custo_total"],
            data_base=raiz["data_base"])

        resultado.arvore = self._expandir_nivel(
            origem, codigo, fator=1.0, nivel=0,
            caminho=(f"{origem} {codigo}",),
            visitados={(origem, codigo)},
            resultado=resultado,
            profundidade_maxima=profundidade_maxima)

        resultado.profundidade = max(
            (no.nivel for raiz_no in resultado.arvore for no in raiz_no.percorrer()),
            default=0)
        resultado.consolidado = self._consolidar(resultado.arvore)
        return resultado

    def _expandir_nivel(
        self,
        origem: str,
        codigo: str,
        *,
        fator: float,
        nivel: int,
        caminho: tuple[str, ...],
        visitados: set[tuple[str, str]],
        resultado: ComposicaoExpandida,
        profundidade_maxima: int,
    ) -> list[NoInsumo]:
        nos: list[NoInsumo] = []
        for linha in self.insumos(origem, codigo):
            coeficiente = linha["coeficiente"] or 0.0
            acumulado = fator * coeficiente
            no = NoInsumo(
                codins=linha["codins"], descricao=linha["descricao"],
                unidade=linha["unidade"], unidade_orig=linha["unidade_orig"],
                classe=linha["classe"], coeficiente=coeficiente,
                coeficiente_acumulado=acumulado,
                custo_unitario=linha["custo_unitario"], nivel=nivel,
                caminho=caminho, origem_pai=origem, codigo_pai=codigo)

            if linha["classe"] == "COMPOSICAO_AUXILIAR":
                self._expandir_auxiliar(
                    no, acumulado=acumulado, nivel=nivel, caminho=caminho,
                    visitados=visitados, resultado=resultado,
                    profundidade_maxima=profundidade_maxima)
            nos.append(no)
        return nos

    def _expandir_auxiliar(
        self,
        no: NoInsumo,
        *,
        acumulado: float,
        nivel: int,
        caminho: tuple[str, ...],
        visitados: set[tuple[str, str]],
        resultado: ComposicaoExpandida,
        profundidade_maxima: int,
    ) -> None:
        """Resolve uma composição auxiliar, com todas as guardas."""
        auxiliar = self.localizar_auxiliar(no.codins)

        if auxiliar is None:
            no.pendencia = "AUXILIAR_NAO_LOCALIZADA"
            no.detalhe_pendencia = (
                f"CODINS {no.codins} está classificado como composição "
                f"auxiliar mas não foi encontrado em nenhuma base.")
            self._registrar_pendencia(resultado, no)
            return

        # Auxiliar percentual: o coeficiente é um percentual sobre material e
        # mão de obra, não uma quantidade física. Multiplicar coeficientes
        # produziria um número sem significado — vira pendência (item 67).
        if auxiliar["unidade"] == UNIDADE_PERCENTUAL:
            no.pendencia = "AUXILIAR_PERCENTUAL"
            no.detalhe_pendencia = (
                f"A auxiliar {auxiliar['origem']} {auxiliar['codigo']} é "
                f"percentual sobre material e mão de obra (unidade '%'). "
                f"Não é expansível por multiplicação de coeficiente; "
                f"requer definição do usuário.")
            self._registrar_pendencia(resultado, no)
            return

        chave = (auxiliar["origem"], auxiliar["codigo"])
        if chave in visitados:
            no.pendencia = "CICLO_DE_COMPOSICAO"
            no.detalhe_pendencia = (
                f"Ciclo detectado: {auxiliar['origem']} {auxiliar['codigo']} "
                f"já aparece no caminho {' > '.join(caminho)}.")
            self._registrar_pendencia(resultado, no)
            return

        if nivel + 1 >= profundidade_maxima:
            no.pendencia = "PROFUNDIDADE_EXCEDIDA"
            no.detalhe_pendencia = (
                f"Profundidade máxima ({profundidade_maxima}) atingida em "
                f"{auxiliar['origem']} {auxiliar['codigo']}.")
            self._registrar_pendencia(resultado, no)
            return

        novo_caminho = caminho + (f"{auxiliar['origem']} {auxiliar['codigo']}",)
        no.filhos = self._expandir_nivel(
            auxiliar["origem"], auxiliar["codigo"],
            fator=acumulado, nivel=nivel + 1, caminho=novo_caminho,
            visitados=visitados | {chave},
            resultado=resultado, profundidade_maxima=profundidade_maxima)
        no.expandido = True
        resultado.auxiliares_expandidas += 1

    def _registrar_pendencia(self, resultado: ComposicaoExpandida, no: NoInsumo) -> None:
        resultado.pendencias.append({
            "tipo": no.pendencia,
            "codins": no.codins,
            "descricao": no.descricao,
            "detalhe": no.detalhe_pendencia,
            "caminho": no.descricao_caminho(),
        })

    # --------------------------------------------------------- consolidação
    @staticmethod
    def _consolidar(arvore: list[NoInsumo]) -> list[ItemConsolidado]:
        """Achata a árvore somando coeficientes acumulados por insumo.

        Um insumo que aparece por caminhos diferentes (item 7 dos testes)
        tem os coeficientes SOMADOS, e todos os caminhos são preservados.
        Uma auxiliar expandida não entra: quem entra são as folhas dela,
        senão o custo seria contado duas vezes.
        """
        acumulador: dict[tuple[str, str], ItemConsolidado] = {}
        for raiz in arvore:
            for no in raiz.percorrer():
                if no.expandido:
                    continue          # substituída pelos próprios filhos
                if no.classe == "COMPOSICAO_AUXILIAR" and no.pendencia:
                    continue          # não expandida: vira pendência, não custo
                chave = (no.codins, no.unidade)
                existente = acumulador.get(chave)
                if existente is None:
                    acumulador[chave] = ItemConsolidado(
                        codins=no.codins, descricao=no.descricao,
                        unidade=no.unidade, unidade_orig=no.unidade_orig,
                        classe=no.classe,
                        coeficiente=no.coeficiente_acumulado,
                        custo_unitario=no.custo_unitario,
                        caminhos=[no.descricao_caminho()])
                else:
                    existente.coeficiente += no.coeficiente_acumulado
                    existente.ocorrencias += 1
                    caminho = no.descricao_caminho()
                    if caminho not in existente.caminhos:
                        existente.caminhos.append(caminho)
        ordem = {"MAO_DE_OBRA": 0, "MATERIAL": 1, "EQUIPAMENTO": 2, "OUTRO": 3}
        return sorted(acumulador.values(),
                      key=lambda i: (ordem.get(i.classe, 9), -i.custo))
