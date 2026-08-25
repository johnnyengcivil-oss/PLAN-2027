"""Normalização de texto, códigos, unidades e números (item 42).

Princípio: o texto original NUNCA é destruído. A normalização produz uma
representação paralela usada só para comparação; a descrição original
permanece intacta no banco e na interface.
"""
from __future__ import annotations

import re
import unicodedata

# Unidades canônicas. A chave é a forma já "achatada" (sem acento, maiúscula,
# sem espaços/pontos); o valor é a forma canônica do sistema.
_MAPA_UNIDADES = {
    # área
    "M2": "M2", "M²": "M2", "MT2": "M2", "METROQUADRADO": "M2",
    "M2XKM": "M2XKM",
    # volume
    "M3": "M3", "M³": "M3", "MT3": "M3", "METROCUBICO": "M3",
    "M3XKM": "M3XKM", "DM3": "DM3",
    # comprimento
    "M": "M", "MT": "M", "METRO": "M", "ML": "M", "MTS": "M",
    "CM": "CM", "MM": "MM", "KM": "KM",
    # massa
    "KG": "KG", "QUILO": "KG", "QUILOGRAMA": "KG",
    "G": "G", "GRAMA": "G",
    "T": "TON", "TON": "TON", "TN": "TON", "TONELADA": "TON",
    # volume líquido
    "L": "L", "LT": "L", "LITRO": "L", "LTS": "L",
    # tempo
    "H": "H", "HR": "H", "HORA": "H", "HS": "H",
    "DIA": "DIA", "DD": "DZ", "MES": "MES", "MS": "MES",
    # contagem / embalagem
    "UN": "UN", "UND": "UN", "UNID": "UN", "UNIDADE": "UN", "PC": "UN",
    "PECA": "UN", "PÇ": "UN",
    "CJ": "CJ", "CONJ": "CJ", "CONJUNTO": "CJ",
    "JG": "JG", "JOGO": "JG",
    "PAR": "PAR",
    "DZ": "DZ", "DUZIA": "DZ",
    "MIL": "MIL", "MILHEIRO": "MIL",
    "SC": "SC", "SACO": "SC",
    "BR": "BR", "BARRA": "BR",
    "LA": "LA", "LATA": "LA",
    "GL": "GL", "GALAO": "GL",
    "RL": "RL", "ROLO": "RL",
    "CX": "CX", "CAIXA": "CX",
    "CT": "CT", "CARTELA": "CT",
    "FD": "FD", "FARDO": "FD",
    "BS": "BS", "BISNAGA": "BS",
    "TB": "TB", "TUBO": "TB",
    "VB": "VB", "VG": "VB", "VERBA": "VB",
    "PT": "PT", "POTE": "PT",
    # outros
    "%": "PCT", "PORC": "PCT",
    "ENS": "ENS", "ENS.": "ENS",
    "HA": "HA", "KM2": "KM2", "UM": "UN",
    "GLB": "VB", "GLOBAL": "VB",
}

# Unidades cuja conversão depende do produto (item 26). Nunca convertidas
# por regra global.
UNIDADES_EMBALAGEM = {
    "SC", "BR", "LA", "GL", "RL", "CX", "CT", "FD", "BS", "TB", "PT", "CJ", "JG",
}

# Unidades sem grandeza física definida — não convertem nunca.
UNIDADES_ABSTRATAS = {"VB", "PCT", "ENS"}

_RE_ESPACOS = re.compile(r"\s+")
_RE_NAO_ALFANUM = re.compile(r"[^0-9A-Za-z]+")


def limpar_espacos(texto: object) -> str:
    """Remove no-break spaces, colapsa espaços e apara as pontas."""
    if texto is None:
        return ""
    s = str(texto).replace("\xa0", " ").replace(" ", " ").replace(" ", " ")
    return _RE_ESPACOS.sub(" ", s).strip()


