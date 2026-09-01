# Banco Próprio de Composições

Sistema Excel/VBA + Python para construir progressivamente o banco de
composições de preços da empresa, a partir da correspondência entre os
serviços internos de mão de obra e as composições referenciais EDIF/INFRA.

Funciona **100% local**, sem API paga e sem privilégio de administrador.

```
SERVIÇO DE MÃO DE OBRA DA EMPRESA
            ↓
  BUSCA AUTOMÁTICA EDIF + INFRA          ← Python: textual + semântica + regras técnicas
            ↓
      SUGESTÕES COM SCORE                ← explicável, decomposto em 5 componentes
            ↓
       ESCOLHA DO USUÁRIO                ← sempre humana, mesmo com 100%
            ↓
   DECOMPOSIÇÃO DOS INSUMOS              ← auxiliares expandidas recursivamente
            ↓
  BUSCA NA BASE DA EMPRESA               ← materiais e equipamentos internos
            ↓
     VALIDAÇÃO DO USUÁRIO
            ↓
  COMPOSIÇÃO PRÓPRIA DA EMPRESA          ← vira conhecimento reaproveitado
```

## Estado atual

| Fase | Situação |
|---|---|
| 1 — Auditoria das bases | concluída — `docs/FASE1_DIAGNOSTICO.md` |
| 2 — Modelo de dados | concluída — 15 tabelas + 1 view |
| 3 — Importadores | concluída — 5 bases, leitura pura |
| 4 — Matching serviço → EDIF/INFRA | concluída |
| 5 — Interface Excel/VBA | concluída — 9 abas, 10 módulos |
| 6 — Composição referencial | concluída |
| 7 — Expansão de auxiliares | concluída — validada em 3.589 composições |
| 8 — Matching materiais/equipamentos | concluída |
| 9 — Banco próprio | concluída |
| 10 — Aprendizado por vínculos | concluída |
| 11 — Empacotamento | receita pronta em `docs/INSTALACAO.md` |

123 testes automatizados, incluindo os 7 casos obrigatórios do item 60.

## Começando

**Windows, por duplo clique:** `instalar.bat` prepara o ambiente e
verifica a instalação; `verificar.bat` reconfere; `prova.bat` roda a prova
funcional. Passo a passo completo em [`docs/INSTALACAO.md`](docs/INSTALACAO.md).

**Pela linha de comando:**

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip

# confere dependências, bases, banco, motor e interface
.venv/bin/python verificar.py

# coloque as 5 bases em BASES/ (ver BASES/LEIA-ME.txt) e importe
.venv/bin/python python/main.py --json '{"acao":"atualizar_bases"}'

# prova funcional completa (item 65)
.venv/bin/python prova_funcional.py

# testes
.venv/bin/python -m pytest tests/ -q

# gerar a pasta de trabalho do Excel
.venv/bin/python build_xlsm.py
```

A montagem do `.xlsm` está em [`docs/INSTALACAO.md`](docs/INSTALACAO.md).

## Estrutura

```
python/
  main.py              ponte JSON (arquivo, inline ou stdin)
  motor/
    config.py          config.json, políticas, pesos; caminhos relativos
    normalize.py       texto, unidades, códigos, números pt-BR
    units.py           conversões determinísticas (nunca por IA)
    techspec.py        atributos técnicos e penalizações por conflito
    database.py        esquema SQLite
    loaders.py         leitura das 5 bases, somente leitura
    ingest.py          importação incremental por SHA-256
    semantic.py        embeddings locais, 2 backends
    matching.py        score explicável, serviços e materiais
    compositions.py    expansão recursiva, hierárquico + consolidado
    own.py             composição própria, custeio, pendências
    api.py             whitelist de 26 ações
