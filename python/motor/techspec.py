"""Extração de atributos técnicos de descrições (itens 10, 11 e 24).

O objetivo não é entender a frase, e sim capturar os discriminantes que
decidem se dois itens são tecnicamente o mesmo: dimensão, espessura,
diâmetro, resistência, classe, bitola, norma, ação executiva.

Estes atributos alimentam duas coisas:
  * o componente `tecnico` do score;
  * as PENALIZAÇÕES por conflito (item 11) — dois itens semanticamente
    parecidos mas com dimensões diferentes têm o score derrubado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .normalize import normalizar_texto, normalizar_unidade

_NUM = r"\d{1,5}(?:[.,]\d{1,4})?"


def _f(txt: str) -> float | None:
    try:
        return float(txt.replace(",", "."))
    except (ValueError, AttributeError):
        return None


# ------------------------------------------------------------ ação executiva
# Ações mutuamente excludentes: execução x demolição, fornecimento x instalação.
ACOES = {
    "DEMOLICAO": r"\bDEMOLI\w*|\bDEMOL\b",
    "REMOCAO": r"\bREMOCAO\b|\bREMOVER\b|\bRETIRADA\b|\bRETIRAR\b",
    "DESMONTAGEM": r"\bDESMONTAGEM\b|\bDESMONTAR\b",
    "RECUPERACAO": r"\bRECUPERACAO\b|\bREPARO\b|\bRESTAURA\w*|\bREFORMA\b",
    "FORNECIMENTO": r"\bFORNECIMENTO\b|\bFORNEC\w*",
    "INSTALACAO": r"\bINSTALACAO\b|\bCOLOCACAO\b|\bASSENTAMENTO\b|\bMONTAGEM\b|\bAPLICACAO\b",
    "EXECUCAO": r"\bEXECUCAO\b|\bEXECUTAR\b|\bCONSTRUCAO\b",
    "LOCACAO": r"\bLOCACAO\b|\bALUGUEL\b",
    "TRANSPORTE": r"\bTRANSPORTE\b|\bCARGA\b|\bDESCARGA\b",
    "ESCAVACAO": r"\bESCAVACAO\b|\bESCAVAR\b",
    "PINTURA": r"\bPINTURA\b|\bPINTAR\b",
    "LIMPEZA": r"\bLIMPEZA\b",
}

# Pares que se contradizem: se um item tem A e o outro tem B, são serviços
# diferentes ainda que descrevam o mesmo elemento construtivo.
ACOES_CONFLITANTES = [
    ({"DEMOLICAO", "REMOCAO", "DESMONTAGEM"}, {"EXECUCAO", "INSTALACAO", "FORNECIMENTO"}),
    ({"LOCACAO"}, {"EXECUCAO", "INSTALACAO", "FORNECIMENTO", "DEMOLICAO"}),
]

# ------------------------------------------------------------------ materiais
MATERIAIS = {
    "CONCRETO": r"\bCONCRETO\b",
    "ARGAMASSA": r"\bARGAMASSA\b",
    "ACO": r"\bACO\b|\bCA-?\s?[2567]0\b|\bFERRO\b|\bVERGALHAO\b",
    "MADEIRA": r"\bMADEIRA\b|\bCOMPENSADO\b|\bPINUS\b|\bPEROBA\b|\bCEDRIN\w*",
    "CERAMICO": r"\bCERAMIC\w*|\bAZULEJO\b|\bPASTILHA\b|\bPORCELANATO\b",
    "BLOCO_CONCRETO": r"\bBLOCO\w*\s+(?:DE\s+)?CONCRETO\b|\bBLOCO\w*\s+ESTRUTURAL\b",
    "BLOCO_CERAMICO": r"\bBLOCO\w*\s+(?:DE\s+)?CERAMIC\w*",
    "TIJOLO": r"\bTIJOLO\w*",
    "PVC": r"\bPVC\b|\bCPVC\b",
    "COBRE": r"\bCOBRE\b",
    "ALUMINIO": r"\bALUMINIO\b",
    "GALVANIZADO": r"\bGALVANIZAD\w*|\bZINCAD\w*",
    "GESSO": r"\bGESSO\b|\bDRYWALL\b|\bACARTONAD\w*",
    "VIDRO": r"\bVIDRO\b|\bCRISTAL\b",
    "ASFALTO": r"\bASFALT\w*|\bCBUQ\b|\bCAUQ\b|\bEMULSAO ASFALTICA\b",
    "BRITA": r"\bBRITA\b|\bPEDRA BRITADA\b|\bPEDRISCO\b",
    "AREIA": r"\bAREIA\b",
    "CIMENTO": r"\bCIMENTO\b|\bCP\s?I{1,3}\b|\bCPI{1,3}\b",
    "CAL": r"\bCAL\b|\bCALCARIO\b",
    "TINTA": r"\bTINTA\b|\bESMALTE\b|\bLATEX\b|\bACRILIC\w*",
    "GRANITO": r"\bGRANITO\b",
    "MARMORE": r"\bMARMORE\b",
    "BORRACHA": r"\bBORRACHA\b",
    "FIBROCIMENTO": r"\bFIBROCIMENTO\b|\bFIBRO-CIMENTO\b",
    "ASBESTO": r"\bAMIANTO\b|\bASBESTO\b",
    "GRANILITE": r"\bGRANILITE\b|\bGRANITINA\b",
    "ELASTOMERO": r"\bELASTOMER\w*|\bPOLIURETAN\w*|\bEPOXI\w*",
}

# Materiais que se excluem mutuamente (item 11): um bloco de concreto não é
# um bloco cerâmico, ainda que a frase seja quase idêntica.
GRUPOS_EXCLUDENTES = [
    {"BLOCO_CONCRETO", "BLOCO_CERAMICO", "TIJOLO"},
    {"PVC", "COBRE", "ACO", "GALVANIZADO", "ALUMINIO"},
    {"MADEIRA", "ALUMINIO", "PVC", "ACO"},
    {"CERAMICO", "GRANITO", "MARMORE", "GRANILITE", "MADEIRA"},
    {"AREIA", "BRITA", "CIMENTO", "CAL"},
]


@dataclass
class Spec:
    """Atributos técnicos extraídos de uma descrição."""

    texto_norm: str = ""
    unidade: str = ""
    acoes: set[str] = field(default_factory=set)
    materiais: set[str] = field(default_factory=set)
    espessura_cm: float | None = None
    diametro_mm: float | None = None
    diametro_pol: float | None = None
    fck_mpa: float | None = None
    classe_aco: str = ""
    dimensoes_cm: tuple[float, ...] = ()
    comprimento_m: float | None = None
    normas: set[str] = field(default_factory=set)
    tracos: set[str] = field(default_factory=set)
    classe_cimento: str = ""
    potencia: float | None = None
    abrangente: bool = False
    numeros: set[float] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "acoes": sorted(self.acoes),
            "materiais": sorted(self.materiais),
            "espessura_cm": self.espessura_cm,
            "diametro_mm": self.diametro_mm,
            "diametro_pol": self.diametro_pol,
            "fck_mpa": self.fck_mpa,
            "classe_aco": self.classe_aco,
            "classe_cimento": self.classe_cimento,
            "dimensoes_cm": list(self.dimensoes_cm),
            "comprimento_m": self.comprimento_m,
            "normas": sorted(self.normas),
            "tracos": sorted(self.tracos),
        }


# ------------------------------------------------------------------ regexes

_RE_ESPESSURA = re.compile(
    rf"(?:\bE\s*[=:]\s*|\bESP\w*\.?\s*[=:]?\s*|\bESPESSURA\s+(?:DE\s+)?)({_NUM})\s*(CM|MM|M)?\b")
_RE_ESP_SUFIXO = re.compile(rf"({_NUM})\s*(CM|MM)\s+DE\s+ESPESSURA\b")
_RE_DIAM = re.compile(rf"(?:\bD\s*[=:]?\s*|\bDIAM\w*\.?\s*[=:]?\s*|\bDN\s*)({_NUM})\s*(MM|CM|M|\")?")
_RE_POL = re.compile(rf"({_NUM})\s*(?:\"|\bPOL\b|\bPOLEGADAS?\b)")
_RE_POL_FRAC = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*(?:\"|\bPOL\b)")
_RE_POL_MISTA = re.compile(r"\b(\d{1,2})\s+(\d{1,2})\s*/\s*(\d{1,2})\s*(?:\"|\bPOL\b)")
_RE_FCK = re.compile(rf"\bF\s*C\s*K\s*[=:]?\s*({_NUM})\s*(?:MPA)?|\b({_NUM})\s*MPA\b")
_RE_CA = re.compile(r"\bCA[\s\-]?(25|50|60)\b")
# Tipo de cimento Portland: CP-II, CPII-E, CP-V ARI, ... O tipo muda a
# aplicação e o preço, então é discriminante técnico, não sinônimo.
_RE_CP = re.compile(r"\bCP\s*[\-]?\s*(I{1,3}V?|IV|V)\b")
_RE_NORMA = re.compile(r"\b(?:NBR|ABNT|DIN|ASTM|EB|NB)\s*[\-]?\s*(\d{3,5})\b")
_RE_TRACO = re.compile(r"\b(\d{1,2})\s*:\s*(\d{1,2})(?:\s*:\s*(\d{1,2}))?\b")
_RE_DIMS = re.compile(rf"({_NUM})\s*[X]\s*({_NUM})(?:\s*[X]\s*({_NUM}))?\s*(CM|MM|M)?\b")
_RE_COMPR = re.compile(rf"({_NUM})\s*(?:M|METROS?)\b(?!\s*[23])")
_RE_BLOCO_MED = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*(CM)?\b")
# Medida solta com unidade explícita ("BLOCO 14 CM"). Em elemento planar
# — bloco, tijolo, chapa, placa — essa medida É a espessura, ainda que a
# descrição não traga "E=" ou "ESP". Sem isso, "bloco 14cm" e "bloco 19cm"
# seriam indistinguíveis (item 11).
_RE_DIM_SOLTA = re.compile(rf"(?<![A-Z0-9/])({_NUM})\s*(CM|MM)\b")
_MATERIAIS_PLANARES = {"BLOCO_CONCRETO", "BLOCO_CERAMICO", "TIJOLO", "GESSO",
                       "CERAMICO", "MADEIRA", "VIDRO", "GRANILITE"}
_RE_NUM_SOLTO = re.compile(rf"(?<![A-Z0-9]){_NUM}(?![A-Z0-9])")


def _para_cm(valor: float, unidade: str | None) -> float:
    if unidade == "MM":
        return valor / 10.0
    if unidade == "M":
        return valor * 100.0
    return valor


def extrair(descricao: str, unidade: str = "") -> Spec:
    """Extrai os atributos técnicos de uma descrição."""
    t = normalizar_texto(descricao)
    spec = Spec(texto_norm=t, unidade=normalizar_unidade(unidade))

    for nome, padrao in ACOES.items():
        if re.search(padrao, t):
            spec.acoes.add(nome)
    for nome, padrao in MATERIAIS.items():
        if re.search(padrao, t):
            spec.materiais.add(nome)
    # Descrições internas frequentemente enumeram alternativas
    # ("BLOCOS CERÂMICOS OU CONCRETO"): o serviço cobre as duas variantes.
    # Ambas precisam ser registradas, senão a enumeração seria lida como
    # conflito de material contra uma referência específica.
    if re.search(r"\bBLOCO\w*", t):
        if re.search(MATERIAIS["CONCRETO"], t):
            spec.materiais.add("BLOCO_CONCRETO")
        if re.search(MATERIAIS["CERAMICO"], t):
            spec.materiais.add("BLOCO_CERAMICO")
    # "BLOCO DE CONCRETO" também casa CONCRETO; o específico manda.
    if "BLOCO_CONCRETO" in spec.materiais:
        spec.materiais.discard("CONCRETO")
    if "BLOCO_CERAMICO" in spec.materiais:
        spec.materiais.discard("CERAMICO")
    # Enumeração de alternativas — usada pela comparação para não punir
    # um serviço genérico que legitimamente cobre várias variantes.
    spec.abrangente = bool(re.search(r"\bOU\b|\bE/OU\b", t))

    # Espessura
    m = _RE_ESPESSURA.search(t) or _RE_ESP_SUFIXO.search(t)
    if m:
        val = _f(m.group(1))
        if val is not None:
            grupos = m.groups()
            und = grupos[1] if len(grupos) > 1 else None
            spec.espessura_cm = _para_cm(val, und)

    # Diâmetro em polegadas (fracionário, misto ou decimal)
    mm_ = _RE_POL_MISTA.search(t)
    if mm_:
        inteiro, num, den = int(mm_.group(1)), int(mm_.group(2)), int(mm_.group(3))
        if den:
            spec.diametro_pol = inteiro + num / den
    else:
        mf = _RE_POL_FRAC.search(t)
        if mf and int(mf.group(2)):
            spec.diametro_pol = int(mf.group(1)) / int(mf.group(2))
        else:
            mp = _RE_POL.search(t)
            if mp:
                spec.diametro_pol = _f(mp.group(1))
    if spec.diametro_pol:
        spec.diametro_mm = round(spec.diametro_pol * 25.4, 2)

    # Diâmetro métrico (D=, DN, DIAM)
    md = _RE_DIAM.search(t)
    if md and spec.diametro_mm is None:
        val = _f(md.group(1))
        if val is not None:
            und = md.group(2)
            if und == "CM":
                spec.diametro_mm = val * 10
            elif und == "M":
                spec.diametro_mm = val * 1000
            elif und == '"':
                spec.diametro_pol = val
                spec.diametro_mm = round(val * 25.4, 2)
            else:
                spec.diametro_mm = val

    # fck
    mfck = _RE_FCK.search(t)
    if mfck:
        spec.fck_mpa = _f(mfck.group(1) or mfck.group(2) or "")

    mca = _RE_CA.search(t)
    if mca:
        spec.classe_aco = f"CA{mca.group(1)}"

    if "CIMENTO" in spec.materiais:
        mcp = _RE_CP.search(t)
        if mcp:
            spec.classe_cimento = f"CP{mcp.group(1)}"

    spec.normas = {f"NBR{m.group(1)}" for m in _RE_NORMA.finditer(t)}

    for m in _RE_TRACO.finditer(t):
        partes = [p for p in m.groups() if p]
        spec.tracos.add(":".join(partes))

    # Medidas de bloco no formato 09/14/19
    mb = _RE_BLOCO_MED.search(t)
    if mb:
        spec.dimensoes_cm = tuple(sorted(float(g) for g in mb.groups()[:3] if g))
    else:
        md2 = _RE_DIMS.search(t)
        if md2:
            und = md2.group(4)
            vals = [_f(g) for g in md2.groups()[:3] if g]
            vals = [v for v in vals if v is not None]
            if vals:
                if und is None:
                    und = "CM" if max(vals) >= 10 else "M"
                spec.dimensoes_cm = tuple(sorted(_para_cm(v, und) for v in vals))

    # Medidas soltas com unidade, quando nenhum padrão dimensional casou.
    # Cada fato técnico é registrado UMA única vez: uma medida já explicada
    # pelo diâmetro ou promovida a espessura não vira também "dimensão",
    # para não ser penalizada duas vezes na comparação.
    if not spec.dimensoes_cm:
        soltas: list[float] = []
        for m in _RE_DIM_SOLTA.finditer(t):
            val = _f(m.group(1))
            if val is None or val <= 0:
                continue
            cm = _para_cm(val, m.group(2))
            if 0 < cm <= 500:
                soltas.append(cm)
        if spec.diametro_mm is not None:
            diam_cm = spec.diametro_mm / 10.0
            soltas = [v for v in soltas if abs(v - diam_cm) > 1e-6]
        if spec.espessura_cm is not None:
            soltas = [v for v in soltas if abs(v - spec.espessura_cm) > 1e-6]
        unicas = sorted(set(soltas))
        if unicas:
            if (spec.espessura_cm is None and len(unicas) == 1
                    and spec.materiais & _MATERIAIS_PLANARES):
                # Medida única em elemento planar É a espessura.
                spec.espessura_cm = unicas[0]
            else:
                spec.dimensoes_cm = tuple(unicas)

    mc = _RE_COMPR.search(t)
    if mc:
        val = _f(mc.group(1))
        if val is not None and 0 < val <= 100:
            spec.comprimento_m = val

    spec.numeros = {v for v in (_f(m.group(0)) for m in _RE_NUM_SOLTO.finditer(t))
                    if v is not None}
    return spec


# ----------------------------------------------------------- comparação

@dataclass
class Comparacao:
    """Resultado da comparação técnica entre duas specs."""

    score: float = 1.0           # 0..1 — componente técnico do score final
    penalidades: list[str] = field(default_factory=list)
    reforcos: list[str] = field(default_factory=list)
    conflito_grave: bool = False

    def registrar(self, fator: float, motivo: str, grave: bool = False) -> None:
        self.score *= fator
        self.penalidades.append(motivo)
        if grave:
            self.conflito_grave = True


def _prox(a: float, b: float, tol: float = 0.02) -> bool:
    if a is None or b is None:
        return False
    if a == b:
        return True
    maior = max(abs(a), abs(b))
    return maior > 0 and abs(a - b) / maior <= tol


def comparar(a: Spec, b: Spec) -> Comparacao:
    """Compara duas specs e devolve score técnico + explicação.

    Conflitos técnicos derrubam o score (item 11). Coincidências
    técnicas reforçam. Ausência de informação é neutra — nunca inventa.
    """
    c = Comparacao()

    # --- ação executiva
    for grupo_x, grupo_y in ACOES_CONFLITANTES:
        ax, ay = a.acoes & grupo_x, a.acoes & grupo_y
        bx, by = b.acoes & grupo_x, b.acoes & grupo_y
        if (ax and by and not ay and not bx) or (ay and bx and not ax and not by):
            c.registrar(0.25, f"Ações incompatíveis: {sorted(a.acoes & (grupo_x | grupo_y))} "
                              f"x {sorted(b.acoes & (grupo_x | grupo_y))}", grave=True)
            break

    # --- material
    if a.materiais and b.materiais:
        if a.materiais & b.materiais:
            c.reforcos.append(f"Material coincidente: {sorted(a.materiais & b.materiais)}")
        else:
            conflitou = False
            for grupo in GRUPOS_EXCLUDENTES:
                ga, gb = a.materiais & grupo, b.materiais & grupo
                if ga and gb and not (ga & gb):
                    c.registrar(0.35, f"Materiais excludentes: {sorted(ga)} x {sorted(gb)}",
                                grave=True)
                    conflitou = True
                    break
            if not conflitou:
                c.registrar(0.80, f"Materiais distintos: {sorted(a.materiais)} "
                                  f"x {sorted(b.materiais)}")

    # --- espessura
    if a.espessura_cm is not None and b.espessura_cm is not None:
        if _prox(a.espessura_cm, b.espessura_cm):
            c.reforcos.append(f"Espessura coincidente: {a.espessura_cm:g} cm")
        else:
            razao = min(a.espessura_cm, b.espessura_cm) / max(a.espessura_cm, b.espessura_cm)
            c.registrar(0.30 + 0.45 * razao,
                        f"Espessura divergente: {a.espessura_cm:g} cm x {b.espessura_cm:g} cm",
                        grave=razao < 0.6)

    # --- diâmetro
    if a.diametro_mm is not None and b.diametro_mm is not None:
        if _prox(a.diametro_mm, b.diametro_mm, 0.05):
            c.reforcos.append(f"Diâmetro coincidente: {a.diametro_mm:g} mm")
        else:
            razao = min(a.diametro_mm, b.diametro_mm) / max(a.diametro_mm, b.diametro_mm)
            c.registrar(0.25 + 0.45 * razao,
                        f"Diâmetro divergente: {a.diametro_mm:g} mm x {b.diametro_mm:g} mm",
                        grave=razao < 0.7)

    # --- fck
    if a.fck_mpa is not None and b.fck_mpa is not None:
        if _prox(a.fck_mpa, b.fck_mpa):
            c.reforcos.append(f"fck coincidente: {a.fck_mpa:g} MPa")
        else:
            razao = min(a.fck_mpa, b.fck_mpa) / max(a.fck_mpa, b.fck_mpa)
            c.registrar(0.30 + 0.40 * razao,
                        f"Resistência divergente: fck {a.fck_mpa:g} x {b.fck_mpa:g} MPa",
                        grave=razao < 0.75)

    # --- classe do aço
    if a.classe_aco and b.classe_aco:
        if a.classe_aco == b.classe_aco:
            c.reforcos.append(f"Classe do aço coincidente: {a.classe_aco}")
        else:
            c.registrar(0.35, f"Classe do aço divergente: {a.classe_aco} x {b.classe_aco}",
                        grave=True)

    # --- tipo de cimento Portland
    if a.classe_cimento and b.classe_cimento:
        if a.classe_cimento == b.classe_cimento:
            c.reforcos.append(f"Tipo de cimento coincidente: {a.classe_cimento}")
        else:
            c.registrar(0.45, f"Tipo de cimento divergente: "
                              f"{a.classe_cimento} x {b.classe_cimento}")

    # --- dimensões (porcelanato 60x60 x 90x90)
    if a.dimensoes_cm and b.dimensoes_cm:
        if a.dimensoes_cm == b.dimensoes_cm:
            c.reforcos.append(f"Dimensões coincidentes: {a.dimensoes_cm}")
        elif set(a.dimensoes_cm) & set(b.dimensoes_cm):
            c.registrar(0.85, f"Dimensões parcialmente coincidentes: "
                              f"{a.dimensoes_cm} x {b.dimensoes_cm}")
        elif a.abrangente or b.abrangente:
            c.registrar(0.75, f"Dimensões divergentes, mas a descrição enumera "
                              f"alternativas: {a.dimensoes_cm} x {b.dimensoes_cm}")
        else:
            c.registrar(0.45, f"Dimensões divergentes: {a.dimensoes_cm} x {b.dimensoes_cm}")

    # --- traço da argamassa
    if a.tracos and b.tracos:
        if a.tracos & b.tracos:
            c.reforcos.append(f"Traço coincidente: {sorted(a.tracos & b.tracos)}")
        else:
            c.registrar(0.70, f"Traço divergente: {sorted(a.tracos)} x {sorted(b.tracos)}")

    # --- norma técnica (só reforça; ausência não pune)
    if a.normas and b.normas and (a.normas & b.normas):
        c.reforcos.append(f"Norma coincidente: {sorted(a.normas & b.normas)}")

    c.score = max(0.0, min(1.0, c.score))
    return c
