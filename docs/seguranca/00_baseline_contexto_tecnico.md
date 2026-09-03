# RELATÓRIO DE CONTEXTO TÉCNICO PARA CONTINUIDADE DA ANÁLISE DE SEGURANÇA

## Sistema Gerencial — Almeida Sapata Engenharia

**Finalidade deste documento:** fornecer ao Claude todo o contexto técnico, evidências, conclusões preliminares e pontos ainda pendentes identificados até o momento, para que a análise prossiga a partir dos próximos arquivos ZIP fornecidos, sem reiniciar a investigação e sem repetir testes já realizados.

---

# 1. INSTRUÇÕES OBRIGATÓRIAS AO ANALISTA

Esta é uma avaliação interna, autorizada e defensiva de um sistema corporativo em produção.

A análise realizada até aqui foi baseada exclusivamente em:

- funcionamento normal da aplicação;
- HTML e JavaScript entregue normalmente ao navegador;
- arquivos auxiliares salvos pelo próprio navegador;
- requisições utilizadas pelas próprias telas;
- mensagens de erro geradas pela própria aplicação;
- conteúdo de um erro SQL ocorrido ao utilizar uma entrada incompatível com a consulta;
- análise estática dos arquivos fornecidos.

## Não executar

Não realizar:

- exploração de vulnerabilidades;
- SQL Injection;
- XSS;
- bypass de autenticação;
- bypass de autorização;
- alteração de IDs para tentar acessar dados de terceiros;
- brute force;
- fuzzing;
- enumeração agressiva;
- scanning automatizado contra o servidor;
- alteração não autorizada de registros;
- testes destrutivos;
- inserção de payloads;
- acesso a recursos além daqueles normalmente disponibilizados ao usuário;
- qualquer tentativa de invasão.

Os próximos arquivos serão enviados em ZIP e deverão ser analisados **estaticamente**.

Se uma hipótese somente puder ser comprovada por exploração ativa, registre:

**A VERIFICAR INTERNAMENTE**

e explique qual código ou configuração deve ser revisado.

---

# 2. CLASSIFICAÇÃO DE EVIDÊNCIA

Utilizar obrigatoriamente estas classificações durante a continuidade do diagnóstico.

### CONFIRMADO

A evidência fornecida demonstra diretamente o comportamento ou a deficiência.

### INDÍCIO FORTE

Existem evidências relevantes indicando o risco, mas ainda é necessário analisar o código server-side para confirmar integralmente a vulnerabilidade.

### A VERIFICAR

Não existem elementos suficientes nos arquivos atuais.

### CONTROLE IDENTIFICADO

Foi encontrada uma proteção implementada pelo sistema.

Nunca promover automaticamente um indício para vulnerabilidade confirmada.

---

# 3. AMBIENTE E TECNOLOGIAS OBSERVADAS

Foram identificados até o momento:

- Adobe/Macromedia ColdFusion / CFML;
- páginas `.cfm`;
- componentes `.cfc`;
- SQL Server;
- JDBC SQL Server;
- Java;
- Tomcat/Catalina;
- jQuery;
- jQuery UI;
- DataTables;
- CKEditor;
- CKFinder;
- AJAX intensivo;
- formulários HTML;
- chamadas AJAX utilizando `POST`;
- endpoints CFC chamados diretamente pelo navegador.

O erro de banco fornecido identifica explicitamente componentes ColdFusion, JDBC SQL Server e Tomcat.

Foram também revelados caminhos físicos do ambiente Windows, por exemplo:

`E:\sistemas\ASEng\...`

---

# 4. ARQUIVOS ANALISADOS ATÉ O MOMENTO

## 4.1 Dump de erro

Arquivo:

`Markdown(4).md colado`

Contém um erro SQL completo retornado ao navegador, incluindo:

- SQL executado;
- SQLState;
- código de erro;
- stack trace;
- datasource;
- driver;
- caminhos físicos;
- arquivos CFM/CFC;
- linhas do código.

## 4.2 Tela de medição

Pacote ZIP:

`b91f3cfb-512f-408b-96be-7214d981822f.zip`

Arquivo principal:

`AS Engenharia.html`

O ZIP contém o HTML completo salvo pelo navegador e aproximadamente dezenas de arquivos auxiliares JS/CSS/imagens.

A tela analisada correspondia ao módulo de **edição de medição de serviços**.

Exemplo observado:

- contrato interno: `20250495`;
- aditivo: `1`;
- medição: `8`;
- rotina: `41`.

Esses identificadores servem apenas como referência da amostra analisada e não devem ser utilizados para testes.

---

# 5. PRIMEIRO ACHADO RELEVANTE — CONSTRUÇÃO DE SQL COM ENTRADA EXTERNA

## SEC-001 — Entrada externa incorporada diretamente à instrução SQL

**Classificação:** CONFIRMADO quanto à incorporação da entrada à consulta.

**Criticidade preliminar:** ALTA.

**Possível classe:** CWE-89 / SQL Injection, porém a explorabilidade ainda não deve ser considerada confirmada.

Foi analisada uma página que originalmente utilizava um parâmetro:

`id_pedido`

com valor único.

Ao ser fornecida uma lista de dois números separados por vírgula, o sistema gerou erro SQL.

O dump produzido pela própria aplicação mostrou que a entrada havia sido incorporada diretamente em várias partes da consulta.

Exemplo conceitual observado:

```sql
WHERE PED.ID_PEDIDO = 124991,124992
```

O mesmo valor apareceu repetidamente em diferentes CTEs/subconsultas.

Isso demonstra que a aplicação não transformou a entrada em parâmetros individuais do driver.

Também não houve rejeição prévia do formato antes da construção da instrução.

## Conclusão tecnicamente segura

Pode-se afirmar:

> Foi identificada evidência de incorporação direta de entrada externa na construção da instrução SQL.

Ainda não afirmar:

> SQL Injection explorável confirmada.

Para isso, deve-se revisar o código-fonte responsável.

---

# 6. LOCAL DO CÓDIGO REVELADO PELO ERRO

O stack trace aponta para:

`E:\sistemas\ASEng\suprimento\cfcs\pedido_DAO2.cfc`

Função:

`GETPRINTORDER`

Linha aproximada:

`141`

Fluxo seguinte identificado:

`pedido_DAO2.cfc`

→ `npedido_print.cfm`

→ `Application.cfc`

Também foi revelado:

`E:\sistemas\ASEng\suprimento\npedido_print.cfm`

linha aproximada 4.

E:

`E:\sistemas\ASEng\Application.cfc`

