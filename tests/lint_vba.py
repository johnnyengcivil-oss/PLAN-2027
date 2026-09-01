"""Verificação estrutural dos módulos VBA.

O VBA não é compilado aqui, então esta é a rede de segurança possível:
blocos balanceados e macros de botão que realmente existem. Trata
continuação de linha (`_`), sem a qual um `If` de duas linhas vira falso
positivo.

    python tests/lint_vba.py
"""
from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PASTA = RAIZ / "vba"


def logicas(caminho: pathlib.Path) -> list[tuple[int, str]]:
    """Junta as linhas continuadas com `_` numa única linha lógica."""
    brutas = caminho.read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n")
    saida: list[tuple[int, str]] = []
    acumulado, inicio = "", 0
    for n, linha in enumerate(brutas, 1):
        t = linha.strip()
        if not acumulado:
            inicio = n
        # Continuação de linha no VBA é ESPAÇO seguido de sublinhado.
        # Sem exigir o espaço, um identificador terminado em "_"
        # (ex.: `Next sub_`) seria lido como continuação e engoliria a
        # linha seguinte — foi exatamente o que produziu um falso
        # "End If faltando" aqui.
        if re.search(r"\s_$", t):
            acumulado += t[:-1].rstrip() + " "
            continue
        saida.append((inicio, (acumulado + t).strip()))
        acumulado = ""
    if acumulado:
        saida.append((inicio, acumulado.strip()))
    return saida


def verificar(caminho: pathlib.Path) -> list[str]:
    erros: list[str] = []
    pilha: list[tuple[int, str]] = []
    contadores = {"If": 0, "For": 0, "With": 0, "Select": 0, "Do": 0}
    for n, t in logicas(caminho):
        if not t or t.startswith("'"):
            continue
        if re.match(r"^(Public |Private |Friend )?(Sub|Function) \w+", t):
            pilha.append((n, t))
        elif re.match(r"^End (Sub|Function)$", t):
            if not pilha:
                erros.append(f"{caminho.name}:{n} End sem abertura")
            else:
                pilha.pop()
        # If de bloco: termina em Then. `If x Then y` numa linha só não conta.
        if re.match(r"^If .*\bThen$", t):
            contadores["If"] += 1
        elif t == "End If":
            contadores["If"] -= 1
        if re.match(r"^For\b", t):
            contadores["For"] += 1
        elif re.match(r"^Next\b", t):
            contadores["For"] -= 1
        if re.match(r"^With\b", t):
            contadores["With"] += 1
        elif t == "End With":
            contadores["With"] -= 1
        if re.match(r"^Select Case\b", t):
            contadores["Select"] += 1
        elif t == "End Select":
            contadores["Select"] -= 1
        if re.match(r"^Do\b", t):
            contadores["Do"] += 1
        elif re.match(r"^Loop\b", t):
            contadores["Do"] -= 1
    if pilha:
        erros.append(f"{caminho.name}: {len(pilha)} Sub/Function sem End: "
                     f"{[p[1][:40] for p in pilha[:3]]}")
    for bloco, saldo in contadores.items():
        if saldo:
            erros.append(f"{caminho.name}: {bloco} desbalanceado (saldo {saldo:+d})")
    return erros


def main() -> int:
    arquivos = sorted(PASTA.glob("*.bas"))
    if not arquivos:
        print("Nenhum módulo .bas encontrado.")
        return 1

    erros: list[str] = []
    for caminho in arquivos:
        problemas = verificar(caminho)
        estado = "OK" if not problemas else "FALHA"
        n = len(caminho.read_bytes().decode("utf-8").split("\n"))
        print(f"  {estado:<5} {caminho.name:<24} {n:>4} linhas")
        erros += problemas

    # Toda rotina referenciada por nome precisa existir como Public.
    #
    # Cobre dois casos que só falhariam em execução: a macro de um botão
    # (OnAction, string) e as chamadas dentro do código que o
    # modFormBuilder injeta nos formulários — que o compilador do VBA só
    # vê depois que o formulário é criado.
    publicas, alvos = set(), {}
    for caminho in arquivos:
        txt = caminho.read_bytes().decode("utf-8")
        for m in re.finditer(r"^Public (?:Sub|Function) (\w+)", txt, re.M):
            publicas.add(f"{caminho.stem}.{m.group(1)}")
    modulos = {c.stem for c in arquivos}
    for caminho in arquivos:
        txt = caminho.read_bytes().decode("utf-8")
        for literal in re.findall(r'"([^"\n]*)"', txt):
            for m in re.finditer(r"\b(mod\w+)\.(\w+)\b", literal):
                if m.group(1) in modulos:
                    alvos[f"{m.group(1)}.{m.group(2)}"] = caminho.name
    faltando = {a: f for a, f in alvos.items() if a not in publicas}
    print(f"\n  Rotinas referenciadas por nome: {len(alvos)}")
    if faltando:
        for macro, arquivo in sorted(faltando.items()):
            erros.append(f"{arquivo}: rotina inexistente {macro}")
    else:
        print("  Todas existem como Public.")

    # Controles usados pela lógica precisam ser criados pelo construtor.
    construtor = (PASTA / "modFormBuilder.bas")
    if construtor.exists():
        txt = construtor.read_bytes().decode("utf-8")
        criados = set(re.findall(r'"(lst\w+|txt\w+|cbo\w+|chk\w+|lbl\w+|btn\w+|fra\w+)"',
                                 txt))
        usados = set()
        for nome in ("modAssistente.bas", "modEscolherItem.bas"):
            arq = PASTA / nome
            if not arq.exists():
                continue
            corpo = arq.read_bytes().decode("utf-8")
            usados |= set(re.findall(
                r"\bf\.(lst\w+|txt\w+|cbo\w+|chk\w+|lbl\w+|btn\w+|fra\w+)", corpo))
        ausentes = sorted(usados - criados)
        print(f"  Controles usados pela lógica: {len(usados)}")
        if ausentes:
            for c in ausentes:
                erros.append(f"modFormBuilder.bas: controle não criado: {c}")
        else:
            print("  Todos são criados pelo construtor.")

    # Arquivos do Windows precisam de CRLF.
    for caminho in arquivos:
        if b"\r\n" not in caminho.read_bytes():
            erros.append(f"{caminho.name}: sem CRLF (o editor do VBA espera)")

    if erros:
        print("\nPROBLEMAS:")
        for e in erros:
            print(f"  - {e}")
        return 1
    print("\nEstrutura dos módulos VBA íntegra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
