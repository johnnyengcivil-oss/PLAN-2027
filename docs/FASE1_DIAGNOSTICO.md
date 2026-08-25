# FASE 1 — Diagnóstico das Bases

Auditoria executada sobre os arquivos entregues, com leitura **estritamente somente-leitura**.
Nenhum arquivo original foi aberto para escrita, salvo ou convertido.

---

## 1. Inventário: são CINCO bases, não quatro

O enunciado do projeto previa quatro arquivos. Foram entregues **cinco**, e o quinto é
estruturalmente decisivo: as **Composições Auxiliares** vêm em arquivo separado.
Sem ele, a expansão recursiva (itens 20–21) seria impossível.

| Papel | Arquivo entregue | Formato | Registros |
|---|---|---|---|
| Serviços / mão de obra da empresa | `xlsx_5.xlsx` | XLSX | 949 serviços |
| Materiais da empresa | `MATERIAIS.xlsx` | XLSX | 10.610 materiais |
| Referência EDIF | `ONERADA_SEM_Des_Comp_Custos_Unit_EDIF_JAN26.xls` | XLS (BIFF8) | 2.632 composições |
| Referência INFRA | `ONERADA_SEM_Des_Comp_Custos_Unit._INFRA__JAN26.xls` | XLS (BIFF8) | 843 composições |
| **Composições Auxiliares** | `ONERADA_SEM_Des_Composi__es_Auxiliares_JAN26.xls` | XLS (BIFF8) | 114 composições |

### 1.1 EDIF x INFRA: identificação automática, sem depender de ordem ou tamanho

O item 4 pedia que o sistema não presumisse a classificação. Não é preciso presumir nem
perguntar: **cada arquivo se identifica internamente**. A linha 2 traz o título e o nome da
única aba é inequívoco:

| Arquivo | Aba | Título interno (linha 2) |
|---|---|---|
| EDIF | `Comp EDIF SEM Des Jan 2026` | `COMPOSIÇÕES DE EDIFICAÇÕES - SEM DESONERAÇÃO` |
| INFRA | `Comp INFRA SEM Des JAN26` | `COMPOSIÇÕES DE INFRAESTRUTURA URBANA - SEM DESONERAÇÃO` |
| AUX | `Comp Auxiliares SEM Des Jan26` | `COMPOSIÇÕES AUXILIARES - SEM DESONERAÇÃO` |

O loader classifica por esse conteúdo (`loaders.detectar_origem`), com o **nome do arquivo
como pista secundária**. A aba `CONFIGURAÇÃO` permite sobrepor manualmente a detecção e
grava a escolha em `config.json` — o caminho de fallback exigido pelo item 4 existe, mas
na prática não é acionado com estas bases.

Origem das bases: **SIURB — Secretaria de Infraestrutura Urbana e Obras**, data-base
**JAN/2026**, tabelas *sem desoneração*.

---

## 2. Estrutura das bases de referência (EDIF / INFRA / AUX)

As três compartilham **exatamente o mesmo layout** de 10 colunas — um único parser atende
às três. As 4 primeiras linhas são cabeçalho institucional; os dados começam na linha 5.

```
col 0   col 1              col 2    col 3     col 4   col 5        col 6    col 7   col 8    col 9
CÓDIGO  NOME DO SERVIÇO    CODINS   NOMINS    UNID    CUSTO UNIT.  COEF.    UNID    Vparc    VALOR
```

Duas naturezas de linha se alternam:

* **Linha de composição** — `col0` preenchida com o código. Traz `NOME DO SERVIÇO` (col1),
  a unidade da composição (col7) e o custo unitário total (col9).
* **Linha de insumo** — `col0` vazia, `col2` (CODINS) preenchida. Traz descrição (col3),
  unidade do insumo (col4), custo unitário (col5), **coeficiente (col6)** e valor parcial (col8).

O insumo pertence à última composição vista acima dele.

**Qualidade do parse — 100%:**

| Base | Composições | Linhas de insumo | Linhas não classificadas | Composições sem insumo |
|---|---|---|---|---|
| EDIF | 2.632 | 10.445 | 4 (cabeçalho) | 0 |
| INFRA | 843 | 3.374 | 4 (cabeçalho) | 0 |
| AUX | 114 | 449 | 4 (cabeçalho) | 0 |