def sem_acento(texto: str) -> str:
    """Remove acentuação preservando as letras."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar_texto(texto: object) -> str:
    """Forma de comparação: sem acento, maiúscula, espaçamento colapsado.

    Preserva dígitos, letras e os símbolos tecnicamente relevantes
    (x, /, ", ., ,, -, %, º) porque carregam dimensão e classe.
    """
    s = limpar_espacos(texto)
    if not s:
        return ""
    s = sem_acento(s).upper()
    # Sinais tipográficos que aparecem nas bases.
    s = (s.replace("Ø", "D").replace("ø", "D")
           .replace("“", '"').replace("”", '"').replace("''", '"')
           .replace("²", "2").replace("³", "3"))
    s = re.sub(r"[^0-9A-Z%\"'./,\-x×X: ]+", " ", s)
    s = s.replace("×", "X")
    return _RE_ESPACOS.sub(" ", s).strip()


def chave_comparacao(texto: object) -> str:
    """Chave agressiva (só alfanumérico) para deduplicação e cache."""
    return _RE_NAO_ALFANUM.sub("", sem_acento(limpar_espacos(texto)).upper())


def tokens(texto: object) -> list[str]:
    """Tokens alfanuméricos da forma normalizada, para similaridade lexical."""
    norm = normalizar_texto(texto)
    brutos = re.split(r"[^0-9A-Z%\"]+", norm)
    return [t for t in brutos if t]


def normalizar_unidade(unidade: object) -> str:
    """Canonicaliza uma unidade. `M2`, `M²`, `m 2` → `M2`."""
    s = limpar_espacos(unidade)
    if not s:
        return ""
    if s.strip() == "%":
        return "PCT"
    bruto = sem_acento(s).upper().replace(" ", "")
    bruto = bruto.replace("²", "2").replace("³", "3")
    # Preserva o "%" antes de remover pontuação.
    tem_pct = "%" in bruto
    bruto = bruto.replace(".", "").replace("%", "")
    if tem_pct and not bruto:
        return "PCT"
    if bruto in _MAPA_UNIDADES:
        return _MAPA_UNIDADES[bruto]
    # "M 2" já virou "M2"; tenta ainda separar dígito final (ex.: "MT2").
    sem_dig = re.sub(r"\d+$", "", bruto)
    if bruto not in _MAPA_UNIDADES and sem_dig in _MAPA_UNIDADES and not bruto[-1:].isdigit():
        return _MAPA_UNIDADES[sem_dig]
    return bruto


def normalizar_codigo(codigo: object) -> str:
    """Preserva zeros à esquerda e remove sujeira de float do Excel.

    O Excel devolve códigos numéricos como float (`140006.0`); a parte
    decimal nula é descartada, mas `007` continua `007`.
    """
    if codigo is None:
        return ""
    if isinstance(codigo, float):
        if codigo == int(codigo):
            return str(int(codigo))
        return repr(codigo)
    if isinstance(codigo, int):
        return str(codigo)
    s = limpar_espacos(codigo)
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s


def para_numero(valor: object) -> float | None:
    """Converte número em qualquer notação (pt-BR ou internacional).

    Trata `"R$ 1.234,56"` → 1234.56 e `"5.84"` → 5.84.
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = limpar_espacos(valor)
    if not s:
        return None
    s = re.sub(r"(?i)\b(r\$|rs)\b", "", s).replace("R$", "").strip()
    s = s.replace("−", "-")
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in {"-", ".", ","}:
        return None
    tem_ponto, tem_virgula = "." in s, "," in s
    if tem_ponto and tem_virgula:
        # O último separador é o decimal.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif tem_virgula:
        # Vírgula é decimal, salvo quando é claramente separador de milhar
        # (grupos de exatamente 3 dígitos: "1,234,567").
        partes = s.split(",")
        if len(partes) > 2 and all(len(p) == 3 for p in partes[1:]):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif tem_ponto:
        partes = s.split(".")
        if len(partes) > 2 and all(len(p) == 3 for p in partes[1:]):
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None
