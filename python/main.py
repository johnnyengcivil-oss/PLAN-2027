"""Ponto de entrada do motor — ponte JSON entre o Excel/VBA e o Python.

Três formas de invocação, todas equivalentes no resultado:

    motor.exe --pedido pedido.json --resposta resposta.json   (usada pelo VBA)
    motor.exe --json "{\"acao\": \"status\"}"
    echo {"acao":"status"} | motor.exe

Arquivo é o modo preferido pelo VBA: evita limite de linha de comando,
problemas de aspas e de página de código do Windows. Tudo em UTF-8.

O código de saída é 0 quando a ação executa e 1 quando falha, para que o
VBA possa checar sem precisar interpretar o JSON antes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):                # execução direta: python main.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from motor import api                        # noqa: E402


def _ler_pedido(args: argparse.Namespace) -> dict:
    if args.pedido:
        texto = Path(args.pedido).read_text(encoding="utf-8-sig")
    elif args.json:
        texto = args.json
    elif args.acao:
        pedido = {"acao": args.acao}
        for par in args.param or []:
            chave, _, valor = par.partition("=")
            pedido[chave.strip()] = valor
        return pedido
    else:
        texto = sys.stdin.read()
    texto = (texto or "").strip()
    if not texto:
        return {}
    return json.loads(texto)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="motor",
        description="Motor do Banco Próprio de Composições (uso local).")
    parser.add_argument("--pedido", help="arquivo JSON de entrada")
    parser.add_argument("--resposta", help="arquivo JSON de saída")
    parser.add_argument("--json", help="JSON de entrada inline")
    parser.add_argument("--acao", help="nome da ação (atalho para testes)")
    parser.add_argument("--param", action="append",
                        help="parâmetro chave=valor (repetível, com --acao)")
    parser.add_argument("--raiz", help="pasta do sistema (padrão: a do executável)")
    parser.add_argument("--indent", type=int, default=None,
                        help="indentação do JSON de saída")
    parser.add_argument("--listar-acoes", action="store_true",
                        help="lista a whitelist de ações e sai")
    args = parser.parse_args(argv)

    if args.listar_acoes:
        print(json.dumps({"status": "ok", "acoes": api.acoes_disponiveis()},
                         ensure_ascii=False, indent=2))
        return 0

    try:
        pedido = _ler_pedido(args)
    except (OSError, json.JSONDecodeError) as exc:
        resposta = {"status": "erro", "erro": f"Pedido inválido: {exc}"}
    else:
        if args.raiz:
            pedido.setdefault("raiz", args.raiz)
        resposta = api.executar(pedido)

    saida = json.dumps(resposta, ensure_ascii=False, indent=args.indent,
                       default=str)
    if args.resposta:
        destino = Path(args.resposta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(saida, encoding="utf-8")
    else:
        sys.stdout.write(saida)
        sys.stdout.write("\n")
    return 0 if resposta.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