Nenhuma linha órfã, nenhuma composição vazia, nenhum rodapé espúrio.

### 2.1 ACHADO CRÍTICO — o código NÃO é único entre bases

**37 códigos existem simultaneamente em EDIF e INFRA designando serviços completamente
diferentes.** Em 100% dos 37 casos o nome do serviço difere:

| Código | EDIF | INFRA |
|---|---|---|
| `10001001` | HD.01 - CAVALETE DE ENTRADA - 3/4" | ANDAIMES METÁLICOS - FORNECIMENTO |
| `10001002` | HD.02 - CAVALETE DE ENTRADA - 1" | ANDAIMES METÁLICOS - MONTAGEM E DESMONTAGEM |
| `13001001` | ENCHIMENTO COM TIJOLOS CERÂMICOS FURADOS | ESTACA TIPO RAIZ, 100MM, PERFURAÇÃO EM SOLO |

**Consequência de projeto:** a chave primária de toda referência é o par
**`(origem, codigo)`** — nunca o código isolado. Isso vale para as tabelas, para os
vínculos confirmados, para o cache de embeddings e para o JSON da API. Tratar o código
como único produziria composições silenciosamente trocadas.

EDIF e INFRA não colidem com AUX (0 interseções), mas a chave composta é aplicada
uniformemente às três.

---

## 3. Classificação dos insumos — determinística, a partir da própria base

O item 19 exige não depender apenas do texto. A base oferece um sinal estrutural forte:
a **faixa do CODINS**, confirmada de forma independente pela unidade.

São 2.391 CODINS distintos em 14.268 ocorrências.

| Classe | Regra | Distintos | Confirmação independente |
|---|---|---|---|
| `COMPOSICAO_AUXILIAR` | CODINS existe como CÓDIGO na base AUX | 92 | resolução direta |
| `MAO_DE_OBRA` | CODINS com 4 dígitos (1xxx/2xxx) | 95 | **95/95 com unidade `H`** |
| `EQUIPAMENTO` | CODINS inicia com `94` | 89 | **87/89 com unidade `H`** |
| `MATERIAL` | demais | 2.115 | unidades de material (Un, M, Kg, M2, M3, L) |

A concordância entre faixa de código e unidade é praticamente perfeita, o que valida a
regra. Duas exceções em `94xxx` são tratadas por regra explícita:

* `94254` MÁQUINA DE SOLDA-RETIFICADOR 500A — unidade vazia → permanece `EQUIPAMENTO`.
* `94531` CÂMARA NOVA DE PNEU R13 — unidade `Un` → reclassificado para `MATERIAL`
  (é peça de reposição, não equipamento horário).

A faixa `95xxx` (24 itens: elevadores, brocas, conjuntos motor-bomba) tem **unidade `Un`
em 24/24** — são fornecimentos, e portanto `MATERIAL`, não equipamento. Classificá-los
como equipamento pela aparência do nome seria um erro.

O marcador textual `(SGSP)` aparece em 69 CODINS e **todos** têm 4 dígitos — corrobora a
regra de mão de obra, e é usado apenas como reforço.

---

## 4. Composições auxiliares e recursão

* **92 das 114** composições auxiliares são efetivamente referenciadas; 22 nunca são usadas.
* Essas 92 aparecem em **966 linhas de insumo** que precisam ser expandidas.
* **Todas** as referências a composição resolvem-se na base AUX. Nenhuma composição EDIF
  ou INFRA é usada como insumo de outra — a recursão é fechada dentro de AUX.
* **Profundidade máxima: 2 níveis** (10 auxiliares chamam outras auxiliares).
* **Nenhum ciclo detectado.**

Exemplo real de 2 níveis, usado como caso de teste:

```
10580  ALVENARIA DE TIJOLOS COM ARGAMASSA DE CIMENTO E AREIA 1:3   (M3)
├── 2020   PEDREIRO (SGSP)                          H    11,0000    [MÃO DE OBRA]
├── 2099   SERVENTE (SGSP)                          H     8,8000    [MÃO DE OBRA]
├── 10630  ARGAMASSA DE CIMENTO C/ AREIA GROSSA 1:3 M3    0,2200    [AUXILIAR ↓]
│   ├── 2099   SERVENTE (SGSP)                      H    10,0000    [MÃO DE OBRA]
│   ├── 10504  AREIA LAVADA GROSSA                  M3    1,2160    [MATERIAL]
│   └── 10517  CIMENTO PORTLAND CPII-E/F-32         Kg  486,0000    [MATERIAL]
└── 12580  TIJOLO MAÇICO DE BARRO COMUM             Un  720,0000    [MATERIAL]
```