linha aproximada 942.

## Prioridade para os próximos ZIPs

Se esses arquivos forem fornecidos, analisar imediatamente:

- `pedido_DAO2.cfc`;
- `npedido_print.cfm`;
- `Application.cfc`.

Pesquisar especialmente:

- `cfquery`;
- `cfqueryparam`;
- `URL.`;
- `FORM.`;
- `arguments.`;
- interpolação com `#...#`;
- construção dinâmica de SQL.

---

# 7. SEC-002 — EXPOSIÇÃO EXCESSIVA DE ERROS

**Classificação:** CONFIRMADO.

**Criticidade:** ALTA.

A aplicação apresentou ao usuário detalhes internos extensos do erro.

Foram revelados:

- SQL executado;
- estrutura da consulta;
- SQLState;
- exceção JDBC;
- tecnologia utilizada;
- driver;
- stack trace;
- paths físicos;
- organização das pastas da aplicação;
- nomes de arquivos;
- componentes CFC;
- funções;
- linhas do código;
- datasource.

## Impacto

Essa exposição facilita significativamente o reconhecimento técnico da aplicação.

Um terceiro passa a conhecer:

- tecnologia;
- arquitetura;
- localização dos componentes;
- estrutura aproximada do banco;
- nomes de schemas;
- nomes de tabelas;
- nomes de views;
- relacionamentos;
- nomes dos DAOs;
- pontos relevantes do código.

Mesmo que nenhuma vulnerabilidade adicional existisse, isso constitui exposição desnecessária de informações internas.

## Recomendação

Implementar tratamento centralizado de exceções no `Application.cfc`.

Ao navegador:

```text
Não foi possível concluir a operação.
Código do erro: XXXXX
```

No log interno:

- stack trace;
- exceção;
- consulta;
- usuário;
- contexto;
- identificador da requisição.

---

# 8. MÓDULO DE MEDIÇÕES — ARQUITETURA RECONSTRUÍDA

A tela `AS Engenharia.html` permitiu reconstruir boa parte do fluxo funcional de medição.

## Entrada na edição

A função JavaScript observada:

`editarMedicao(id_medicao,id_contrato,id_aditivo,id_rotina)`

faz:

```text
POST medicoesMOEdita.cfm
```

enviando:

```text
id_medicao
id_contrato
id_aditivo
id_rotina
```

---

# 9. CARREGAMENTO DOS ITENS

A página posteriormente chama:

```text
POST medicaoMOEditaServicos.cfm
```

Parâmetros:

```text
id_contrato
id_aditivo
id_medicao
id_rotina
```

A resposta HTML contém os serviços pertencentes à medição.

Outras chamadas observadas:

```text
medicaoMOEditaObservacao.cfm
medicaoMOEditaRodapeValores.cfm
medicaoMOEditaRodapeReprovacao.cfm
```

---

# 10. GRAVAÇÃO DE ITEM MEDIDO

## SEC-003 — Endpoint direto de atualização de item

Endpoint:

`_medicoesEdita.cfm`

Método:

`POST`

Função JavaScript:

`validandoDadosServicoMedicao(id)`

O botão Salvar não executa submit convencional.

Ele executa JavaScript e, após algumas validações, envia AJAX diretamente para `_medicoesEdita.cfm`.

Foram observados os seguintes parâmetros enviados pelo cliente:

```text
quantidade
qtdAcu
porcentAtual
id_material
acumuladoMedido
quantMed
quantContrato
preco
quantidadeAcumulada2
vlContrato
id_medicao
id_aditivo
id_contrato
id_centroCusto
id_medicaott
med_obs_memo
```

## Classificação

O envio desses parâmetros é **CONFIRMADO**.

A existência de confiança server-side nesses valores é **A VERIFICAR**.

---

# 11. SEC-004 — QUANTIDADE EXCESSIVA DE DADOS DE NEGÓCIO CONFIADOS AO CLIENTE

**Classificação:** INDÍCIO FORTE.

**Criticidade se confirmada:** ALTA.

O navegador envia não somente a informação alterada pelo usuário, mas diversos valores que poderiam ser recuperados diretamente pelo servidor.

Exemplos:

```text
preco
quantContrato
vlContrato
qtdAcu
acumuladoMedido
quantidadeAcumulada2
porcentAtual
```

Para uma aplicação segura, dados como:

- preço contratual;
- quantidade contratada;
- valor do contrato;
- acumulado anterior;
- saldo;

não deveriam ser aceitos como fonte de verdade somente porque foram enviados pelo navegador.

O servidor já possui essas informações no banco.

## Verificação necessária

Analisar `_medicoesEdita.cfm` e o DAO chamado por ele.

Determinar se:

### Cenário adequado

O endpoint ignora/revalida esses valores e consulta novamente o banco.

### Cenário vulnerável

O endpoint utiliza diretamente os valores enviados pelo navegador para efetuar cálculos ou atualizar registros.

Esse é um dos pontos de maior prioridade da análise.

---

# 12. SEC-005 — VALIDAÇÃO DE QUANTIDADE EXECUTADA NO JAVASCRIPT

**Classificação:** CONFIRMADO.

A função `validandoDadosServicoMedicao()` calcula no navegador:

```text
acumuladoReal =
quantidadeAcumulada2 - qtdMedidaAnterior
```

Depois:

```text
verificaQtd =
acumuladoReal + quantidade medida
```

E compara com:

```text
quantContrato
```

Caso a quantidade projetada ultrapasse a contratada, o JavaScript bloqueia o envio.

Portanto, existe claramente uma validação client-side.

---

# 13. CONTROLE POSITIVO — O SERVIDOR TAMBÉM PARECE VALIDAR QUANTIDADE

**Classificação:** CONTROLE IDENTIFICADO / requer confirmação de implementação.

A resposta de `_medicoesEdita.cfm` possui códigos interpretados pelo JavaScript:

```text
0 = sucesso

1 = quantidade medida superior à quantidade prevista

2 = acumulado menor que o da medição anterior

3 = erro
```

Isso constitui forte evidência de que existe ao menos alguma validação server-side relacionada à quantidade e ao acumulado.

Não considerar, portanto, que toda a regra existe apenas no JavaScript.

## Próxima análise

Verificar no código:

- de onde são obtidos os valores usados nessa validação;
- se vêm novamente do banco;
- ou se o servidor compara valores que o próprio navegador enviou.

Essa diferença é fundamental.

---

# 14. CENTRO DE CUSTO

A tela contém um seletor:

`id_centrocusto{item}`