vba/                   10 módulos VBA versionados
tests/                 123 testes
docs/                  diagnóstico e instalação
build_xlsm.py          gera a pasta de trabalho
prova_funcional.py     prova exigida pelo item 65
```

O mapeamento para os módulos sugeridos no enunciado: `normalize.py` e
`techspec.py` são desdobramentos de `matching.py`; `ingest.py` separa a
orquestração da importação de `loaders.py`; `own.py` concentra a
composição própria; `models.py` não existe como arquivo próprio porque as
estruturas de domínio são dataclasses declaradas junto do módulo que as
usa (`Candidato`, `NoInsumo`, `ItemProprio`, `Conversao`, `Spec`).

## Decisões que definiram a arquitetura

Todas medidas sobre as bases reais, não presumidas. O detalhamento está em
[`docs/FASE1_DIAGNOSTICO.md`](docs/FASE1_DIAGNOSTICO.md).

**São cinco bases, não quatro.** As Composições Auxiliares vêm em arquivo
separado. Sem ele, a expansão recursiva dos itens 20 e 21 seria impossível.

**A chave de referência é `(origem, codigo)`.** 37 códigos existem
simultaneamente em EDIF e INFRA designando serviços diferentes — em 100%
dos casos. Tratar o código como único trocaria composições silenciosamente.

**EDIF, INFRA e AUX são identificados pelo conteúdo.** O título
institucional da linha 2 e o nome da aba decidem. Verificado com nomes sem
significado e com ordem alfabética e tamanho deliberadamente invertidos.

**A classe do insumo vem da estrutura, não do texto.** A faixa do CODINS
decide, e a unidade confirma: 95/95 das mãos de obra e 87/89 dos
equipamentos têm unidade `H`. A faixa `95xxx` tem `Un` em 24/24 — são
fornecimentos, e classificá-los como equipamento pelo nome seria errado.

**`VALOR` é o preço vigente.** É o máximo do histórico de cotações em
10.610/10.610 registros e nunca fica abaixo da cotação mais recente. O
histórico é normalizado em tabela própria, deixando prontas as políticas
`ULTIMO`, `MEDIA_RECENTE`, `MEDIANA` e `MAX` sem migração.

**15,2% dos serviços internos já embutem material.** 144 dos 949 são
`FORNECIMENTO E INSTALAÇÃO`, `FORNECIMENTO` ou `LOCAÇÃO`. Aplicar a eles a
regra de 1,0000 mais os materiais da referência contaria o material duas
vezes — o erro do item 18, na direção oposta à prevista. O escopo é
classificado no carregamento e a política virou configuração, não regra
inventada.

**`DD` nestas bases é diária, não dúzia.** A família DIÁRIAS usa `DD`, 152
dos 187 materiais em `DD` são locação, e a referência escreve `DÚZIA` por
extenso. Como consequência, período de locação não converte para hora
automaticamente: quantas horas produtivas há numa diária é decisão da
empresa, não constante física.

## O que o sistema garante

**As bases originais nunca são alteradas.** Abertas apenas para leitura
(`xlrd` e `openpyxl` com `read_only=True`). Nada é gravado, convertido,
renomeado ou salvo por cima. Há teste que verifica isso no código-fonte.

**Nenhum vínculo é confirmado automaticamente**, nem com score de 100%
(item 14). O lote pré-calcula e prioriza; confirmar continua sendo do
engenheiro. Sugestão automática e vínculo validado são visualmente
distintos (item 34).

**A expansão recursiva foi verificada aritmeticamente.** Recalculando o
custo das 3.589 composições a partir dos coeficientes acumulados, 99,8%
fecham dentro de 1% do custo publicado, com erro mediano de 0,003%. As 5
que divergem de fato são exatamente as 5 que o sistema já havia marcado
como pendência `AUXILIAR_PERCENTUAL` — detectadas pela estrutura (unidade
`%`), independentemente do custo.

**Conversões são determinísticas.** Unidade de embalagem só converte com
regra cadastrada para o produto ou conteúdo declarado no próprio texto
(`"... 50kgs"` → 1 SC = 50 KG). Quando há ambiguidade — `"Aço CA 50 Ø10mm
x 12,00m"` tem dois comprimentos candidatos — vira pendência em vez de
chute.

**Conflito técnico derruba o score.** Espessura, diâmetro, fck, classe do
aço, tipo de cimento, dimensões e ação executiva geram penalização
explicada, e um conflito grave tem teto de score: por mais parecida que
seja a frase, não chega a "forte candidato".

**Uma pendência não descarta a composição** (item 39). Os demais insumos
são montados, o item aberto fica com custo zero — nunca com número
inventado — e a composição fica `PENDENTE`.

**Reimportar preserva o conhecimento** (item 53). Só as tabelas de origem
são recriadas; vínculos, composições próprias e conversões permanecem.
Composições cuja referência mudou são marcadas `REVISAR`.

**Funciona sem LLM.** O backend semântico padrão é TF-IDF com n-gramas de
caractere: local, determinístico, sem download e sem rede.
`sentence-transformers` é um upgrade opcional.

## Comunicação VBA ↔ Python

```json
{"acao": "buscar_servico", "codigo_empresa": "140006", "top_n": 10}
```

```json
{"status": "ok", "acao": "buscar_servico",
 "resultados": [{"origem": "EDIF", "codigo": "4001071", "score": 0.825,
                 "componentes": {"textual": 0.79, "semantico": 0.63,
                                 "cobertura": 0.71, "unidade": 1.0,
                                 "tecnico": 1.0},
                 "confianca": "PROVAVEL", "vinculo_validado": false}]}
```

As 26 ações são uma whitelist fechada — um dicionário nome → função. Nome
fora dele é recusado. Não existe `eval`, `exec`, `__import__`, `subprocess`
nem `getattr` sobre o payload, e há teste que varre o código-fonte para
garantir isso.