Consolidado (coeficiente acumulado = produto dos coeficientes do caminho):
`CIMENTO = 0,2200 × 486,0000 = 106,9200 Kg` — exatamente a mecânica do item 21.

Ainda que a profundidade real seja 2, o expansor é **genericamente recursivo com guarda de
ciclo e limite de profundidade**, para sobreviver a atualizações futuras da base.

### 4.1 Composições auxiliares com unidade `%`

Cinco auxiliares têm unidade `%` e representam **percentuais sobre material e mão de obra**,
não quantidades físicas:

```
25221, 25222, 25223, 25228  SERVIÇO DE PROTENSÃO 20 PORC DO MAT. E MÃO DE OBRA
30750                       DESPESA C/ SOLDA, ESMERIL, LIXA E PINTURA - 8% DA M.OBRA E MATERIAL
```

Não são expansíveis por multiplicação de coeficiente. São marcadas como
**pendência `AUXILIAR_PERCENTUAL`** para decisão do usuário, em vez de receber uma regra
inventada (item 67).

---

## 5. Base de serviços da empresa (`xlsx_5.xlsx`)

Cabeçalho na linha 2; dados a partir da linha 3. **949 linhas com código** — o número real,
não 981 (total de linhas) nem 978. As 30 linhas restantes são **separadores visuais de
família**: trazem só o nome da família na coluna A e nenhum código. São descartadas.

Colunas: `Família` · `CÓDIGO` · `UN` · `DESCRIÇÃO` · `PREÇO APROVADO` · `VALOR`

* 30 famílias. Maiores: SERVIÇOS COMPLEMENTARES (131), PAVIMENTAÇÕES (75), SERRALHERIA (73),
  FUNDAÇÕES (68), GALERIAS E REDES DE DRENAGEM (68), ALVENARIA (43).
* **Nenhum código duplicado**, nenhuma descrição vazia.
* `PREÇO APROVADO`: **325 `Sim`** / 624 `Não`.
* `VALOR` é **texto** (`"R$ 16,00"`) em 949/949 linhas → exige parse de moeda pt-BR.
* O cabeçalho da coluna UN contém *no-break spaces* (`\xa0\xa0UN\xa0\xa0`) — a detecção de
  cabeçalho normaliza `\xa0` antes de comparar.
* Unidades já vêm inconsistentes na origem: `M2` (312) e `M²` (1); `vb` minúsculo (1).

### 5.1 ACHADO CRÍTICO — a base não é só mão de obra

Este é o achado com maior impacto sobre a regra dos itens 17 e 18.

O item 17 parte de que "o item de mão de obra da empresa já representa o custo da execução
do serviço", entrando com coeficiente 1,0000, e o item 18 conclui que os materiais vêm da
referência EDIF/INFRA. Isso é correto **para serviços de execução**, mas a base contém
**144 serviços (15,2%) que já embutem o material ou não são execução**:

| Escopo detectado | Qtd | % | Efeito sobre a composição própria |
|---|---|---|---|
| `EXECUCAO_INDEFINIDO` | 620 | 65,3% | regra padrão do item 17 aplica-se |
| `MAO_DE_OBRA` (explícito) | 126 | 13,3% | regra padrão — caso ideal |
| `FORNEC_E_INSTAL` | 74 | 7,8% | **material já incluído → importar da referência duplicaria custo** |
| `DEMOLICAO_REMOCAO` | 59 | 6,2% | consome pouco ou nenhum material |
| `LOCACAO` | 40 | 4,2% | não é execução; não comporta insumos |
| `FORNECIMENTO` | 30 | 3,2% | **só material, sem execução** |

Exemplos textualmente inequívocos:

```
140016  MÃO DE OBRA ESPECIALIZADA PARA INSTALAÇÃO DE DIVISÓRIAS      → só execução
140017  FORNECIMENTO E INSTALAÇÃO DE DIVISÓRIA EM GESSO DRYWALL      → já inclui material
140039  FORNECIMENTO E INSTALAÇÃO DE KIT PORTA DRYWALL COMPLETA      → já inclui material
```