Valor especial observado:

`0000000`

representando ausência de centro de custo.

O JavaScript impede determinada gravação quando:

- existe quantidade medida;
- e o centro de custo permanece `0000000`.

Mensagem:

`Selecione o Centro de Custo`

---

# 15. CONTROLE POSITIVO — VALIDAÇÃO SERVER-SIDE DE CENTRO DE CUSTO

**Classificação:** CONTROLE IDENTIFICADO.

No processo de aprovação/baixa existem retornos server-side indicando ausência de centro de custo.

No endpoint:

`_medicoesBaixa.cfm`

o retorno:

```text
-1
```

é interpretado como:

`Informe o centro de custo nos serviços medidos.`

O mesmo tipo de proteção aparece na aprovação:

`_medicoesAprova.cfm`

com retorno `-1`.

Isso indica que a aplicação não depende exclusivamente do JavaScript para essa regra.

## Ponto ainda necessário

Analisar se `_medicoesEdita.cfm` também valida imediatamente o centro de custo ou se a inconsistência somente é detectada na aprovação/baixa.

---

# 16. RECÁLCULO DOS VALORES DA MEDIÇÃO

Após `_medicoesEdita.cfm` retornar sucesso, o JavaScript chama:

`atualizarValoreRodape()`

Essa função serializa:

`formMedicaoAprovar`

e envia:

```text
POST cfcs/medicao_DAO.cfc?method=atualizarValoresRodape
```

Depois a tela carrega novamente:

`medicaoMOEditaRodapeValores.cfm`

## SEC-006 — MÉTODO CFC CHAMADO DIRETAMENTE PELO NAVEGADOR

**Classificação:** CONFIRMADO quanto à exposição funcional.

**Risco:** A VERIFICAR.

É necessário analisar:

`cfcs/medicao_DAO.cfc`

especialmente o método:

`atualizarValoresRodape`

Verificar:

- `access="remote"`;
- autenticação;
- autorização;
- validação dos IDs;
- origem dos valores;
- uso de `cfqueryparam`;
- transações.

---

# 17. APROVAÇÃO DE MEDIÇÃO

Foram identificadas duas funções relacionadas:

`aprovacaoUltimaMedicao()`

e:

`aprovarMedicaoEdicao()`

Ambas chamam:

```text
POST _medicoesAprova.cfm
```

A página contém comentário JavaScript afirmando, em essência, que somente o engenheiro responsável pode aprovar a última medição.

## SEC-007 — AUTORIZAÇÃO DE APROVAÇÃO PRECISA SER COMPROVADA NO SERVIDOR

**Classificação:** A VERIFICAR.

**Criticidade potencial:** CRÍTICA/ALTA.

A existência de um botão condicionado ao perfil ou de JavaScript específico não é suficiente para garantir autorização.

Deve ser localizada dentro de `_medicoesAprova.cfm` ou função server-side equivalente uma regra que determine:

```text
usuário autenticado
→ perfil
→ responsabilidade pela obra/contrato
→ direito de aprovar aquela medição
```

Não testar por troca de usuário ou IDs.

Verificar exclusivamente por análise de código.

---

# 18. DADOS ENVIADOS NA APROVAÇÃO

O formulário `formMedicaoAprovar` contém, entre outros:

```text
id_contrato
id_aditivo
id_medicao
responsavel
vDesconto
retencao
retencaoZero
valorNotaFiscal
totalPagar
vsaldoContrato
obsAprovacao
```

Alguns desses campos são `hidden`.

## SEC-008 — VALORES FINANCEIROS ENVIADOS PELO CLIENTE

**Classificação:** INDÍCIO FORTE.

**Criticidade se confiados diretamente:** ALTA.

Os seguintes valores merecem especial revisão:

```text
vDesconto
retencao
valorNotaFiscal
totalPagar
vsaldoContrato
```

Campos HTML ocultos **não são controles de segurança**.

O servidor precisa recalcular ou validar esses valores com os registros originais.

Verificar `_medicoesAprova.cfm`.

---

# 19. VALIDAÇÃO DE TOTAL NEGATIVO

Antes da aprovação, o JavaScript executa:

```text
if totalPagar < 0
    impedir aprovação
```

Essa é uma validação client-side.

## Status

**CONFIRMADO:** validação no navegador.

**A VERIFICAR:** existência da mesma regra no servidor.

Também existe confirmação especial para aprovação quando o total é zero.

A confirmação visual não constitui controle server-side.

---

# 20. BAIXA DA MEDIÇÃO

Função:

`baixarMedicao(...)`

Endpoint:

```text
POST _medicoesBaixa.cfm
```

A interface verifica:

- número da NF;
- data da NF;
- total igual a zero;
- centro de custo mediante resposta server-side.

O botão é desabilitado durante a requisição para evitar duplicidade.

## SEC-009 — PROTEÇÃO DE DUPLICIDADE SOMENTE VISÍVEL NO CLIENTE

**Classificação:** A VERIFICAR.

O comentário no JavaScript afirma que o botão é desabilitado para evitar duplicidade.

Isso protege contra duplo clique na interface, mas não substitui:

- idempotência;
- locking;
- unique constraints;
- verificação de status server-side;
- transação.

Revisar `_medicoesBaixa.cfm`.

---

# 21. EXCLUSÃO DA MEDIÇÃO

Função:

`medicaoExcluirEdicao()`

Endpoint:

```text
POST _medicoesExclui.cfm
```

A proteção observável no cliente é uma caixa de confirmação:

`Deseja excluir a medição do sistema?`

Depois da confirmação, o formulário é serializado e enviado ao endpoint.

## SEC-010 — AUTORIZAÇÃO DE EXCLUSÃO

**Classificação:** A VERIFICAR.

**Criticidade potencial:** ALTA.

Verificar obrigatoriamente se `_medicoesExclui.cfm` valida no servidor:

- usuário autenticado;
- perfil;
- direito sobre contrato/obra;
- estado atual da medição;
- possibilidade de exclusão;
- relacionamento entre IDs.

Não considerar a caixa de confirmação como controle de segurança.

---

# 22. PROBLEMA DE TRATAMENTO DE RETORNO NA EXCLUSÃO

**Classificação:** CONFIRMADO como deficiência de interface/integridade de feedback.

No callback `success` da exclusão, o JavaScript exibe:

`Registro excluído com sucesso.`

sem interpretar aparentemente o conteúdo retornado em `r`.

Isso significa que uma resposta HTTP considerada tecnicamente bem-sucedida pelo AJAX pode produzir mensagem de sucesso independentemente do resultado funcional, dependendo do comportamento server-side.

