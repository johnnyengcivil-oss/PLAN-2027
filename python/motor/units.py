"""Conversão de unidades — determinística, nunca por IA (itens 25 a 27).

Três níveis, do mais seguro ao mais específico:

1. Conversão dimensional universal (t↔kg, m³↔L, cm↔m). Sempre válida.
2. Conversão de contagem (MIL = 1000 UN, DZ = 12 UN). Válida sempre, pois
   são multiplicadores puros de contagem.
3. Conversão dependente do produto (SC→KG, BR→M, peça→M2). NUNCA aplicada
   por regra global. Só ocorre quando há regra cadastrada para o material
   ou quando o próprio texto declara o conteúdo (ex.: "cimento ... 50kg").
   Sem isso, devolve pendência CONVERSAO_PENDENTE.

Toda conversão devolve um objeto `Conversao` que registra o fator, o método
e a justificativa — insumo direto da rastreabilidade do item 31.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .normalize import (
    UNIDADES_ABSTRATAS,
    UNIDADES_EMBALAGEM,
    UNIDADES_PERIODO,
    normalizar_texto,
    normalizar_unidade,
)

# ------------------------------------------------------------------ grandezas

MASSA = {"G": 0.001, "KG": 1.0, "TON": 1000.0}
COMPRIMENTO = {"MM": 0.001, "CM": 0.01, "M": 1.0, "KM": 1000.0}
AREA = {"M2": 1.0, "CM2": 0.0001, "HA": 10000.0, "KM2": 1_000_000.0}
VOLUME = {"L": 0.001, "DM3": 0.001, "M3": 1.0, "CM3": 1e-6}
TEMPO = {"H": 1.0}   # períodos de locação ficam fora: ver UNIDADES_PERIODO
CONTAGEM = {"UN": 1.0, "DZ": 12.0, "MIL": 1000.0, "PAR": 2.0}

_GRANDEZAS: dict[str, dict[str, float]] = {
    "MASSA": MASSA, "COMPRIMENTO": COMPRIMENTO, "AREA": AREA,
    "VOLUME": VOLUME, "TEMPO": TEMPO, "CONTAGEM": CONTAGEM,
}

# Unidades compostas de transporte — só convertem entre si mesmas.
_COMPOSTAS = {"M3XKM", "M2XKM"}


def grandeza_de(unidade: str) -> str | None:
    """Grandeza física de uma unidade canônica, se houver."""
    u = normalizar_unidade(unidade)
    for nome, tabela in _GRANDEZAS.items():
        if u in tabela:
            return nome
    return None


@dataclass
class Conversao:
    """Resultado de uma tentativa de conversão."""

    ok: bool
    fator: float = 1.0
    metodo: str = ""          # IDENTIDADE | DIMENSIONAL | CONTAGEM | REGRA_PRODUTO | TEXTO_PRODUTO
    justificativa: str = ""
    pendencia: str = ""       # CONVERSAO_PENDENTE | UNIDADE_INCOMPATIVEL
    detalhes: dict[str, Any] = field(default_factory=dict)

    def aplicar(self, quantidade: float) -> float:
        return quantidade * self.fator


def _falha(pendencia: str, msg: str, **det: Any) -> Conversao:
    return Conversao(ok=False, metodo="", justificativa=msg,
                     pendencia=pendencia, detalhes=det)


# ------------------------------------------------- extração de conteúdo do texto

# "50 KG", "3,6 L", "18 LITROS", "12,00 M", "20KG"
_RE_CONTEUDO = re.compile(
    r"(?<![\d,.])(\d{1,5}(?:[.,]\d{1,3})?)\s*"
    r"(KGS|KG|QUILOS?|GRAMAS?|G|LITROS?|LTS|LT|ML|L|M3|M2|MM|CM|M|"
    r"UNIDADES?|UN|PECAS?)\b"
)

_ALIAS_CONTEUDO = {
    "KGS": "KG", "QUILO": "KG", "QUILOS": "KG", "GRAMA": "G", "GRAMAS": "G",
    "LT": "L", "LTS": "L", "LITRO": "L", "LITROS": "L",
    "UNIDADE": "UN", "UNIDADES": "UN", "PECA": "UN", "PECAS": "UN",
}


def extrair_conteudo_embalagem(descricao: str, unidade_destino: str) -> tuple[float, str] | None:
    """Procura no texto o conteúdo declarado da embalagem.

    `"CIMENTO PORTLAND CP II-E-32 SACO 50KG"` + destino `KG` → `(50.0, "50 KG")`.
    Só aceita quando a unidade encontrada é da mesma grandeza do destino,
    e só quando há UM candidato — ambiguidade vira pendência.
    """
    destino = normalizar_unidade(unidade_destino)
    g_destino = grandeza_de(destino)
    if not g_destino:
        return None
    texto = normalizar_texto(descricao)
    achados: list[tuple[float, str]] = []
    for m in _RE_CONTEUDO.finditer(texto):
        try:
            valor = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        if valor <= 0:
            continue
        unidade = _ALIAS_CONTEUDO.get(m.group(2), m.group(2))
        if unidade == "ML":
            valor, unidade = valor / 1000.0, "L"
        unidade = normalizar_unidade(unidade)
        if grandeza_de(unidade) != g_destino:
            continue
        tabela = _GRANDEZAS[g_destino]
        equivalente = valor * tabela[unidade] / tabela[destino]
        achados.append((equivalente, f"{m.group(1)} {m.group(2)}"))
    if len(achados) != 1:
        return None
    return achados[0]


# "60X60", "0,60 X 0,60", "30 X 40 CM"
_RE_DIMENSOES = re.compile(
    r"(\d{1,4}(?:[.,]\d{1,3})?)\s*[X]\s*(\d{1,4}(?:[.,]\d{1,3})?)\s*(CM|MM|M)?\b"
)


def area_por_peca(descricao: str) -> tuple[float, str] | None:
    """Área de uma peça a partir das dimensões no texto (item 27).

    `"PORCELANATO 60X60"` → `(0.36, "60X60 cm")`. Sem unidade explícita,
    valores ≥ 10 são interpretados como centímetros e < 10 como metros —
    convenção do setor, registrada na justificativa.
    """
    texto = normalizar_texto(descricao)
    m = _RE_DIMENSOES.search(texto)
    if not m:
        return None
    try:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", "."))
    except ValueError:
        return None
    if a <= 0 or b <= 0:
        return None
    unidade = m.group(3)
    if unidade == "MM":
        fator, rotulo = 0.001, "mm"
    elif unidade == "CM":
        fator, rotulo = 0.01, "cm"
    elif unidade == "M":
        fator, rotulo = 1.0, "m"
    else:
        fator, rotulo = (0.01, "cm (assumido)") if max(a, b) >= 10 else (1.0, "m (assumido)")
    area = (a * fator) * (b * fator)
    if area <= 0:
        return None
    return area, f"{m.group(1)}x{m.group(2)} {rotulo}"


# ------------------------------------------------------------------ API principal

def converter(
    unidade_origem: str,
    unidade_destino: str,
    *,
    descricao_produto: str = "",
    regra_produto: float | None = None,
    origem_regra: str = "",
) -> Conversao:
    """Fator que converte uma quantidade de `unidade_origem` para `unidade_destino`.

    `regra_produto` é o fator já cadastrado em `conversion_rules` para este
    material; quando presente, tem precedência sobre qualquer heurística.
    """
    o = normalizar_unidade(unidade_origem)
    d = normalizar_unidade(unidade_destino)

    if not o or not d:
        return _falha("CONVERSAO_PENDENTE",
                      "Unidade de origem ou destino ausente.",
                      origem=o, destino=d)

    if o == d:
        return Conversao(True, 1.0, "IDENTIDADE",
                         f"Unidades idênticas ({o}).")

    # 1. Regra cadastrada para o produto tem prioridade absoluta.
    if regra_produto is not None and regra_produto > 0:
        return Conversao(True, float(regra_produto), "REGRA_PRODUTO",
                         f"Regra cadastrada: 1 {o} = {regra_produto:g} {d}"
                         + (f" ({origem_regra})" if origem_regra else "."),
                         detalhes={"origem_regra": origem_regra})

    # Período de locação x hora produtiva: decisão da empresa, não física.
    if ({o, d} & UNIDADES_PERIODO) and ({o, d} - UNIDADES_PERIODO):
        periodo = o if o in UNIDADES_PERIODO else d
        return _falha("CONVERSAO_PENDENTE",
                      f"{periodo} é período de locação; a equivalência com "
                      f"{d if periodo == o else o} depende da jornada adotada "
                      f"pela empresa. Cadastre a regra de conversão.",
                      origem=o, destino=d)

    if o in UNIDADES_ABSTRATAS or d in UNIDADES_ABSTRATAS:
        return _falha("UNIDADE_INCOMPATIVEL",
                      f"Unidade sem grandeza física definida ({o} → {d}).",
                      origem=o, destino=d)

    if o in _COMPOSTAS or d in _COMPOSTAS:
        return _falha("UNIDADE_INCOMPATIVEL",
                      f"Unidade composta de transporte não convertível ({o} → {d}).",
                      origem=o, destino=d)

    # 2. Mesma grandeza física → conversão determinística.
    g_o, g_d = grandeza_de(o), grandeza_de(d)
    if g_o and g_o == g_d:
        tabela = _GRANDEZAS[g_o]
        fator = tabela[o] / tabela[d]
        metodo = "CONTAGEM" if g_o == "CONTAGEM" else "DIMENSIONAL"
        return Conversao(True, fator, metodo,
                         f"1 {o} = {fator:g} {d} ({g_o.lower()}).")

    # 3. Embalagem → grandeza física: depende do produto (item 26).
    if o in UNIDADES_EMBALAGEM or d in UNIDADES_EMBALAGEM or "UN" in (o, d):
        return _conversao_dependente_produto(o, d, descricao_produto)

    return _falha("UNIDADE_INCOMPATIVEL",
                  f"Sem conversão determinística entre {o} e {d}.",
                  origem=o, destino=d)


def _conversao_dependente_produto(o: str, d: str, descricao: str) -> Conversao:
    """Tenta deduzir a conversão a partir do texto do próprio produto."""
    if not descricao:
        return _falha("CONVERSAO_PENDENTE",
                      f"Conversão {o} → {d} depende do produto e não há "
                      f"regra cadastrada. Requer definição do usuário.",
                      origem=o, destino=d)

    # Embalagem/unidade → massa, volume ou comprimento declarado no texto.
    if grandeza_de(d) in {"MASSA", "VOLUME", "COMPRIMENTO"}:
        achado = extrair_conteudo_embalagem(descricao, d)
        if achado:
            fator, trecho = achado
            return Conversao(True, fator, "TEXTO_PRODUTO",
                             f"Conteúdo declarado na descrição do produto "
                             f"(\"{trecho}\"): 1 {o} = {fator:g} {d}.",
                             detalhes={"trecho": trecho})

    # Peça/unidade → área, pelas dimensões do produto (item 27).
    if d == "M2" and (o == "UN" or o in UNIDADES_EMBALAGEM):
        achado = area_por_peca(descricao)
        if achado:
            area, trecho = achado
            return Conversao(True, area, "TEXTO_PRODUTO",
                             f"Dimensões da peça ({trecho}): "
                             f"1 {o} = {area:g} M2.",
                             detalhes={"trecho": trecho})

    # Direção inversa (massa/área → embalagem).
    if grandeza_de(o) in {"MASSA", "VOLUME", "COMPRIMENTO"}:
        achado = extrair_conteudo_embalagem(descricao, o)
        if achado and achado[0] > 0:
            fator, trecho = achado
            return Conversao(True, 1.0 / fator, "TEXTO_PRODUTO",
                             f"Conteúdo declarado (\"{trecho}\"): "
                             f"1 {o} = {1.0 / fator:g} {d}.",
                             detalhes={"trecho": trecho})
    if o == "M2" and (d == "UN" or d in UNIDADES_EMBALAGEM):
        achado = area_por_peca(descricao)
        if achado and achado[0] > 0:
            area, trecho = achado
            return Conversao(True, 1.0 / area, "TEXTO_PRODUTO",
                             f"Dimensões da peça ({trecho}): "
                             f"1 M2 = {1.0 / area:g} {d}.",
                             detalhes={"trecho": trecho})

    return _falha("CONVERSAO_PENDENTE",
                  f"Conversão {o} → {d} depende do produto e não pôde ser "
                  f"determinada pela descrição. Requer definição do usuário.",
                  origem=o, destino=d)


def compativel(unidade_a: str, unidade_b: str) -> float:
    """Compatibilidade entre unidades para o score (0,0 a 1,0).

    1,0  idênticas
    0,85 mesma grandeza física (conversão determinística existe)
    0,40 conversão possível mas dependente do produto
    0,0  incompatíveis
    """
    a, b = normalizar_unidade(unidade_a), normalizar_unidade(unidade_b)
    if not a or not b:
        return 0.5           # desconhecido não penaliza nem premia
    if a == b:
        return 1.0
    g_a, g_b = grandeza_de(a), grandeza_de(b)
    if g_a and g_a == g_b:
        return 0.85
    if a in UNIDADES_PERIODO or b in UNIDADES_PERIODO:
        return 0.35          # locação x hora: exige regra da empresa
    if a in UNIDADES_EMBALAGEM or b in UNIDADES_EMBALAGEM:
        return 0.40
    return 0.0