Aplicar `1,0000 × preço interno + materiais da referência` a `140017` contaria o drywall
duas vezes — exatamente o erro que o item 18 quer evitar, só que na direção oposta à prevista.

**Decisão (item 67 — ambiguidade de negócio vira configuração + pendência, não regra inventada):**

O loader classifica o escopo de cada serviço por regex determinístico sobre a descrição e
grava em `company_services.escopo`. A política por escopo é **configurável** em
`config.json` → `politica_escopo`, com o padrão:

| Escopo | Mão de obra interna | Materiais da referência | Equipamentos |
|---|---|---|---|
| `MAO_DE_OBRA`, `EXECUCAO_INDEFINIDO` | 1,0000 | importar | importar |
| `FORNEC_E_INSTAL` | 1,0000 | **pendência `ESCOPO_SOBREPOSTO`** | importar |
| `FORNECIMENTO` | 1,0000 | **pendência** | não importar |
| `DEMOLICAO_REMOCAO` | 1,0000 | importar | importar |
| `LOCACAO` | 1,0000 | não importar | não importar |

Nada é descartado: os insumos referenciais ficam gravados com
`incluido_no_custo = 0` e o motivo, preservando a rastreabilidade exigida pelo item 18.

---

## 6. Base de materiais da empresa (`MATERIAIS.xlsx`)

Cabeçalho na linha 2; dados a partir da linha 3. **10.610 registros**, coluna A vazia.

Colunas úteis: `ITEM`(1) · `CODIGO_MATERIAL`(2) · `FAMILIA`(3) · `UNIDADE`(4) ·
`MATERIAL`(5) · `ULTIMO_PRECO`(6) · `VALOR`(9). As colunas 7, 8, 10+ estão vazias;
a célula J1 contém uma nota operacional do usuário, ignorada.

* **Nenhum código duplicado** (10.610 códigos únicos).
* `VALOR` é **sempre numérico** (7.698 float + 2.912 int); 13 zeros; nenhum nulo.
* 57 famílias, 30 unidades distintas.

### 6.1 Equipamentos já existem nesta base

O item 3 pergunta se há equipamentos na base de materiais. Há — **937 registros** em
quatro famílias:

```
Equipamentos  316    Ferramentas  285    Locação  251    Veículos  85
```

O matching de equipamentos (item 28) usa a mesma base, **restringindo o universo de busca a
essas famílias**. A arquitetura já contempla uma base de equipamentos separada no futuro:
`company_materials.tipo_item` (`MATERIAL` / `EQUIPAMENTO`) e o campo `fonte` isolam a
origem, então basta um novo loader — nenhuma reescrita (item 3).

### 6.2 REGRA DE PREÇO — resolvida por evidência, não por suposição

`ULTIMO_PRECO` não é um número: é um **texto com histórico de cotações**.

```
"    R$ 5.84   DATA : 06/03/26 --       R$ 1.00   DATA : 08/07/24 --       R$ 8.00   DATA : 05/04/24 --  "
```

Fatos medidos sobre os 10.610 registros:

* O histórico é parseável em **10.610/10.610** — nenhuma falha.
* Está **sempre ordenado da cotação mais recente para a mais antiga** (10.610/10.610).
* Distribuição: 7.045 registros com 3 cotações, 1.250 com 2, 2.315 com 1.
* **`VALOR` é igual ao MAIOR preço do histórico em 10.610/10.610 registros (100%).**
* `VALOR` coincide com a cotação mais recente em 6.611 (62,3%) — nos outros 3.999 é **maior**.
* **`VALOR` nunca é menor que a cotação mais recente** (0 casos).

Ou seja, `VALOR` é o **preço aprovado conservador da empresa** = máximo das últimas cotações.
Não é uma coincidência estatística; é uma regra determinística com 100% de aderência.

**Decisão documentada (item 52):** o preço vigente padrão é **`VALOR`**, por ser a política
que a própria empresa já pratica e por nunca subestimar o custo. O loader grava também
`preco_ultimo` e `data_ultimo` (cotação mais recente extraída do histórico) e persiste o
histórico completo em `company_material_prices` (código, data, preço, ordem). Isso deixa
prontas — sem migração — as políticas futuras do item 52: `ULTIMO`, `MEDIA_RECENTE`,
`MEDIANA`, `MAX` e `ATE_DATA`. A política é chaveada em `config.json` →
`politica_preco_material`, cujo padrão é `VALOR_APROVADO`.