## Impacto

- usuário pode receber confirmação incorreta;
- dificuldade de auditoria;
- divergência entre interface e estado real;
- ocultação de erro lógico.

---

# 23. REPROVAÇÃO DA MEDIÇÃO

Função:

`medicaoReprovarEdicao()`

Endpoint:

```text
POST _medicoesReprova.cfm
```

A interface exige motivo de reprovação.

O JavaScript verifica apenas se o campo possui conteúdo.

Depois envia:

```text
id_contrato
id_aditivo
id_medicao
obs
```

## SEC-011 — REPROVAÇÃO E AUTORIZAÇÃO

**Classificação:** A VERIFICAR.

O servidor deve garantir que o usuário possui direito de reprovação da medição.

A verificação client-side de existência do texto não substitui autorização.

---

# 24. OBSERVAÇÕES DA MEDIÇÃO

Função:

`editarObsMedicao()`

Endpoint:

```text
POST _medicaoEditaObs.cfm
```

São enviados:

```text
id_contrato
id_aditivo
id_medicao
observacao
```

## SEC-012 — ENTRADA TEXTUAL PERSISTENTE A REVISAR

**Classificação:** A VERIFICAR.

O campo `observacao` é entrada textual persistente.

Revisar:

- parametrização SQL;
- encoding de saída;
- `encodeForHTML`;
- `encodeForHTMLAttribute`;
- `encodeForJavaScript`;
- uso posterior em `.html()`.

Essa revisão é necessária para avaliar risco de XSS persistente ou falhas de SQL.

Não executar payloads.

---

# 25. ALTERAÇÃO DO PERÍODO DA MEDIÇÃO

Função:

`alterarPeriodoMedicao(id_medicao,id_contrato,id_aditivo)`

Endpoint:

```text
POST _medicao_periodo_editar.cfm
```

Parâmetros:

```text
id_contrato
id_aditivo
id_medicao
inicio
fim
```

O servidor retorna códigos específicos:

```text
1  = sucesso
-1 = conflito com medição anterior
-2 = conflito com medição posterior
-6 = data final anterior à inicial
-3 = data inicial incompatível com contrato
-4 = erro
```

## Controle positivo

**Classificação:** CONTROLE IDENTIFICADO.

Há evidência relevante de validação server-side das regras cronológicas.

Isso deve ser reconhecido no relatório final.

Ainda é necessário revisar:

- autorização;
- parametrização;
- origem das datas;
- transação.

---

# 26. AVALIAÇÃO DE PRESTADOR

Foram identificados os endpoints:

```text
medicao_avalia_percentual.cfm
medicaoMOAvaliacaoPrestador.cfm
_medicoes_prestador_avaliar.cfm
../cadastro/pontuacoes_prestador.cfm
../cadastro/pontuacoes_prestador_nota.cfm
```

O fluxo observado é:

aprovação da medição

→ verificar necessidade de avaliação

→ carregar formulário de avaliação

→ enviar notas

→ gravar avaliação.

O endpoint `_medicoes_prestador_avaliar.cfm` possui respostas tratadas, incluindo:

```text
0
-1
23000
```

O valor `23000` é interpretado como:

`Já existe pontuação lançada.`

Isso sugere algum mecanismo de integridade/constraint ou tratamento de duplicidade.

## Status

Necessário analisar server-side:

- autorização;
- relação entre avaliação e medição;
- identidade do avaliador;
- alteração das notas;
- repetição de lançamento;
- parametrização.

---

# 27. ENDPOINTS IDENTIFICADOS NO HTML DA MEDIÇÃO

Até o momento foram observados pelo menos os seguintes endpoints AJAX:

```text
../cadastro/pontuacoes_prestador.cfm

../cadastro/pontuacoes_prestador_nota.cfm

../cfcs/geral.cfc?method=buscaRamal

_medicaoEditaObs.cfm

_medicao_periodo_editar.cfm

_medicoesAprova.cfm

_medicoesBaixa.cfm

_medicoesEdita.cfm

_medicoesExclui.cfm

_medicoesReprova.cfm

_medicoes_prestador_avaliar.cfm

cfcs/medicao_DAO.cfc?method=atualizarValoresRodape

medicaoMOAvaliacaoPrestador.cfm

medicaoMOEditaObservacao.cfm

medicaoMOEditaRodapeReprovacao.cfm

medicaoMOEditaRodapeValores.cfm

medicaoMOEditaServicos.cfm

medicao_avalia_percentual.cfm

medicoesMOEdita.cfm

medicoesMOLista2.cfm

popuphistoricomedicao.cfm
```

Essa lista deve ser utilizada como ponto de partida ao correlacionar novos ZIPs.

---

# 28. RELATÓRIOS E ANEXOS COM IDs EM URL

Foram observadas chamadas como:

```text
anexoMemoriaCalculoMed1.cfm
```

e:

```text
relatorio_contrato_rel04.cfm
```

com diversos identificadores na query string, incluindo referências a:

- contrato;
- aditivo;
- medição;
- obra;
- rotina;
- status;
- situação.

## SEC-013 — AUTORIZAÇÃO OBJETO A OBJETO EM RELATÓRIOS E ANEXOS

**Classificação:** A VERIFICAR.

**Criticidade potencial:** ALTA.

O simples uso de IDs na URL não é vulnerabilidade.

O ponto crítico é verificar se essas páginas realizam autorização server-side antes de retornar:

- relatório;
- memória;
- documento;
- anexo.

Não testar troca de IDs.

Revisar código.

---

# 29. SEC-014 — AUTORIZAÇÃO OBJETO A OBJETO É O PRINCIPAL PONTO PENDENTE

A arquitetura observada utiliza extensivamente identificadores enviados pelo navegador:

```text
id_contrato
id_aditivo
id_medicao
id_material
id_medicaott
id_rotina
id_prestador
id_apuracao
id_responsavel
```

A existência desses IDs no cliente é normal.

O risco existe se o servidor fizer algo equivalente a:

```text
receber ID
→ localizar registro
→ alterar
```

sem verificar:

```text
usuário
→ perfil/permissão
→ obra
→ contrato
→ medição
→ item
```

## Classificação atual

**A VERIFICAR — PRIORIDADE MÁXIMA**

Possível classe, se inexistente:

- Broken Access Control;
- IDOR;
- BOLA.

Não classificar como confirmado sem o código.

---

# 30. SEC-015 — POSSÍVEL AUSÊNCIA DE PROTEÇÃO CSRF

