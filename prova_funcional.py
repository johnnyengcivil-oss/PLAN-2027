"""Prova funcional exigida pelo item 65.

Percorre o fluxo completo em serviços REAIS das bases, dos candidatos
EDIF/INFRA até a composição própria simulada, mostrando em cada etapa por
que o algoritmo decidiu o que decidiu.

NADA aqui é gravado como definitivo: a seleção do candidato é feita
"apenas para teste", como o item 65 pede, e a validação humana continua
sendo requisito para virar conhecimento da empresa.

    python prova_funcional.py [--servicos 140006,1110006] [--json saida.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "python"))

from motor import config, database, ingest                    # noqa: E402
from motor.compositions import ExpansorComposicoes            # noqa: E402
from motor.matching import BuscadorMateriais, BuscadorServicos  # noqa: E402
from motor.own import MontadorComposicaoPropria               # noqa: E402
from motor.semantic import MotorSemantico                     # noqa: E402

# Serviços escolhidos por cobrirem situações estruturalmente diferentes.
SERVICOS_PADRAO = [
    ("140006", "alvenaria — descrição enumera variantes e dimensões"),
    ("1110006", "reboco — puxa composição auxiliar de argamassa"),
    ("140010", "demolição — ação executiva oposta à de execução"),
    ("1110012", "assentamento de azulejos — revestimento cerâmico"),
    ("120006", "demolição de concreto armado — composição com equipamento"),
    ("140017", "fornecimento e instalação — risco de dupla contagem"),
]

LARGURA = 108


def titulo(texto: str, marcador: str = "=") -> None:
    print("\n" + marcador * LARGURA)
    print(texto)
    print(marcador * LARGURA)


def moeda(valor) -> str:
    return f"R$ {valor:,.4f}".replace(",", "@").replace(".", ",").replace("@", ".") \
        if isinstance(valor, (int, float)) else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prova funcional (item 65)")
    parser.add_argument("--servicos", help="códigos separados por vírgula")
    parser.add_argument("--json", help="grava o resultado estruturado")
    parser.add_argument("--raiz", default=str(RAIZ))
    args = parser.parse_args(argv)

    cfg = config.carregar(args.raiz)
    con = database.conectar(cfg.caminho_db)
    if database.escalar(con, "SELECT COUNT(*) FROM company_services") in (0, None):
        print("Importando bases...")
        ingest.importar(con, cfg)

    semantico = MotorSemantico(cfg.pasta_cache, cfg.backend_semantico,
                               cfg.modelo_embeddings)
    servicos = BuscadorServicos(con, cfg, semantico)
    materiais = BuscadorMateriais(con, cfg, semantico)
    expansor = ExpansorComposicoes(con)
    montador = MontadorComposicaoPropria(con, cfg, expansor, materiais)

    if args.servicos:
        alvos = [(c.strip(), "") for c in args.servicos.split(",") if c.strip()]
    else:
        alvos = SERVICOS_PADRAO

    titulo("PROVA FUNCIONAL — BANCO PRÓPRIO DE COMPOSIÇÕES")
    print(f"Backend semântico : {semantico.descricao_backend()}")
    print(f"Serviços da base  : {database.escalar(con, 'SELECT COUNT(*) FROM company_services')}")
    print(f"Materiais da base : {database.escalar(con, 'SELECT COUNT(*) FROM company_materials')}")
    print(f"Composições ref.  : {database.escalar(con, 'SELECT COUNT(*) FROM reference_compositions')}")
    print("\nNenhuma escolha desta prova é gravada como definitiva.")

    saida: list[dict] = []
    for indice, (codigo, motivo) in enumerate(alvos, 1):
        servico = con.execute(
            "SELECT * FROM company_services WHERE codigo = ?", (codigo,)).fetchone()
        if servico is None:
            print(f"\n[{indice}] serviço {codigo} não encontrado — ignorado.")
            continue

        titulo(f"CASO {indice} — SERVIÇO INTERNO {servico['codigo']}"
               + (f"   ({motivo})" if motivo else ""))
        print(f"  Família : {servico['familia']}")
        print(f"  Unidade : {servico['unidade_orig']}")
        print(f"  Escopo  : {servico['escopo']}")
        print(f"  Preço   : {moeda(servico['preco'])}"
              f"   (aprovado: {'sim' if servico['preco_aprovado'] else 'não'})")
        print(f"  {servico['descricao']}")

        # ---------------------------------------------- 1) candidatos
        print("\n  [1] CANDIDATOS EDIF/INFRA — com o score decomposto")
        candidatos = servicos.buscar(servico["descricao"], servico["unidade"],
                                     top_n=4, codigo_empresa=codigo)
        if not candidatos:
            print("      Nenhum candidato acima do score mínimo.")
            print("      -> pendência SERVICO_SEM_CORRESPONDENCIA (item 38);")
            print("         o serviço não é descartado nem vinculado por força.")
            saida.append({"servico": codigo, "candidatos": [], "resultado": "SEM_CANDIDATO"})
            continue
        for pos, c in enumerate(candidatos, 1):
            print(f"      {pos}. {c.score * 100:5.1f}%  {c.confianca:<9} "
                  f"{c.origem} {c.codigo:<10} {c.descricao[:56]}")
            comp = "  ".join(f"{k}={v * 100:.0f}%" for k, v in c.componentes.items())
            print(f"         {comp}")
            for r in c.reforcos:
                print(f"         + {r}")
            for p in c.penalidades:
                print(f"         - {p}")

        # ------------------------------------- 2) escolha técnica (só teste)
        escolhido = candidatos[0]
        print(f"\n  [2] SELEÇÃO TÉCNICA PARA TESTE: {escolhido.origem} {escolhido.codigo}")
        print("      (item 65: escolhido pelo algoritmo apenas para validar a lógica;")
        print("       em produção esta linha exige o clique do engenheiro)")

        # ---------------------------------------------- 3) expansão
        expandida = expansor.expandir(escolhido.origem, escolhido.codigo)
        print(f"\n  [3] COMPOSIÇÃO DE REFERÊNCIA EXPANDIDA")
        print(f"      {expandida.descricao}  [{expandida.unidade_orig}]")
        print(f"      profundidade={expandida.profundidade}  "
              f"auxiliares expandidas={expandida.auxiliares_expandidas}  "
              f"classes={expandida.resumo_classes()}")

        def arvore(nos, prefixo="        "):
            for no in nos:
                marca = " [AUXILIAR ↓]" if no.expandido else (
                    f" [!{no.pendencia}]" if no.pendencia else "")
                print(f"{prefixo}{'    ' * no.nivel}{no.codins:<7} "
                      f"{no.descricao[:40]:<40} {no.unidade_orig:<4} "
                      f"coef={no.coeficiente:<10.6g} acum={no.coeficiente_acumulado:<10.6g} "
                      f"{no.classe[:12]:<12}{marca}")
                arvore(no.filhos, prefixo)
        arvore(expandida.arvore)

        base = expandida.custo_total or 0
        calc = expandida.custo_calculado()
        erro = abs(calc - base) / base * 100 if base else 0
        print(f"\n      conferência: publicado {moeda(base)}  x  "
              f"recalculado {moeda(calc)}   (diferença {erro:.4f}%)")

        # ---------------------------------------------- 4) composição própria
        propria = montador.montar(codigo, escolhido.origem, escolhido.codigo,
                                  top_sugestoes=3)
        print(f"\n  [4] COMPOSIÇÃO PRÓPRIA SIMULADA")
        print(f"      política de escopo aplicada: "
              f"materiais={'importa' if propria.politica_aplicada.get('importar_materiais') else 'NÃO importa'}"
              f"  equipamentos={'importa' if propria.politica_aplicada.get('importar_equipamentos') else 'NÃO importa'}")
        if propria.politica_aplicada.get("motivo"):
            print(f"      motivo: {propria.politica_aplicada['motivo']}")

        print(f"\n      {'TIPO':<12} {'CÓD':<7} {'DESCRIÇÃO INTERNA':<38} {'UN':<4} "
              f"{'COEF.FINAL':>12} {'CUSTO':>12}  SITUAÇÃO")
        for item in propria.itens:
            situacao = ("NÃO SOMADO" if not item.incluido_no_custo
                        else (item.pendencia or
                              ("VALIDADO" if "VALIDADO" in item.detalhe_score else "sugestão")))
            print(f"      {item.tipo:<12} {item.codigo_interno:<7} "
                  f"{(item.descricao_interna or '—')[:38]:<38} "
                  f"{item.unidade_interna:<4} {item.coeficiente_final:>12.6f} "
                  f"{item.custo_item:>12.4f}  {situacao}")
            if item.codins_ref:
                print(f"        └ ref {item.codins_ref:<6} {item.descricao_ref[:38]:<38} "
                      f"[{item.unidade_ref:<4}] coef.orig={item.coeficiente_original:<10.6g} "
                      f"conv={item.metodo_conversao or '—'}(x{item.fator_conversao:g})"
                      + (f" score={item.score:.3f}" if item.score else ""))
                if item.caminho_expansao:
                    print(f"          via {item.caminho_expansao}")

        estado, motivo_estado = propria.status()
        print(f"\n      mão de obra  {moeda(propria.custo_mao_obra):>16}")
        print(f"      materiais    {moeda(propria.custo_materiais):>16}")
        print(f"      equipamentos {moeda(propria.custo_equipamentos):>16}")
        print(f"      CUSTO DIRETO {moeda(propria.custo_direto):>16}")
        print(f"      STATUS: {estado}" + (f" — {motivo_estado}" if motivo_estado else ""))

        if propria.pendencias:
            print(f"\n      PENDÊNCIAS ({len(propria.pendencias)}):")
            for p in propria.pendencias:
                print(f"        [{p['tipo']}] {p.get('descricao', '')[:40]}")
                print(f"          {p.get('detalhe', '')[:88]}")

        saida.append({
            "servico": codigo,
            "descricao": servico["descricao"],
            "escopo": servico["escopo"],
            "candidatos": [c.to_dict() for c in candidatos],
            "escolhido_para_teste": {"origem": escolhido.origem,
                                     "codigo": escolhido.codigo,
                                     "score": escolhido.score},
            "expansao": expandida.to_dict(incluir_arvore=True),
            "composicao_propria": propria.to_dict(),
            "conferencia_custo_referencia": {
                "publicado": base, "recalculado": calc, "erro_pct": erro},
        })

    titulo("RESUMO DA PROVA")
    print(f"{'SERVIÇO':<10} {'ESCOPO':<20} {'REFERÊNCIA':<16} {'SCORE':>7} "
          f"{'ITENS':>6} {'PEND':>5} {'CUSTO DIRETO':>16}  STATUS")
    for r in saida:
        if not r.get("candidatos"):
            print(f"{r['servico']:<10} {'—':<20} {'SEM CANDIDATO':<16}")
            continue
        cp = r["composicao_propria"]
        esc = r["escolhido_para_teste"]
        print(f"{r['servico']:<10} {r['escopo'][:20]:<20} "
              f"{esc['origem'] + ' ' + esc['codigo']:<16} "
              f"{esc['score'] * 100:>6.1f}% {len(cp['itens']):>6} "
              f"{len(cp['pendencias']):>5} {moeda(cp['custo_direto']):>16}  "
              f"{cp['status']}")

    print("\nNenhum vínculo foi gravado. Em produção, cada linha acima passa")
    print("pela confirmação do engenheiro antes de virar conhecimento da empresa.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(saida, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        print(f"\nResultado estruturado gravado em {args.json}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