Idade das cotações mais recentes: 2.696 de 2026, 2.038 de 2025, 1.999 de 2024 — e uma
cauda de 397 registros anteriores a 2018. O sistema marca preço com mais de 24 meses com o
sinal `PRECO_DESATUALIZADO` na composição, sem bloquear.

---

## 7. Unidades presentes — insumo para `units.py`

Unidades da referência (insumos): `H`, `Un`, `M`, `M2`, `M3`, `Kg`, `L`, `M3XKM`, `M2XKM`, `%`, `TON`.

Unidades da base interna de materiais (30): `UN`(6.795), `M`(489), `KG`(401), `GL`(351),
`M2`(344), `BR`(297), `LA`(285), `RL`(192), **`M²`(187)**, `DD`(187), `CT`(134), `CJ`(133),
`SC`(114), `MS`(105), `PC`(83), `VB`(83), **`M³`(75)**, `CX`(69), `JG`(65), `M3`(60),
`VG`(35), `Par`(32), `BS`(22), `TN`(21), `LT`(19), `TB`(13), `H`(7), `MIL`(4), `FD`(3).

Duas consequências diretas:

1. `M2`/`M²` e `M3`/`M³` **coexistem dentro da mesma base** → a canonicalização do item 42
   não é cosmética, é requisito de correção.
2. Unidades de **embalagem/comercialização** — `SC` saco, `BR` barra, `LA` lata, `GL` galão,
   `RL` rolo, `CX` caixa, `CT` cartela, `FD` fardo, `MIL` milheiro, `PC` peça, `CJ` conjunto,
   `JG` jogo, `DD`/`DZ` dúzia — **não têm conversão universal para `KG`/`M3`/`M2`**.
   Conforme item 26, jamais são convertidas por regra global. Só convertem quando existe
   regra cadastrada para aquele material específico (`conversion_rules`) ou quando o
   **próprio texto do material** declara o conteúdo (ex.: `"... 50kg"`, `"... 3,6L"`,
   `"barra 12,00m"`), extraído por `techspec.py`. Sem isso → pendência `CONVERSAO_PENDENTE`.
   `MIL` = 1.000 unidades e `DD` = 12 unidades são as únicas exceções seguras
   (multiplicadores de contagem, independentes do produto).

---

## 8. Resumo das decisões técnicas tomadas nesta fase

| # | Decisão | Fundamento |
|---|---|---|
| 1 | Chave de referência = `(origem, codigo)` | 37 códigos colidem entre EDIF e INFRA com serviços distintos |
| 2 | Um único parser para EDIF/INFRA/AUX | layout de 10 colunas idêntico nas três |
| 3 | Origem detectada pelo título interno da linha 2 e nome da aba | não depende de nome, ordem ou tamanho de arquivo (item 4) |
| 4 | Classificação de insumo por faixa de CODINS, validada pela unidade | 95/95 e 87/89 de concordância; não depende do texto (item 19) |
| 5 | `95xxx` = MATERIAL, não equipamento | 24/24 com unidade `Un` (fornecimento) |
| 6 | Auxiliar = CODINS presente como CÓDIGO em AUX | resolve 92 auxiliares / 966 linhas, sem heurística textual |
| 7 | Recursão genérica com guarda de ciclo, apesar de profundidade real 2 | resistência a atualizações futuras da base |
| 8 | Auxiliares `%` → pendência, sem regra inventada | 5 casos não expansíveis por multiplicação (item 67) |
| 9 | Preço vigente = `VALOR` | = máximo do histórico em 10.610/10.610; nunca abaixo da última cotação |
| 10 | Histórico de preços normalizado em tabela própria | habilita políticas do item 52 sem migração |
| 11 | Escopo do serviço interno classificado e política configurável | 144 serviços (15,2%) já incluem material — risco real de dupla contagem |
| 12 | Equipamentos buscados nas 4 famílias de equipamento de `MATERIAIS.xlsx` | 937 registros já disponíveis; `tipo_item` isola base futura (item 3) |
| 13 | Unidades de embalagem nunca convertidas por regra global | item 26; só por regra do produto ou conteúdo declarado no texto |