**Classificação:** INDÍCIO FORTE / A VERIFICAR.

Na página HTML analisada não foi identificado token explicitamente relacionado a:

```text
csrf
token
nonce
```

As alterações são realizadas por diversos `POST` AJAX.

Exemplos:

```text
_medicoesEdita.cfm
_medicoesAprova.cfm
_medicoesBaixa.cfm
_medicoesExclui.cfm
_medicoesReprova.cfm
_medicao_periodo_editar.cfm
_medicaoEditaObs.cfm
```

## Não concluir ainda

A ausência de token no HTML não é suficiente para confirmar CSRF porque podem existir outros mecanismos:

- cookie `SameSite`;
- verificação de `Origin`;
- verificação de `Referer`;
- header customizado;
- filtro global;
- proteção no `Application.cfc`.

## Próxima análise

Verificar:

- `Application.cfc`;
- headers;
- configuração dos cookies;
- endpoints de escrita.

---

# 31. SEC-016 — VALIDAÇÃO CLIENT-SIDE NÃO DEVE SER CONSIDERADA SEGURANÇA

A tela executa várias regras em JavaScript.

Exemplos:

- quantidade máxima;
- centro de custo;
- total negativo;
- NF obrigatória;
- motivo da reprovação;
- notas obrigatórias;
- confirmações;
- prevenção de duplo clique.

Isso é adequado para experiência do usuário.

Porém qualquer regra relevante à:

- segurança;
- financeiro;
- contrato;
- integridade;

precisa existir novamente no servidor.

A análise deve produzir uma matriz:

| Regra | Navegador | Servidor | Resultado |
|---|---|---|---|

---

# 32. SEC-017 — USO DE `eval()` NO JAVASCRIPT

**Classificação:** CONFIRMADO.

Foram observadas chamadas como:

```javascript
eval($("#quantidadeAcumulada2" + id).val())
eval($("#qtdMedidaAnterior" + id).val())
eval($("#quantContrato" + id).val())
```

Também existe comentário indicando que anteriormente a quantidade digitada era processada com `eval`, prática posteriormente removida para aquele campo específico.

## Avaliação

O uso de `eval()` para converter números é desnecessário e deve ser eliminado.

Utilizar:

```javascript
parseFloat(...)
```

ou validação numérica equivalente.

## Criticidade preliminar

BAIXA/MÉDIA isoladamente.

Pode assumir maior relevância caso alguma origem da string seja controlável por entrada não confiável.

Não classificar como execução de código confirmada.

---

# 33. SEC-018 — ESTRUTURA DOM COM IDs REPETIDOS

**Classificação:** CONFIRMADO.

O HTML apresenta repetição de identificadores que deveriam ser únicos.

Exemplos observados:

- diversos `id="id_contrato"`;
- diversos `id="id_aditivo"`;
- diversos `id="id_medicao"`;
- vários formulários utilizando `id="medicaoEdita"`.

Isso viola a expectativa de unicidade dos IDs no DOM.

## Impacto principal

Integridade funcional e previsibilidade.

Seletores como:

```javascript
$("#id_contrato")
```

podem depender implicitamente do primeiro elemento correspondente.

Se futuramente elementos repetidos possuírem valores divergentes, funções podem capturar contexto incorreto.

## Recomendação

Usar:

- IDs únicos;
- `data-*`;
- seletores relativos à linha;
- objetos JavaScript estruturados.

---

# 34. SEC-019 — AUSÊNCIA DE MECANISMO DE CONCORRÊNCIA VISÍVEL

**Classificação:** A VERIFICAR.

Não foi identificado na página algo claramente equivalente a:

- version number;
- rowversion;
- timestamp de concorrência;
- optimistic locking token.

Isso não significa que inexista no servidor.

## Risco

Dois usuários podem potencialmente:

1. carregar o mesmo estado;
2. alterar o mesmo item;
3. gravar em momentos diferentes;
4. sobrescrever decisões baseadas em estado antigo.

É especialmente relevante para:

- medições;
- aprovação;
- valores acumulados;
- baixa.

Revisar DAO e banco.

---

# 35. SEC-020 — TRANSACIONALIDADE

**Classificação:** A VERIFICAR.

O lançamento da medição ocorre item por item.

Cada serviço executa uma requisição independente.

Isso implica que, em um processo automatizado ou manual sequencial, pode ocorrer:

```text
item 1 → salvo
item 2 → salvo
item 3 → erro
item 4 → não processado
```

Não existe evidência atual de transação abrangendo múltiplos itens.

Para o fluxo manual atual isso pode ser decisão arquitetural.

Para integração em lote deve ser revisado.

---

# 36. AUTOMAÇÃO EXCEL PLANEJADA — CONTEXTO

Está sendo estudada uma integração Excel → Sistema para lançamento automatizado da memória de medição.

O objetivo NÃO é simular mouse/cliques.

Pretende-se utilizar diretamente a mesma lógica HTTP utilizada pela interface.

Fluxo ideal:

```text
Excel
↓
validação local
↓
integração controlada
↓
endpoint server-side
↓
validação central
↓
banco
```

A análise do HTML confirmou que tecnicamente isso é possível porque o próprio botão Salvar utiliza AJAX.

---

# 37. RISCOS DA AUTOMAÇÃO SE O ENDPOINT ATUAL FOR UTILIZADO DIRETAMENTE

O principal risco identificado é a possibilidade de o integrador confiar apenas em:

```text
id_contrato
id_aditivo
id_medicao
```

informados pelo Excel.

Se houver identificação errada de uma medição, uma automação poderia processar vários itens rapidamente no contexto incorreto.

Por isso, a integração deverá validar no mínimo:

```text
contrato
aditivo
obra
prestador
medição
item
preço
unidade
quantidade contratada
estado da medição
```

antes da primeira alteração.

---

# 38. CENTRO DE CUSTO NA AUTOMAÇÃO

A regra proposta é:

## Quando já existir centro de custo gravado

Utilizar o valor retornado pelo próprio sistema.

Não solicitar novamente ao usuário.

## Quando o serviço estiver sendo medido pela primeira vez

Se:

```text
quantidade > 0
```

e:

```text
centro de custo = 0000000
```

a integração deverá interromper o item e exigir seleção válida.

A lista deve preferencialmente ser obtida do próprio sistema.

Nunca inventar ou inferir centro de custo.

---

# 39. SEGURANÇA DA AUTOMAÇÃO

A integração deveria possuir três camadas:

## Camada 1 — pré-validação

Antes de qualquer POST:

- confirmar contrato;
- aditivo;
- obra;
- prestador;
- medição;
- item;
- quantidade;
- centro de custo;
- preço;
- estado.

## Camada 2 — validação nativa do servidor

Preservar integralmente:

- quantidade máxima;
- acumulado;
- centro de custo;
- permissões;
- status.

## Camada 3 — pós-validação

Após gravar:

- consultar novamente o item;
- conferir quantidade;
- conferir acumulado;
- registrar resultado.

---

# 40. RECOMENDAÇÃO PARA AUTOMAÇÃO FUTURA

Em vez de fazer centenas de POSTs diretamente ao endpoint legado, recomenda-se considerar posteriormente um pequeno endpoint interno específico para integração.

Exemplo arquitetural:

`medicaoLote.cfm`

ou um método CFC equivalente.

Ele receberia somente:

```text
id_medicao
itens
quantidade
centro de custo quando necessário
observação
```

E recuperaria todos os demais dados do banco.

Fluxo:

```text
autenticar
↓
autorizar
↓
buscar contexto da medição
↓
validar todos os itens
↓
iniciar transação
↓
gravar
↓
recalcular
↓
auditar
↓
commit
```

Em qualquer falha:

```text
rollback
```

Essa recomendação não exige reescrever o sistema.

---

# 41. DEPENDÊNCIAS FRONT-END IDENTIFICADAS

O ZIP contém versões identificáveis de bibliotecas.

Entre elas:

## jQuery legado

Arquivo:

`jquery.min.js.download`

Cabeçalho:

`jQuery JavaScript Library v1.3.2`

Data indicada no próprio arquivo: 2009.

## jQuery adicional

Também existe:

`jquery-3.6.0.min.js.download`

Portanto há evidência de coexistência de gerações muito distintas do jQuery entre os recursos da aplicação.

## CKEditor

Versão identificada:

`4.10.1`

## DataTables

Arquivo analisado:

`jquery.dataTables.min.js.download`

Versão:

`1.9.4`

## jQuery UI

Versão identificada:

`1.13.1`

---

# 42. SEC-021 — DEPENDÊNCIAS LEGADAS

**Classificação:** CONFIRMADO quanto às versões presentes.

**Vulnerabilidade específica:** A VERIFICAR.

O sistema carrega bibliotecas antigas, inclusive componentes com muitos anos de diferença entre versões.

Isso deve motivar levantamento completo de dependências.

Não concluir automaticamente que uma CVE específica é explorável apenas pela versão.

Claude deverá, se solicitado posteriormente, montar inventário:

```text
biblioteca
versão
arquivo
onde é utilizada
necessidade
versão suportada atual
risco de atualização
```

Também avaliar coexistência de múltiplas versões de jQuery.

---

# 43. SEC-022 — POSSÍVEIS SINKS DE XSS

**Classificação:** A VERIFICAR.

A página utiliza repetidamente padrões como:

```javascript
$("#elemento").html(retorno)
```

para inserir respostas provenientes de endpoints CFM no DOM.

Isso é comum em aplicações AJAX e não constitui vulnerabilidade por si só.

Entretanto existem também campos de texto controlados por usuário, como:

- observações;
- motivo de reprovação;
- observação da aprovação;
- observação da memória.

Deve-se verificar como esses dados são posteriormente renderizados.

Pesquisar por:

```text
cfoutput
html()
innerHTML
write()
encodeForHTML
encodeForHTMLAttribute
encodeForJavaScript
htmlEditFormat
```

Não realizar payload XSS.

---

# 44. SEC-023 — `encodeURI()` NÃO É SANITIZAÇÃO

No fluxo de reprovação existe algo equivalente a:

```javascript
encodeURI($("#obs_reprovar").val())
```

porém o valor serializado pelo formulário segue sendo enviado ao servidor.

Além disso, `encodeURI` não constitui mecanismo de proteção contra:

- XSS;
- SQL Injection;
- HTML Injection.

Não considerar essa chamada uma proteção de segurança.

A validação correta deve ocorrer no contexto adequado no servidor e na saída.

---

# 45. SEC-024 — POST NÃO É CONTROLE DE SEGURANÇA

Diversas operações sensíveis utilizam corretamente `POST`, entre elas:

- editar;
- aprovar;
- baixar;
- reprovar;
- excluir.

Entretanto o uso de `POST` não substitui:

- autenticação;
- autorização;
- CSRF;
- validação;
- auditoria.

Cada endpoint deve ser analisado individualmente.

---

# 46. CONTROLES POSITIVOS JÁ OBSERVADOS

O diagnóstico não deve tratar o sistema como se não possuísse segurança alguma.

Foram encontrados sinais de controles server-side.

## Quantidade medida

`_medicoesEdita.cfm` possui retornos relacionados a quantidade e acumulado.

## Centro de custo

`_medicoesAprova.cfm` e `_medicoesBaixa.cfm` sinalizam centro de custo ausente.

## Período

`_medicao_periodo_editar.cfm` devolve códigos distintos para diferentes violações cronológicas.

## Avaliação duplicada

O fluxo de avaliação trata retorno `23000` como existência de pontuação já lançada.

Esses controles deverão ser investigados no código antes de qualquer conclusão negativa.

---

# 47. POSSÍVEL PADRÃO ARQUITETURAL

Com os elementos atuais, existe um **indício** de uma arquitetura típica de aplicação ColdFusion legada:

```text
HTML/JavaScript
↓
CFM de interface
↓
CFM de ação iniciado por "_"
↓
CFC/DAO
↓
SQL Server
```

Exemplos:

```text
medicoesMOEdita.cfm
↓
_medicoesEdita.cfm
↓
medicao_DAO.cfc
```

E:

```text
npedido_print.cfm
↓
pedido_DAO2.cfc
```

Essa hipótese deverá ser testada contra os próximos módulos fornecidos.

---

# 48. RISCO DE SEGURANÇA ARQUITETURAL MAIS IMPORTANTE

Até o momento, o maior risco potencial não é a existência dos endpoints AJAX.

O ponto fundamental é determinar **onde a confiança termina**.

O modelo seguro precisa ser:

```text
CLIENTE NÃO CONFIÁVEL
↓
servidor valida sessão
↓
servidor valida autorização
↓
servidor valida relacionamento dos IDs
↓
servidor consulta valores oficiais
↓
servidor aplica regras
↓
DAO parametriza SQL
↓
banco
```

Se algum endpoint fizer:

```text
cliente envia ID + preço + quantidade + contrato
↓
servidor aceita
↓
UPDATE
```

o risco é elevado.

Essa questão deve orientar os próximos ZIPs.

---

# 49. MATRIZ PRELIMINAR DOS ACHADOS

| ID | Achado | Evidência | Criticidade preliminar | Situação |
|---|---|---|---|---|
| SEC-001 | Entrada externa incorporada à SQL | Dump da consulta | Alta | Confirmado quanto à concatenação |
| SEC-002 | Stack trace/SQL/path expostos | Página de erro | Alta | Confirmado |
| SEC-003 | Endpoint direto para alterar item | HTML/JS | Informativo/arquitetural | Confirmado |
| SEC-004 | Dados de negócio derivados enviados pelo cliente | POST `_medicoesEdita.cfm` | Alta se confiados | Indício forte |
| SEC-005 | Limite de quantidade validado no navegador | JavaScript | Médio/Alto | Confirmado |
| SEC-006 | Método CFC chamado diretamente pelo cliente | JavaScript | A definir | Confirmado |
| SEC-007 | Autorização para aprovação | Não localizada | Alta/Crítica se ausente | A verificar |
| SEC-008 | Valores financeiros no formulário de aprovação | HTML | Alta se confiados | Indício forte |
| SEC-009 | Prevenção de dupla baixa pelo botão | JavaScript | Médio | A verificar server-side |
| SEC-010 | Autorização de exclusão | Não localizada | Alta | A verificar |
| SEC-011 | Autorização de reprovação | Não localizada | Alta | A verificar |
| SEC-012 | Campos persistentes de observação | HTML/JS | Médio/Alto | A verificar |
| SEC-013 | Relatórios/anexos com IDs | URL gerada pela tela | Alta se sem autorização | A verificar |
| SEC-014 | Autorização objeto a objeto | Arquitetura | Crítica se ausente | A verificar |
| SEC-015 | Token CSRF não observado | HTML | Alta se proteção inexistente | Indício/A verificar |
| SEC-016 | Regras relevantes no client-side | JavaScript | Médio/Alto | Confirmado |
| SEC-017 | Uso de `eval()` | JavaScript | Baixa/Média | Confirmado |
| SEC-018 | IDs DOM duplicados | HTML | Média/integridade | Confirmado |
| SEC-019 | Controle de concorrência não observado | HTML | Médio | A verificar |
| SEC-020 | Transação multi-item não observada | Fluxo | Médio | A verificar |
| SEC-021 | Bibliotecas legadas | Arquivos JS | Médio/A verificar | Confirmado quanto às versões |
| SEC-022 | `.html()` com respostas + campos textuais | JavaScript | Médio/Alto se não codificado | A verificar |
| SEC-023 | Uso inadequado de `encodeURI` como aparente tratamento | JavaScript | Baixo/Médio | Confirmado |
| SEC-024 | Endpoints sensíveis baseados em POST | Arquitetura | Informativo | Confirmado |

---

# 50. CONTROLES POSITIVOS PRELIMINARES

| ID | Controle | Evidência | Situação |
|---|---|---|---|
| CTRL-001 | Rejeição server-side de quantidade inválida aparente | retorno `1` | Identificado |
| CTRL-002 | Validação de acumulado aparente | retorno `2` | Identificado |
| CTRL-003 | Centro de custo obrigatório antes de aprovação/baixa | retorno `-1` | Identificado |
| CTRL-004 | Validação cronológica do período | vários retornos negativos | Identificado |
| CTRL-005 | Tratamento de avaliação duplicada | retorno `23000` | Identificado |
| CTRL-006 | Confirmações para operações críticas | JavaScript | UX, não segurança server-side |
| CTRL-007 | Desabilitação do botão durante baixa | JavaScript | UX/anti-duplo clique |

---

# 51. PRIORIDADE PARA OS PRÓXIMOS ARQUIVOS

Se disponíveis, analisar primeiro:

## Prioridade máxima

`Application.cfc`

Motivo:

- autenticação global;
- autorização global;
- tratamento de erros;
- sessão;
- filtros;
- proteção de endpoints;
- possível CSRF;
- logging.

## Pedido

`suprimento/cfcs/pedido_DAO2.cfc`

Especialmente:

`GETPRINTORDER`

linha aproximadamente 141.

## Medição

```text
_medicoesEdita.cfm
_medicoesAprova.cfm
_medicoesBaixa.cfm
_medicoesExclui.cfm
_medicoesReprova.cfm
_medicao_periodo_editar.cfm
_medicaoEditaObs.cfm
cfcs/medicao_DAO.cfc
```

---

# 52. O QUE PROCURAR NOS CFM/CFC

Pesquisar sistematicamente por:

```text
URL.
FORM.
COOKIE.
CGI.
SESSION.
arguments.

cfquery
cfqueryparam

queryExecute

INSERT
UPDATE
DELETE
SELECT

access="remote"

cftransaction

cfabort
cfthrow
cfcatch

encodeForHTML
encodeForJavaScript
encodeForURL

htmlEditFormat

createUUID

csrf
token

session.user
session.usuario
session.id
```

---

# 53. REGRAS PARA AUDITORIA DE SQL

Para cada query, determinar:

### Entrada

Qual dado é externo?

### Conversão

Ele é convertido para tipo?

### Parametrização

Existe `cfqueryparam`?

### Autorização

A query limita o resultado ao contexto permitido ao usuário?

### Integridade relacional

Exemplo correto conceitualmente:

```text
medição pertence ao contrato?
contrato pertence à obra?
usuário pode operar a obra?
item pertence à medição?
```

Não basta validar individualmente que os IDs existem.

---

# 54. PADRÃO DE CORREÇÃO RECOMENDADO — SEM REESCREVER O SISTEMA

A aplicação parece adequada para uma estratégia incremental.

Criar uma camada central, por exemplo:

```text
security.cfc
authorization.cfc
validation.cfc
```

Funções conceituais:

```text
exigirSessao()

podeEditarContrato()

podeEditarMedicao()

medicaoPertenceContrato()

itemPertenceMedicao()

medicaoEstaAberta()

centroCustoValido()

validarQuantidadeMedida()
```

Depois cada endpoint legado chama essa camada antes de executar sua lógica existente.

---

# 55. PARAMETRIZAÇÃO SQL

Substituir progressivamente construções do tipo:

```cfml
WHERE ID_PEDIDO = #valor#
```

por parâmetros tipados:

```cfml
WHERE ID_PEDIDO =
<cfqueryparam
    value="#valor#"
    cfsqltype="cf_sql_integer">
```

Para listas legítimas utilizar mecanismo de lista parametrizada adequado.

Priorizar inicialmente:

```text
INSERT
UPDATE
DELETE
```

e consultas acessíveis por parâmetros externos.

---

# 56. REDUZIR DADOS CONFIADOS AO CLIENTE

O cliente deveria enviar preferencialmente apenas:

```text
identificador da operação
identificador do objeto
valor realmente informado pelo usuário
```

O servidor deve buscar:

```text
preço
quantidade contratada
saldo
acumulado
valor contratual
status
obra
fornecedor/prestador
relacionamentos
```

diretamente do banco.

---

# 57. AUTORIZAÇÃO CENTRAL

Uma função central deve conseguir responder:

```text
Este usuário pode executar ESTA ação sobre ESTE objeto?
```

Não somente:

```text
Este usuário está logado?
```

Exemplo conceitual:

```text
podeEditarMedicao(
    usuario,
    id_medicao
)
```

Internamente:

```text
medição
↓
contrato
↓
obra
↓
permissões do usuário
```

---

# 58. CSRF

Se não existir proteção equivalente, implementar de forma incremental.

Priorizar endpoints de escrita:

```text
editar
aprovar
baixar
excluir
reprovar
alterar período
alterar observação
```

A existência de proteção precisa ser verificada primeiro.

---

# 59. TRATAMENTO DE ERROS

Usar tratamento global no `Application.cfc`.

Externamente retornar:

```text
erro genérico
+
identificador único
```

Internamente registrar:

```text
usuário
data/hora
endpoint
objeto
erro
stack trace
identificador
```

Nunca retornar ao navegador:

- SQL completo;
- caminhos físicos;
- stack trace;
- datasource;
- detalhes JDBC.

---

# 60. AUDITORIA

Operações de alto impacto deveriam possuir registro de:

```text
usuário
data/hora
IP/origem
sessão
ação
objeto
valor anterior
valor novo
motivo
resultado
```

Priorizar:

- medição;
- aprovação;
- baixa;
- exclusão;
- reprovação;
- alterações financeiras;
- contrato;
- pedido.

---

# 61. CONCORRÊNCIA

Avaliar uso de:

- `rowversion`;
- número de versão;
- timestamp;
- optimistic locking.

Antes de atualizar:

```text
estado que usuário carregou
==
estado atual?
```

Se não:

```text
rejeitar
+
solicitar recarga
```

Isso é especialmente importante na automação via Excel.

---

# 62. CONCLUSÃO PRELIMINAR

Com base apenas no material analisado, já é possível afirmar que existem **fragilidades relevantes que justificam uma revisão estruturada da segurança da aplicação**.

As duas evidências mais importantes são:

1. entrada externa sendo incorporada à construção de SQL em consulta de pedido;

2. tratamento de exceções em produção expondo SQL, stack trace, estrutura interna e caminhos físicos.

A análise da tela de medição também demonstra uma arquitetura com grande quantidade de lógica e parâmetros controlados pelo cliente.

Entretanto, a própria tela mostra evidências de que determinadas regras também são verificadas server-side.

Portanto não é tecnicamente correto afirmar, neste momento, que:

- todas as validações podem ser burladas;
- qualquer usuário pode alterar qualquer contrato;
- existe IDOR confirmado;
- existe CSRF confirmado;
- existe SQL Injection explorável confirmada;
- valores financeiros podem efetivamente ser adulterados.

Esses são pontos prioritários de revisão dos próximos arquivos.

---

# 63. HIPÓTESE CENTRAL PARA A CONTINUIDADE DA INVESTIGAÇÃO

O objetivo principal dos próximos ZIPs deverá ser responder:

## Pergunta 1

A concatenação SQL identificada no módulo de pedido é um caso isolado ou um padrão dos DAOs?

## Pergunta 2

As regras observadas no JavaScript são repetidas no servidor utilizando dados oficiais do banco?

## Pergunta 3

Os endpoints validam autorização objeto a objeto ou apenas sessão/perfil?

## Pergunta 4

O servidor confia nos valores financeiros enviados pelo cliente?

## Pergunta 5

Existe proteção CSRF global?

## Pergunta 6

Existe camada central de segurança no `Application.cfc`?

## Pergunta 7

As operações críticas possuem auditoria adequada?

## Pergunta 8

As consultas usam `cfqueryparam` consistentemente?

## Pergunta 9

Os métodos CFC expostos ao navegador possuem controle de acesso?

## Pergunta 10

As bibliotecas legadas efetivamente continuam em uso nas funcionalidades críticas?

---

# 64. INSTRUÇÃO PARA OS PRÓXIMOS LOTES

Quando novos ZIPs forem fornecidos:

1. não reiniciar a análise do zero;

2. incorporar os arquivos ao inventário atual;

3. localizar dependências entre os módulos;

4. atualizar esta matriz;

5. fortalecer ou reduzir a classificação dos achados;

6. transformar "A VERIFICAR" em "CONFIRMADO" somente quando houver evidência;

7. registrar controles positivos encontrados;

8. identificar padrões repetitivos;

9. não realizar qualquer acesso externo;

10. não produzir payloads ofensivos.

Para cada nova evidência, registrar:

```text
arquivo
função
endpoint
parâmetro
trecho relevante
achado relacionado
classificação anterior
classificação nova
justificativa
```

---

# 65. RESULTADO FINAL ESPERADO

Ao término da análise de todos os módulos, produzir dois documentos.

## Documento executivo

Para Diretoria:

- linguagem empresarial;
- riscos;
- impacto;
- prioridades;
- plano de correção;
- esforço;
- cronograma;
- sem instruções de ataque.

## Anexo técnico

Para TI/desenvolvimento:

- arquivo;
- função;
- linha;
- endpoint;
- CWE;
- OWASP;
- causa;
- evidência;
- correção;
- exemplo de implementação segura.

O relatório deve privilegiar uma estratégia de **correção incremental**, porque as evidências atuais não indicam necessidade de reescrever toda a aplicação.

A arquitetura-alvo pode ser gradualmente transformada em:

```text
HTML / JS / Excel / Integrações
            ↓
     AUTENTICAÇÃO
            ↓
       AUTORIZAÇÃO
            ↓
   VALIDAÇÃO SERVER-SIDE
            ↓
     REGRA DE NEGÓCIO
            ↓
     DAO PARAMETRIZADO
            ↓
          BANCO
```

Este documento constitui o **baseline da auditoria**.

Não descarte suas conclusões ao receber novos arquivos. Atualize-as com base nas novas evidências.