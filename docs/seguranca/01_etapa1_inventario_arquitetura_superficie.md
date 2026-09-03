# ETAPA 1 — Inventário, arquitetura observável e mapa de superfície

**Sistema:** Sistema Gerencial — Almeida Sapata Engenharia (`sistema.almeidasapata.com.br`)
**Lotes analisados nesta etapa:** `AS.zip` (18 páginas) e `AS2.zip` (15 páginas), mais o baseline `00_baseline_contexto_tecnico.md`
**Natureza da análise:** estritamente passiva e estática, apenas sobre os arquivos enviados. Nenhuma requisição foi feita ao servidor, nenhum ID foi testado, nenhum payload foi gerado.
**Data:** 03/09/2026

Este documento **não** é o relatório executivo final. Ele consolida o inventário, reconstrói a arquitetura, mapeia endpoints, parâmetros, funções JavaScript, fluxos de gravação e CFCs, atualiza a matriz preliminar de achados (SEC-001 a SEC-024 do baseline) e lista o que precisa ser aprofundado.

Classificação de evidência usada em todo o documento: **CONFIRMADO**, **INDÍCIO FORTE**, **A VERIFICAR NO CÓDIGO/SERVIDOR**, **CONTROLE IDENTIFICADO**.

---

## 1. Inventário dos arquivos

### 1.1 Limitações do material

| Item | Situação |
|---|---|
| Fontes `.cfm` / `.cfc` | **Não fornecidos.** Toda inferência sobre o servidor vem de HTML entregue, JavaScript inline, códigos de retorno interpretados pelo JS e três páginas de erro. |
| Cabeçalhos HTTP / cookies | **Não disponíveis** (páginas salvas pelo navegador em modo "página completa"). Atributos `Secure`, `HttpOnly`, `SameSite`, `Set-Cookie`, `X-Frame-Options`, `CSP` não podem ser avaliados. |
| HAR / exportação de rede | Não fornecido. |
| Logs de servidor | Não fornecidos. |
| Fragmentos AJAX | Só os que estavam carregados no DOM no momento do salvamento (ex.: formulários de baixa/exclusão/reprovação da medição não estão no snapshot). |
| Reescrita do DOM | O "salvar página completa" do Chrome reserializa o DOM. Entidades HTML são normalizadas, o que **impede** concluir sobre ausência de `encodeForHTML` só pela saída. |

### 1.2 Páginas HTML (33) e PDF (1)

| # | Arquivo | URL de origem (`saved from url`) | Módulo / rotina | Tamanho | Tipo | JS inline |
|---|---|---|---|---|---|---|
| 1 | AS/LOGIN.html (AS2) | `/logon/indexDes.cfm` | logon | 8,5 KB | tela de login | 3,7 KB |
| 2 | AS/PRINCIPAL.html | `/logon/indexLog.cfm` | logon (menu) | 25 KB | menu principal | 1,7 KB |
| 3 | AS/NOVO-CONTRATO.html | `/servico/contratosNovo.cfm?id_rotina=38` | servico / 38 | 328 KB | cadastro | 12,5 KB |
| 4 | AS2/CONTRATOS-EMP1.html | `/servico/contratosLista.cfm?id_rotina=38` | servico / 38 | 340 KB | lista contratos serviço | 29 KB |
| 5 | AS2/CONTRATOS-EMP2.html | `/servico/contratosLista.cfm?id_rotina=38` | servico / 38 | 352 KB | lista + serviços do contrato aberto | 43 KB |
| 6 | AS2/ANEXO1.html | `/servico/anexoMemoriaCalculo.cfm?id_rotina=38&id_contrato=N&id_aditivo=0&id_material=N` | servico / 38 | 17,5 KB | popup anexos (upload) | 3,2 KB |
| 7 | AS2/MEDIÇÕES1.html | `/servico/medicoesMOLista.cfm?id_rotina=41` | servico / 41 | 147 KB | lista medições | 12,6 KB |
| 8 | AS2/MEDIÇÕES2.html | `/servico/medicoesMOLista.cfm?id_rotina=41` | servico / 41 | 240 KB | edição de medição aberta | 38,5 KB |
| 9 | AS/REL-CONT.html | `/servico/relContSeleciona.cfm?id_rotina=42` | servico / 42 | 43 KB | seleção de relatório | 4,4 KB |
| 10 | AS/REL-CONT2.html | `/servico/relatorio_contrato_rel01.cfm?id_rotina=96&...&id_contrato=N` | servico (via 96) | 4,9 KB | relatório (extrato) | 0,1 KB |
| 11 | AS/TABELA.html | `/servico/relatorio_tabela_rel01.cfm?id_rotina=55&...` | servico / 55 | 41 KB | relatório tabela | 4,1 KB |
| 12 | AS/TABELA2.html | `/servico/relatorio_tabela_rel01.cfm` (sem parâmetros) | servico | 51 KB | **página de erro (dump)** | — |
| 13 | AS/REL-PAGTO.html | `/servico/relatorio_contrato_fornecedor.cfm?id_rotina=105` | servico / 105 | 1,39 MB | relatório pagamentos | 12,5 KB |
| 14 | AS2/CLIENTE MEDIÇÕES.html | `/contrato/contrato_pesquisar_obras_coordenacao.cfm?id_rotina=70` | contrato / 70 | 135 KB | lista de obras (coordenação) | 22 KB |
| 15 | AS2/CONTRATO.html | `/contrato/contrato_pesquisar_obras_coordenacao.cfm?id_rotina=70` | contrato / 70 | 235 KB | edição de obra + gestão medições cliente | 80,6 KB |
| 16 | AS2/CONTRATOS2.html | `/contrato/contrato_pesquisar.cfm?id_rotina=78` | contrato / 78 | 222 KB | contratos comerciais | 12,2 KB |
| 17 | AS/NOVO-MAPA.html | `/mapaConcorrencia/smapa_listar.cfm?id_rotina=179` | mapaConcorrencia / 179 | 132 KB | cadastro de mapa | 67 KB |
| 18 | AS2/MAPA.html | `/mapaConcorrencia/smapa_listar.cfm?id_rotina=179` | mapaConcorrencia / 179 | 225 KB | mapa fase 3 | 80,9 KB |
| 19 | AS2/MAPA2.html | idem | idem | 224 KB | idem (JS idêntico ao MAPA.html) | 80,9 KB |
| 20 | AS2/MAPA3.html | idem | idem | 204 KB | mapa fase 3 com prestador aberto | 105,8 KB |
| 21 | AS/RMS1.html | `/suprimento/req_materiais_listar.cfm?id_rotina=153` | suprimento / 153 | 125 KB | requisição em edição | 39,5 KB |
| 22 | AS/RMS2.html | idem | idem | 134 KB | requisição + pesquisa de materiais | 43 KB |
| 23 | AS/REMESSA.htm | `/suprimento/romaneio_NF.cfm?id_rotina=161` | suprimento / 161 | 107 KB | remessas de NF | 18,4 KB |
| 24 | AS/PEDIDO.html | `/suprimento/npedido_print.cfm` (sem parâmetros) | suprimento | 63 KB | **página de erro (dump)** | — |
| 25 | AS2/MATERIAIS.html | `/pedido/relatorio_material.cfm?id_rotina=31` | pedido / 31 | 92 KB | relatório de materiais/pedidos | 6,6 KB |
| 26 | AS2/DESPESA.html | `/gerencial/gerencial_obras.cfm?id_rotina=96` | gerencial / 96 | 78 KB | filtro despesas | 6,6 KB |
| 27 | AS2/DESPESA2.htm | `/gerencial/gerencial_obras5.cfm?id_obra=N&DataInicial=&DataFinal=&id_rotina=96&idObra=N` | gerencial / 96 | 527 KB | relatório despesas da obra | 0,4 KB |
| 28 | AS/REL-TIL.htm | `/gerencial/gerencial_pedido_observacao.cfm?id_pedido=N` | gerencial | 2,4 KB | popup NF do pedido (**sem id_rotina**) | — |
| 29 | AS/REL-NF.htm | `/financeiro/titulosPagarVer.cfm?id_Titulo=N&flag_origem=1&id_rotina=96` | financeiro (via 96) | 5,7 KB | detalhe de título a pagar | — |
| 30 | AS/REL-NF2.htm | `/financeiro/titulosPagarVer.cfm?id_Titulo=&flag_origem=1&id_rotina=96` | financeiro | 246 KB | **página de erro SQL (dump)** | — |
| 31 | AS/RAMAIS.html | `/cadastro/relatorio_nextel.cfm?id_rotina=109` | cadastro / 109 | 202 KB | lista de ramais/e-mails | 3,1 KB |
| 32 | AS/REL-OBRAS | (sem extensão) | — | 375 KB | **PDF** de 10 páginas (relatório de obras) | — |
| 33 | `*_files/saved_resource.html` (2) | `about:blank` | — | 149 B | iframes vazios | — |

Observações do inventário:

- As pastas `AS/SENHA_files` e `AS/TABELA3_files` existem **sem a página HTML correspondente** (a tela de troca de senha `senhasEdita.cfm` e uma terceira "TABELA" não vieram no lote).
- `MAPA.html` e `MAPA2.html` têm JavaScript inline byte a byte idêntico (mesmo MD5).
- `PEDIDO.html`, `REL-NF2.htm` e `TABELA2.html` contêm o mesmo bloco de script (widget do Google Tradutor do navegador do analista), sem JS da aplicação.
- Todas as 22 telas "novas" (layout com jQuery 3.6) carregam o mesmo conjunto de 31 scripts (idênticos por hash entre páginas), então os JS auxiliares foram analisados uma única vez.

### 1.3 Scripts próprios da aplicação (deduplicados por hash)

| Arquivo | Tamanho | Conteúdo relevante |
|---|---|---|
| `funcoes.js` | 5,8 KB | `validarCPF`, `validarCNPJ`, `validacaoEmail`, `apagarRegistro(id_pessoa)` → `POST cfcs/pessoa_DAO.cfc method=capagarPessoa`, `buscarEndereco(cep)` → **fetch externo `https://viacep.com.br`** |
| `validacaoCampo.js` | 3,9 KB | máscaras/filtros de entrada client-side (números, e-mail) |
| `serializeFormJson.js` | 0,4 KB | monta JSON por concatenação de string e faz `JSON.parse` (quebra com aspas no valor) |
| `messagebox.js` | 20 KB | jQuery MessageBox 2.2.3 |
| `ajaxfileupload.js` | 6,7 KB | upload via iframe oculto; `uploadHttpData` faz **`eval("data = " + data)`** para respostas JSON |
| `simpleAutoComplete.js` | 4,3 KB | autocomplete via `$.get(page, {query})` inserindo resposta com `.html(r)` |
| `datatable-buttons.js` | 54 KB | DataTables Buttons (versão antiga, cabeçalho "DataTables 1.5.6") |
| `mascaras.js` / `masks.js` | 3–4 KB | máscaras (masks.js é o script Adobe `cfinput mask`, ©2012) |
| `cfform.js`, `cfajax.js`, `cfmessage.js`, `cftooltip.js`, `cflistfunctions.js` | — | scripts do ColdFusion (`/cf_scripts/scripts/ajax`), copyright Adobe 2007/2012 |
| `flexdropdown.js`, `jquery.paginate.js`, `highslide-full.js` | — | UI |

### 1.4 Bibliotecas de terceiros e versões (CONFIRMADO quanto às versões presentes)

| Biblioteca | Versões encontradas | Observação |
|---|---|---|
| jQuery | **1.3.2** (`jquery.min.js`), **1.4.2**, **1.11.0** (arquivo nomeado `jquery-1.9.1.js`), **3.6.0** | Até 4 gerações coexistem; telas antigas (PRINCIPAL, RAMAIS, REL-CONT, LOGIN) usam só as antigas |
| jQuery UI | CSS 1.10.2 e 1.13.1; JS 1.13.1; `jquery-ui-1.8.custom` no PRINCIPAL | |
| DataTables | 1.9.4 **e** 1.10.19 carregados na mesma página; Buttons "1.5.6" | |
| Bootstrap | 3.1.1 (MAPA/MAPA2/MAPA3, carregado de `/js/bootstrap/bootstrap-3.1.1/`) | |
| CKEditor / CKFinder | `ckeditor.js` (4.10.1 conforme baseline) e **`ckfinder.js` (v2)** carregados em 13 páginas, **sem uso observado no JS inline** | CKFinder é gerenciador de arquivos; a presença do conector server-side é **A VERIFICAR** |
| Highslide | 4.1.13 | |
| Chosen | 1.5.1 | |
| Inputmask | 5.0.8 | |
| maskMoney | 2.1.2 | |
| meio.mask | 1.1.3 | |
| multiple.select | 1.0.7 | |
| jQuery Paginate | 0.3.0 | |
| JSZip | 3.1.3 | |
| pdfmake | 0.1.53 | |
| MessageBox | 2.2.3 | |
| YUI 2 (`yahoo-dom-event`, `container-min`, `animation-min`) | empacotado pelo ColdFusion | |

---

## 2. Arquitetura observável

### 2.1 Plataforma (a partir das três páginas de erro e dos scripts CF)

| Componente | Evidência | Arquivo |
|---|---|---|
| Adobe ColdFusion, servidor de aplicação | `coldfusion.runtime.*`, `coldfusion.filter.*`, scripts em `/cf_scripts/scripts/ajax` (caminho usado a partir do CF 11), filtro `coldfusion.inspect.weinre.MobileDeviceDomInspectionFilter` (CF 11+) | PEDIDO.html, TABELA2.html, REL-NF2.htm, LOGIN.html |
| Java 11 | `java.base/java.lang.Thread.run(Thread.java:834)` (módulo `java.base` = JDK 9+; linha 834 típica do JDK 11) | idem |
| Tomcat 9 embutido, conector **AJP** | `org.apache.coyote.ajp.AjpProcessor.service(AjpProcessor.java:448)`, `org.apache.tomcat.util.threads.ThreadPoolExecutor` | idem |
| Indício de versão | Java 11 + Tomcat 9 + `/cf_scripts` → **ColdFusion 2018 ou 2021** (INDÍCIO; nível de patch **A VERIFICAR**) | — |
| SQL Server via driver "Macromedia SQLServer JDBC Driver" **6.0.0.1282** | stack `macromedia.jdbc.sqlserver.*` | REL-NF2.htm |
| Datasource | **`ASNOVO`** (chave `DataSource` do dump) | REL-NF2.htm |
| Banco/schema | comentário no JS: "Prestadores existentes no banco de dados `asnovo.pessoas.pessoa`" | MAPA3.html (JS linha ~416) |
| Raiz física da aplicação | `E:\sistemas\ASEng\` | 3 páginas de erro |
| Servidor web frontal | Não identificável (AJP indica IIS/Apache na frente do Tomcat) | — |

### 2.2 Estrutura de diretórios (módulos) observada

`logon/`, `cadastro/`, `contrato/` (+`contrato/cfcs/`), `servico/` (+`servico/cfcs/`), `suprimento/` (+`suprimento/cfcs/`), `suprimentos/` (printRequisicao.cfm), `suprimentoEquipamento/`, `pedido/` (+`pedido/cfcs/`), `gerencial/`, `financeiro/`, `mapaConcorrencia/` (+`cfcs/`), `sistemaArquivo/`, `veiculos/`, `extranet/`, `cfcs/` (global: `geral.cfc`), `js/`, `images/`, `cep.cfm` e `cep_municipio.cfm` na raiz.

### 2.3 Pipeline de requisição (CONFIRMADO pelas stack traces)

```
Requisição → Application.cfc :: onRequest()  (linha 942: <cfinclude> do template alvo)
           → template.cfm
               → linha 2: <cfinclude logon/_includeValidacao.cfm>
                    → linha 4: <cfinclude logon/_verificaPermissoesRotina.cfm>
                         → linha 30: lê a variável ID_ROTINA (sem escopo)
               → lógica da página / cfquery / CFC
Exceção não tratada → handler global que faz <cfdump> da exceção (tabela class="cfdump_struct")
```

Pontos que se confirmam pelas três páginas de erro:

1. **`Application.cfc` existe e centraliza o `onRequest`** (linha 942). É o local natural para autenticação, autorização, CSRF e tratamento de erro.
2. **A verificação de permissão por rotina é feita por include** (`logon/_includeValidacao.cfm` → `logon/_verificaPermissoesRotina.cfm`) e depende de **`ID_ROTINA`**: em `TABELA2.html` a página foi aberta sem `id_rotina` na URL e o erro foi "Variable ID_ROTINA is undefined" **na linha 30 de `_verificaPermissoesRotina.cfm`**. Ou seja, a rotina a ser checada vem da requisição (URL/FORM), não da página.
3. **Nem todas as páginas passam pela checagem de rotina**: `npedido_print.cfm` sem parâmetros falhou na **linha 4 do próprio template** por `ID_PEDIDO` indefinido (não por `ID_ROTINA`), e `gerencial_pedido_observacao.cfm?id_pedido=N` (REL-TIL.htm) renderizou normalmente sem `id_rotina`.
4. **O tratamento global de erro entrega o dump completo ao navegador** (ver SEC-002/SEC-028).

### 2.4 Padrão arquitetural (INDÍCIO FORTE, agora observado em 9 módulos)

```
Menu (indexLog.cfm)  ── links com ?id_rotina=N ──►  Página de rotina (ex.: medicoesMOLista.cfm)
      │                                                     │  $.ajax POST
      │                                                     ▼
      │                                     Fragmentos de leitura  (xxxLista2.cfm, xxxEdita.cfm, popupHistoricoX.cfm)
      │                                                     │  $.ajax POST / $.post
      │                                                     ▼
      │                                     Ações de escrita "_xxx.cfm"  (retornam código numérico: 0 ok, 1/-1/... erro)
      │                                     ou CFC direto:  cfcs/X.cfc?method=Y  /  {method:'Y', returnformat:'JSON'}
      │                                                     ▼
      │                                     DAO (*_DAO.cfc, *_DAO2.cfc) → cfquery → SQL Server (ASNOVO)
      └── relatórios/impressão: GET com IDs na query string (relatorio_*.cfm, *_print*.cfm, popup*.cfm)
```

Convenções observadas:

- Prefixo `_` = ação que grava; sufixo `2`/`New2` = fragmento de listagem paginada; `popupHistorico*` = trilha de histórico por objeto.
- Toda página traz o buscador de ramal global `../cfcs/geral.cfc?method=buscaRamal` (POST `pmenuNome`) e o popup `logon/principal_anexos.cfm?id_rotina=88`.
- Paginação/ordenação por `botao`, `clique`, `campo`, `ordem` (e `pbotao/pclique/pcampo/pordem`, `reqClique/reqCampo/reqOrdem`, `novoCampo/novaOrdem`). Comentário no JS de CONTRATOS-EMP2: *"passamos o clique com zero para não alterar a **session.inicio** senão fica somando"* → estado de paginação em `session`.
- Carrinho de requisição de materiais mantido em sessão (`cfcs/carrinho_requisicao_materiais.cfc?method=getLimpaCarro`).
- `_cf_clientid` e `_cf_ajaxproxytoken:''` nas páginas com `cfform`/`cfselect` bind (CONTRATO.html): o mecanismo de token do CF Ajax **não está em uso** (token vazio).

### 2.5 Autenticação e sessão (o que é observável)

| Aspecto | Observado | Classificação |
|---|---|---|
| Login | `POST /logon/login.cfm` com `login` (e-mail `@almeidasapata.com.br`) e `senha`; validação client-side apenas de obrigatoriedade (`_CF_checkformlogin`) | CONFIRMADO |
| "Esqueceu a senha" | `GET _enviarSenha.cfm?login=<e-mail>` **sem autenticação**; retorno `1` = "O e-mail informado não existe no sistema", `0` = "A senha foi enviada com sucesso" | CONFIRMADO (ver SEC-029) |
| Logout | link `GET /logon/logout.cfm` | CONFIRMADO |
| Troca de senha | `logon/senhasEdita.cfm?id_rotina=4` (tela não fornecida) | — |
| Cookies de sessão | Não observáveis (sem cabeçalhos). Nenhum `CFID/CFTOKEN/JSESSIONID` aparece em URLs (bom sinal: sem sessão na URL) | A VERIFICAR |
| Renovação de sessão no login | `_cf_clientid='C3912D25...A7DB'` é **idêntico** em LOGIN.html (pré-autenticação) e em CONTRATO.html / CONTRATOS-EMP2.html (autenticadas) | INDÍCIO (ver SEC-034) |
| Expiração / timeout | Nenhum mecanismo client-side observado | A VERIFICAR |
| Perfis | Menu com 46 rotinas (ver 3); botões condicionais renderizados no servidor; **flags de papel também enviadas pelo cliente** (`responsavel`, `coordenador`, `tipo`, `idSituacaoLogado`) | ver SEC-030 |

---

## 3. Mapa de módulos (rotinas do menu principal)

Fonte: `PRINCIPAL.html` (`logon/indexLog.cfm`). "Amostra" indica se há página do módulo nos lotes.

| id_rotina | Página | Módulo | Amostra |
|---|---|---|---|
| 4 | logon/senhasEdita.cfm | Segurança → Alterar senha | não (só `SENHA_files`) |
| 27 | suprimento/requisicoes_lista.cfm | Suprimentos → Requisições | não |
| 31 | pedido/relatorio_material.cfm | Pedidos → Relatório de materiais | **sim** (MATERIAIS) |
| 38 | servico/contratosLista.cfm | Contratos de serviço | **sim** (NOVO-CONTRATO, CONTRATOS-EMP1/2, ANEXO1) |
| 41 | servico/medicoesMOLista.cfm | Medições de serviço (MO) | **sim** (MEDIÇÕES1/2) |
| 42 | servico/relContSeleciona.cfm | Relatório de contrato | **sim** (REL-CONT, REL-CONT2) |
| 55 | servico/relTabelaSeleciona.cfm | Relatório tabela | **sim** (TABELA, TABELA2) |
| 59 | servico/relCentroCusto.cfm | Relatório centro de custo | não |
| 60 | pedido/pedidoAprovar.cfm | Aprovação de pedidos | não |
| 70 | contrato/contrato_pesquisar_obras_coordenacao.cfm | Obras / medições de clientes (coordenação) | **sim** (CLIENTE MEDIÇÕES, CONTRATO) |
| 78 | contrato/contrato_pesquisar.cfm | Contratos comerciais | **sim** (CONTRATOS2) |
| 82 | contrato/contrato_medicao_faturamento.cfm | Faturamento de medição (referenciado no JS) | não |
| 88 | logon/principal_anexos.cfm | Sistema de arquivos (popup) | não |
| 89, 90, 93, 145, 146 | veiculos/* | Veículos | não |
| 95, 96, 172 | gerencial/* | Gerencial (lista obras, despesas, transparência) | **sim** (DESPESA, DESPESA2, REL-TIL) |
| 97, 120 | contrato/relatorio_gerencial_medicao.cfm, relatorio_obras_previsto_realizado.cfm | Relatórios gerenciais | não |
| 98 | financeiro/relatorioFaturamento.cfm | Financeiro | não (mas `titulosPagarVer.cfm` em REL-NF/REL-NF2) |
| 105 | servico/relatorio_contrato_fornecedor.cfm | Relatório de pagamentos a prestadores | **sim** (REL-PAGTO) |
| 109 | cadastro/relatorio_nextel.cfm | Ramais/Nextel | **sim** (RAMAIS) |
| 113, 114, 118, 134 | sistemaArquivo/* | Arquivo (caixas, documentos, requisições) | não |
| 122, 123, 142, 143 | suprimento/*almoxarifado* | Almoxarifado | não |
| 126, 128, 129 | cadastro/nprestadores_listar.cfm, nrel_prestador.cfm, nrel_fornecedor.cfm | Cadastros | não |
| 152 | extranet/mensagem_listar.cfm | Extranet | não |
| 153 | suprimento/req_materiais_listar.cfm | Requisição de materiais | **sim** (RMS1, RMS2) |
| 161 | suprimento/romaneio_NF.cfm | Remessa de notas fiscais | **sim** (REMESSA) |
| 168 | suprimentoEquipamento/neqp_requisicao.cfm | Equipamentos | não |
| 171 | servico/medicao_retprestador_listar.cfm | Retenção de prestador | não |
| 179 | mapaConcorrencia/smapa_listar.cfm | Mapa de concorrência | **sim** (NOVO-MAPA, MAPA, MAPA2, MAPA3) |

---

## 4. Mapa de superfície (módulo → página → função JS → endpoint → método → parâmetros → operação)

Legenda de origem dos parâmetros: **[u]** digitado pelo usuário; **[h]** campo hidden/atributo renderizado pelo servidor e devolvido pelo cliente; **[js]** constante no JavaScript; **[f]** formulário serializado inteiro.

### 4.1 Autenticação (logon/)

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| submit `formlogin` | `logon/login.cfm` | POST | `login`[u], `senha`[u] | autenticação |
| `lembrarSenha()` | `logon/_enviarSenha.cfm` | **GET** | `login`[u] | envia senha por e-mail (sem sessão) |
| link menu | `logon/logout.cfm` | GET | — | encerra sessão |
| `abrirSistemaArquivos()` | `logon/principal_anexos.cfm?id_rotina=88` | GET | `id_rotina`[js] | popup do sistema de arquivos |
| `menuPequisaRamal()` (todas as telas) | `cfcs/geral.cfc?method=buscaRamal` | POST | `pmenuNome`[u] | busca ramal; resposta em `.html()` |

### 4.2 Medições de serviço (servico/, rotina 41) — MEDIÇÕES1/MEDIÇÕES2

| Função JS | Endpoint | Método | Parâmetros | Operação / dado |
|---|---|---|---|---|
| `pesquisar()`, `mostrar()`, `ordenando()`, `pesquisarReprovadosPendentes()` | `medicoesMOLista2.cfm` | POST | `formPesquisa`[f]: `Botao, Ordem, clique, campo, id_rotina, contratoID, obrasID, prestadorID, num_contrato, nome_obra, prestador, situacaoID, statusID` | lista de medições (consulta) |
| autocomplete | `cfcs/servico.cfc?method=getAutosuggestContratos / getAutosuggestObrasEng / getAutosuggestPrestadores&returnformat=JSON&queryformat=column` | GET | `term` (jQuery UI) | consulta |
| `editarMedicao(id_medicao,id_contrato,id_aditivo,id_rotina)` | `medicoesMOEdita.cfm` | POST | `id_medicao, id_contrato, id_aditivo, id_rotina`[h] | carrega edição |
| `carregarListaMedicoes()` | `medicaoMOEditaServicos.cfm` | POST | `id_contrato, id_aditivo, id_medicao, id_rotina`[h] | itens da medição |
| `carregarObservacao()` / `carregarResumaoValores()` / `carregarReprovacao()` | `medicaoMOEditaObservacao.cfm` / `medicaoMOEditaRodapeValores.cfm` / `medicaoMOEditaRodapeReprovacao.cfm` | POST | `id_contrato, id_aditivo, id_medicao`[h] | fragmentos |
| `validandoDadosServicoMedicao(id)` | **`_medicoesEdita.cfm`** | POST | `quantidade`[h], `qtdAcu`[h], `porcentAtual`[h], `id_material`[h], `acumuladoMedido`[h], `quantMed`[u], `quantContrato`[h], `preco`[h], `quantidadeAcumulada2`[h], `vlContrato`[h], `id_medicao, id_aditivo, id_contrato`[h], `id_centroCusto`[u], `id_medicaott`[h], `med_obs_memo`[u] | **grava item medido** (retornos 0/1/2/3) |
| `atualizarValoreRodape()` | **`cfcs/medicao_DAO.cfc?method=atualizarValoresRodape`** | POST | `formMedicaoAprovar`[f]: `id_contrato, id_aditivo, id_medicao, responsavel`[h], `vDesconto`[u], `retencaoZero`[h], `retencao`[u], `valorNotaFiscal`[h], `totalPagar`[h], `vsaldoContrato`[h] | recalcula rodapé (sem retorno) |
| `aprovacaoUltimaMedicao()` / `aprovarMedicaoEdicao()` | **`_medicoesAprova.cfm`** | POST | idem `formMedicaoAprovar`[f] | aprova (retorno -1 sem centro de custo; 0 ok) |
| `avaliarPrestador()` | `medicao_avalia_percentual.cfm` | POST | `id_contrato, id_medicao`[h], `id_responsavel`[h `responsavel`] | decide se abre avaliação |
| idem | `medicaoMOAvaliacaoPrestador.cfm` | POST | `formMedicaoAprovar`[f] | formulário de notas |
| dialog Confirmar | **`_medicoes_prestador_avaliar.cfm`** | POST | `frmNotas`[f] (notas `.selecao`, ids) | grava avaliação (0 / -1 / 23000 duplicada) |
| `abrirPontos()` / `verDetalhe()` | `../cadastro/pontuacoes_prestador.cfm` / `pontuacoes_prestador_nota.cfm` | POST | `id_prestador` / `id_apuracao` | consulta |
| `baixarMedicao()` | **`_medicoesBaixa.cfm`** | POST | `formBaixaMedicao`[f] (não presente no snapshot; inclui `vNumNF`, `vDataNF`, `totalPagar`) | baixa (retorno -1 sem centro de custo) |
| `medicaoExcluirEdicao()` | **`_medicoesExclui.cfm`** | POST | `formExcluirMedicao`[f] | exclui medição (resposta ignorada) |
| `medicaoReprovarEdicao()` | **`_medicoesReprova.cfm`** | POST | `formReprovaMedicao`[f] (`obs_reprovar`[u]) | reprova (resposta ignorada) |
| `editarObsMedicao()` | **`_medicaoEditaObs.cfm`** | POST | `editaObs`[f] | grava observação (resposta ignorada) |
| `alterarPeriodoMedicao()` | **`_medicao_periodo_editar.cfm`** | POST | `id_contrato, id_aditivo, id_medicao`[h], `inicio, fim`[u] | altera período (1/-1/-2/-3/-4/-6) |
| `mostrarHistorico()` | `popuphistoricomedicao.cfm` | POST | `id_contrato, id_aditivo, id_medicao` | histórico |
| onclick (server-rendered) | `anexoMemoMedicaoServicos.cfm?id_rotina=41&id_contrato=N&id_servico=N&id_aditivo=N&id_medicao=N&flag_edicao=0` | GET | IDs na URL | popup anexos por serviço |
| onclick | `anexoMemoriaCalculoMed1.cfm?id_rotina=41&id_contrato=N&idSituacao=N&idStatus=N&id_aditivo=N&id_medicao=N` | GET | IDs + status na URL | popup anexos da medição |
| onclick | `relatorio_contrato_rel04.cfm?contrato=N&id_rotina=41&id_contrato=N&idSituacao=3&idStatus=2&id_aditivo=0&id_medicao=N&financeiro=1&id_obra=...` | GET | IDs + flags na URL | relatório da medição |
| botão Nova | `medicoesMONovo.cfm?id_rotina=41` | GET | — | nova medição (tela não fornecida) |

Campos hidden **por item** confirmados em MEDIÇÕES2 (6 itens): `item`, `id_medicaott`, `quantidade`, `preco` (ex. `75.0000`), `qtdAcu`, `qtdMedidaAnterior`, `porcentAtual`, `id_material`, `acumuladoMedido`, `quantContrato`, `quantidadeAcumulada2`; global: `vlContrato=2543.0816`, `responsavel=0`, `valorNotaFiscal=63.5408`, `totalPagar=1271.5408`, `vsaldoContrato=0`, `retencaoZero=0`.

### 4.3 Contratos de serviço (servico/, rotina 38) — NOVO-CONTRATO, CONTRATOS-EMP1/2, ANEXO1

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `finalizarCadastro()` | **`_contratosIncluir.cfm`** | POST | `formContratoIncluir`[f]: `id_contrato`[h], `id_rotina`[h], `id_obra`[u], `id_prestador`[u], `dataInicio`, `dataTermino`, `data_contrato`[u], `vAdiantamento`[u], `vretencao`[u], `vValorNF`[u/js via CFC], `observacao`[u] | cria contrato (1 duplicado, 2 erro, 0 ok) |
| `dadosPrestador()` | `contrato_dados_prestador.cfm` | POST | `id_pessoa, id_obra` | consulta |
| `temImposto()` | `cfcs/contrato.cfc` | POST | `method=getImpostoPrestador, id_pessoa, returnformat=JSON` | consulta → preenche `vValorNF` |
| `mostrarMensagemPrevistos()` | `../contrato/cfcs/medicoes.cfc?method=getLancamentosPrevistos` | POST | `id_obra` | consulta |
| `pesquisar()`, `mostrar()`, `pesquisarAbertura()`, `pesquisarReprovadosPendentes()` | `contratosListaNew2.cfm` | POST | `formPesqServ`[f]: `id_rotina, botao, clique, campo, ordem, frente, idObra, idPrestador, idSituacao, idStatus, idContrato` | lista |
| `gerenciarServicos(id_contrato,id_aditivo,frente,destino)` | **`destino` dinâmico** (`servicosIncluiNew.cfm`, `servicosIncluiAditivo.cfm`, `contratoFormularioV2.cfm`…) | POST | `id_contrato, id_aditivo, id_rotina, frente, clique, ordem, campo` | abre subtela (URL vinda do HTML) |
| `altImposto()` | **`_contratoAlteraImposto.cfm`** | POST | `id_contrato, id_aditivo, valorNF`[u], `id_rotina, ajax=1, id_prestador, id_obra, id_situacao`[h] | altera imposto (-1/0) |
| `alterarDadosContrato()` | **`_contratoEditar.cfm`** | POST | `id_contrato, id_aditivo, vinicio, vtermino, id_obra, vid_prestador, id_situacao, returnformat=JSON` | altera contrato (1 datas, 2 obrigatórias, -4 títulos baixados, 0 ok) |
| `aprovarContrato()` / `diretoriaAprovarContrato()` | **`_contratoAprova.cfm`** | POST | `id_contrato, id_aditivo, id_rotina, ajax=1` (+ `campo` 0/1 = altera lista de preço) | aprova (-1 sem serviços) |
| `aprovarContratoAditivo()` / `diretoriaAprovarContratoAditivo()` | **`_contratoAprovaAditivo.cfm`** | POST | idem | aprova aditivo (-7 sem alteração de valor) |
| `salvarObservacaoContrato()` | **`_contratoEditaObs.cfm`** | POST | `observacao`[u] + ids | grava obs (resposta ignorada) |
| `reprovaContrato()` | **`_contratoReprova.cfm`** | POST | `obs`[u] + ids | reprova (resposta ignorada) |
| `reprovandoContratoAditivo()` | **`_contratoReprovaAditivo.cfm`** | **GET** | `reprovaServicos`[f] + `id_contrato, id_aditivo, reprova, ajax=1, id_rotina` | reprova aditivo |
| `cancelarContrato()` | **`_contratoCancela.cfm`** | POST | `id_contrato, id_rotina, doIncluir=1, ajax=1, id_aditivo` | cancela (1 bloqueado por adiantamento/medição) |
| `excluiContrato()` | **`_contratoExclui.cfm`** | POST | idem | exclui contrato e serviços |
| `salvarRetencaoEdicaoContrato()` | **`_contratoRetencaoEditar.cfm`** | POST | `novaRetencao`[u] + ids | altera retenção (resposta ignorada) |
| `anexaContrato()` / `anexaContratoArquivo()` | **`_anexaContrato.cfm`** | POST multipart (iframe) | `anexo`[arquivo], `id_contrato, id_aditivo, ajax=1, id_rotina` | upload |
| `listarAnexos()` | `contratoAnexos.cfm` | POST | ids + `id_maxAditivo` | lista anexos |
| `apagarArquivo()` | **`_contratoAnexoApagar.cfm`** | POST | `id_anexo, id_contrato, id_aditivo` | apaga anexo |
| `mostrarServicos()` | `servicosIncluiNew2.cfm` | POST | `id_contrato`[js constante], `id_rotina`, `id_aditivo` | lista serviços |
| `adicionarServico()` | **`_servicosEdita.cfm`** | POST | `valor`[u], `quantidade`[u], `observacao`, `inicio`, `termino`, `ajax=1, id_contrato, id_aditivo, id_material` | insere serviço com preço |
| `editarServico()` | **`_servicosQtdEdita.cfm`** | POST | `quantidade, inicio, termino, observacao` + ids | altera serviço |
| `excluirServico()` | `servicoIncluirAditivoVerMedicao.cfm` → **`_servicosExclui.cfm`** | POST | ids (`id_servico, id_material`) | verifica medido (1) e exclui |
| `pequisarServicos()` / `mostrarPesquisa()` | `contratoServicoPesquisa.cfm` | POST | `formPesquisaServico`[f] (`id_material` inteiro, `id_familia`, `pbotao/pclique/pcampo/pordem`) + `frente` | pesquisa de materiais |
| `mostrarTotais()` | `cfcs/servicosIncluiNew.cfc?method=getTotaisServicos` | POST | `id_contrato, id_aditivo` | totais |
| `mostrarHistorico()` | `popuphistoricocontrato.cfm` | POST | ids | histórico |
| `getFormulario()` | `contratoFormularioV2.cfm` | POST | `FLAG_TIPOF, id_rotina, id_contrato, id_aditivo, id_obra` | formulário |
| `abre_pop()` | `contratosServicosPopup.cfm` | GET | — | popup |
| onclick | `anexoMemoriaCalculo.cfm?id_rotina=38&id_contrato=N&id_aditivo=N&id_material=N` | GET | IDs | popup anexos (ANEXO1) |
| `uploadArquivo()` (ANEXO1) | **`_anexo_memoria_servico.cfm`** | POST multipart | `anexo`, `id_contrato, id_aditivo, id_material`[h] | upload memória de cálculo (`data.STATUS/MESSAGE`) |
| `excluirMemoria()` (ANEXO1) | **`_anexoMemoriaCalculoApagar.cfm`** | POST | `id_memoria, id_contrato, returnformat=JSON` | apaga anexo |
| form | `relatorio_contrato_servico.cfm` | POST (`_blank`) | — | relatório |

### 4.4 Relatórios de serviço (rotinas 42, 55, 105) — REL-CONT, REL-CONT2, TABELA, REL-PAGTO

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `validarContrato()` | `relContSeleciona1.cfm` | POST (`target=_new`) | `id_obra, id_contrato, id_aditivo, rel`(radio 1..4), `id_rotina=42` | gera relatório |
| link | `relatorio_contrato_rel01.cfm?id_rotina=96&contrato=&id_obra=N&id_contrato=N&id_aditivo=0&id_medicao=` | GET | IDs | extrato do contrato |
| link | `relatorio_contrato_rel04.cfm?id_rotina=42&...&id_medicao=1` | GET | IDs | relatório medição |
| link | `relatorio_tabela_rel01.cfm?id_rotina=55&id_obra=&id_contrato=&id_aditivo=&id_medicao=` | GET | IDs | relatório tabela |
| `pesquisar()` | `relatorio/relatorioPagamentosListagem.cfm` | POST | `formPesquisa`[f]: `id_rotina=105, botao, clique, campo, ordem, pessoaID, obraID, contratoID, num_contrato, datas` | listagem |
| `mostrar()` | `relatorio_contrato_fornecedor2.cfm` | POST | idem | paginação |
| DataTables server-side | `relatorio/relatorioPagamentos_ajax.cfm` | POST | `iDisplayStart, iDisplayLength, iSortCol_0, sSortDir_0, sSearch, ... , vobra, id_rotina, idPessoa, idContrato, dataContrato1/2, dataNF1/2` | dados JSON |
| `selecionarPessoaID()` | `cfcs/financeiro.cfc` | POST | `method=selecionarIDPessoa, fornecedorID, returnformat=JSON` | consulta |
| autocomplete | `../servico/cfcs/servico.cfc?method=getAutosuggestContratos` | GET | `term` | consulta |

### 4.5 Contratos comerciais, obras e medições de clientes (contrato/, rotinas 70 e 78) — CLIENTE MEDIÇÕES, CONTRATO, CONTRATOS2

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `listarObras()` / `mostrar()` | `contrato_pesquisar_obras_coordenacao2.cfm` | POST | `id_rotina=70, idObras, nomeObra, cliente, clienteID, situacaoID, statusID, numContrato, contratoID, esconder, botao, clique, campo, ordem, returnformat=PLAIN` | lista obras |
| autocomplete / cfselect bind | `cfcs/contrato.cfc` métodos `pegarObras`, `pegarContratos`, `pegarAutoSuggestClientes` (GET JSON) e `pegarClientes`, `pegarTipoContrato`, `selEmpresas` (bind CF Ajax, `_cf_ajaxproxytoken` vazio) | GET/POST | `term` | consulta |
| `mostrarTermosCoordenacao()` | `contrato_obras_termos.cfm` | POST | `id_obra, id_contrato, coordenador`[h `ncoordenador`], `id_AditivoAtual, id_statusObra` | termo provisório |
| `paralisarObra()` / `desparalisarObra()` | `contrato_obras_paralisa.cfm` / `contrato_obras_paralisada_ativar.cfm` | POST | `id_obra, id_aditivoAtual` | formulário |
| `confirmarParalisacao()` / `confirmarDesparalisacao()` | **`_contrato_obras_paralisar.cfm`** | POST | `formParada`[f] (`par_obs, par_datap, pdata_final`) + `paralisar=1` | muda status da obra |
| `vamosEditarObra()` | `contrato_obras_coordenacao_editar.cfm` | POST | `id_coordenador`[h], `id_rotina, id_contrato, id_obra, id_aditivo, pag_volta`[h], `clique, ordem` | formulário de obra |
| `editarObra()` | **`_contrato_obras_editar.cfm`** | POST | `formEditaObra`[f]: `id_contrato, id_obra, id_aditivo, id_statusObra, id_situacaoObra, id_empresa, id_coordenador, id_encarregado, lstEngenheiros`(lista de IDs)[h], `num_os, inicio_os, termino_os, valor_os, nome_fiscal, fone_fiscal, endereços, codigo_iss, codigo_cno`[u] | altera obra (8 datas, -2 soma OS > contrato, 0 ok) |
| `aprovarObraParaMedicao()` | **`_contrato_obras_coordenacao_aprova.cfm`** | POST | idem | aprova obra (resposta ignorada) |
| `reativarFinalizada()` | **`_contrato_obras_coordenacao_reativar.cfm`** | POST | `id_obra, id_contrato` | reativa obra (1 contrato finalizado) |
| change `flag_esconder` | **`cfcs/contratoObras.cfc`** | **GET** (default) | `method=setExecucaoObra, esconder, id_obra, descricao`[js] | marca obra em execução |
| `Nextel()` | `contrato_obras_nextel.cfm` | POST | `id_encarregado` | consulta |
| `getEnderecoObra()` / `getEnderecoEntrega()` | `../cep.cfm`, `../cep_municipio.cfm` | POST | `cep`, `nomeMunicipio` | consulta |
| `listarTudo()` | `contrato_ativo_dados.cfm`, `contrato_art_lista.cfm`, `contrato_modalidades_lista.cfm`, `contrato_seguros_lista.cfm`, `contrato_andamentos_lista.cfm`, `contrato_documentos_lista.cfm`, `contrato_guias_lista.cfm`, `contrato_recebimentos_lista.cfm`, `contrato_certidoes_lista.cfm` | POST | `id_contrato, id_aditivoContrato, id_rotina` | abas do contrato |
| `abrirMedicoes()` / `retornarPrevisto()` / `voltarMedicoes()` | `nmedicoes_lancamentos.cfm` | POST | `id_contrato, id_obra, id_aditivo, id_aditivoAtual, id_rotina` | gestão de medições do cliente |
| `dadosContratoNew()`, `getMenuRealizados()`, `getRelatorio()`, `getPrevistos()` | `nmedicoes_dados_obra_contrato.cfm`, `nmedicoes_lancamentos_menu_realizado.cfm`, `nmedicoes_lancamentos_relatorio.cfm`, `nmedicoes_lancamentos_previstos.cfm` | POST | `vid_contrato, vid_obra, vid_aditivo`[h] / `vformMedicao`[f] | fragmentos |
| `imprimirRelatorio()` | `nmedicoes_lancamentos_relatorio.cfm?vid_contrato=N&vid_obra=N&vid_aditivo=N&printer=1` | GET | IDs | impressão |
| `lancarNovosPrevistos()` | `nmedicoes_lancamentos_previstos_cadastrar.cfm` | POST | ids + `coordenador`[h `vcoordenador`], `id_coordenador`[h] | formulário |
| `salvarPrevisto()` / `salvarPrevistoCoord()` | `nmedicoes_valida_datas.cfm` → **`_nmedicoes_previsto_edita.cfm`** | POST | `id_med, inicial, fim, valor`[u], `id_obra, id_aditivo, edicao=1` (+ `status, situacao, tipo, coordenador=1`) | valida (1/2/6) e grava previsto |
| `salvarPrevisto()` (bloco alternativo) | `_contrato_medicoes_valida_datas.cfm` | POST | idem | validação |
| `cancelaPrevisto()` / `cancelaPrevistoCoord()` | **`_contrato_medicoes_previsto_cancela.cfm`** | POST | `id_med` (+ `coordenador=1, tipo`) | cancela previsto |
| `aprovarMedicaoPrevisto()` / `...Encarregado()` / `...Coordenador()` | **`_contrato_medicoes_previsto_aprova.cfm`** | POST | `idContrato, idObra, idAditivo` + **`coordenador=2`** (engenheiro) ou **`coordenador=1`** (coordenador) | aprova previstos |
| `reprovando()` | **`_contrato_medicoes_reprova.cfm`** | POST | `IdContrato, idObra, idAditivo, previsao=1, tipo`[h `tipo4`], `obs`[u] | reprova previstos |
| `vamosRealizado()` | `nmedicoes_lancamentos_realizados.cfm` | POST | `id_med, id_medicao, id_obra, id_aditivo, vcoordenador`[h], `id_rotina` | realizado |
| `salvarPrevistoRealizado()` / `salvarPrevistoRealizadoCoord()` | **`_nmedicoes_realizadas_inclui.cfm`** | POST | `id_med, id_obra, inicial, fim, valor`[u], `reajuste`[u] (+ `tipo, coordenador=1`) | insere realizado (-4 soma > OS) |
| `aprovarMedicaoPrevistoRealizado()` | **`_contrato_medicoes_previsto_realizadas_aprovar.cfm`** | POST | idem | insere com status "engenharia aprovado" |
| `salvarRealizado()` / `aprovarRealizado()` / `salvarRealizadoCoord()` | **`_nmedicoes_realizadas_edita.cfm`** | POST | `id_medRel, inicial, fim, valor, reajuste` (+ `tipo, coordenador=1`) | altera realizado |
| `aprovarMedicaoRealizada()` | **`_contrato_medicoes_realizadas_aprova.cfm`** | POST | `id_medRel` | aprova realizado |
| `cancelaRealizado()` / `cancelaRealizadoCoord()` | **`_contrato_medicoes_realizadas_cancela.cfm`** | POST | `id_medRel, tipo` | cancela realizado |
| `reprovandoRealizado()` | **`_contrato_medicoes_realizadas_reprova.cfm`** | POST | `id_medRel, previsao=1, tipo`[h `tipo3`], `obs`[u] | reprova realizado |
| `medicaoFaturar()` | `cfcs/medicoes.cfc` | POST | `method=medicaoPlanilha, id_medRel, returnformat=JSON` | verifica planilha anexada |
| `enviarMedicaoFaturamento()` | **`_nmedicoes_realizadas_fatura.cfm`** | POST | `id_med, id_medRel, obs, inicio, fim, valor, reajuste, id_contrato` | envia para faturamento (2 = sem planilha) |
| `faturarPrevistoRealizadoCR()` | **`_nmedicoes_realizadas_inclui_e_fatura.cfm`** | POST | `id_meds, id_med, id_obra, id_contrato, inicial, fim, valor, reajuste, flag_faturamento=1` | insere e fatura → redireciona `contrato_medicao_faturamento.cfm?id_medRel=N&id_rotina=82&doRealizado=1` |
| `desfazerRealizadoZeradoCR()` | **`cfcs/medicoes.cfc?method=desfazerRealizadoFaturadoZerado`** | POST | `id_medRel, id_contrato` | desfaz faturamento |
| `alterarProcesso()` | **`_nmedicoes_alterar_processo.cfm`** | POST | `id_med, processo`[u] | altera número de processo |
| `abrirHistorico()` | `popupHistoricoRealizada.cfm` | POST | `id_medRel, previsto, novoLayout=1` | histórico |
| `verAnexos()` | `nmedicoes_lancamentos_anexos.cfm` | POST | `id_obra, obra, id_contrato, id_medicao, id_aditivo, id_aditivoAtual, statusObra` | anexos |
| `saldosEmpenhos()` | `contrato_empenhos_faturas.cfm?id_contrato=N` | GET | id | popup |
| onclick (server) | `popupHistoricoObra.cfm?id_Obra=N&idAditivo=N`, `relatorio_dados_obra.cfm?id_obra=N`, `anexoContratoALL.cfm?id_rotina=70&id_contrato=N&obra=1&idObra=N&ID_ADITIVOCONTRATO=N` | GET | IDs | popups |
| CONTRATOS2 `pesquisar()` / `mostrar()` | `contrato_pesquisar_comercial2.cfm` | POST | `num_contrato, contratoID, cliente, clienteID, situacaoID, statusID, obrasID, id_rotina=78, botao, clique, campo, ordem` | lista |
| `aditarContrato()`, `abrirDialog()`, `abrirAtas()`, `gestaoEmpenhosContratos()` | `contrato_aditivo.cfm` (`tipo=1`), `contrato_view_usuarios.cfm`, `contrato_atas.cfm`, `contrato_empenhos.cfm` | POST | `id_contrato, id_aditivo` | fragmentos |
| `cancelarContrato()` | **`_contrato_cancelar.cfm`** | POST | `id_contrato, id_aditivo, id_rotina, returnformat=json` | cancela (9 em edição, 0 ok) |
| form `formPrintContrato` | `relatorio_requisitos_contratuais.cfm` | POST (`_blank`) | ids | relatório |
| onclick | `popupHistoricoContrato.cfm?id_contrato=N&id_aditivo=N`, `anexoContratoALL.cfm?id_contrato=N&ID_ADITIVOCONTRATO=0&id_rotina=78&id_aditivo=0` | GET | IDs | popups |

### 4.6 Mapa de concorrência (mapaConcorrencia/, rotina 179) — NOVO-MAPA, MAPA, MAPA2, MAPA3

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `pesquisar()` / `pesquisarDaAbertura()` | `smapa_listar2.cfm` | POST | `frmMapas`[f] (`vid_mapa, pidObra/cidObra, vfases, vsituacao, vstatus, frente, id_rotina`) | lista mapas |
| `preencherStatus()` | `cfcs/mapaConcorrenciaF1.cfc` | GET JSON | `method=getBindStatus, vfases` | consulta |
| `adicionarRequisicao()` / `cadastrar()` | `smapa_cadastrar.cfm` → **`_smapa_cadastrar.cfm`** | POST | `formCadastro`[f] (`cadid_requisicao, cadid_aditivo, flag_cadastrar=1, obs, obra…`) | cria mapa |
| `abrirMapaFase2()` / `abrirMapaFase3()` / `carregarMapa()` | `smapa_fase2_editar.cfm`, `smapa_fase3_editar.cfm`, `smapa_fases_itens.cfm` | POST | `id_requisicao, id_aditivo, id_rotina` | fases |
| `verHistorico()`, `verAnexosRequisicao()`, `verAnexosObras()` | `smapa_historico.cfm`, `smapa_anexos.cfm`, `smapa_anexos_obra.cfm` | POST | ids | consulta |
| `excluirRequisicaoListagem()` | **`_smapa_excluir.cfm`** | POST | `id_requisicao, id_aditivo, id_rotina` | exclui mapa |
| `editaInicioRequisicao()` / `editaFimRequisicao()` / `editaObraRequisicao()` / `alterarObsRequisicao()` | **`cfcs/mapaConcorrenciaF1.cfc`** | POST | `method=validaEdicaoInicioRequisicao\|validaEdicaoFimRequisicao\|alteraObraRequisicao\|alteraObsRequisicao`, `id_requisicao, inicio\|fim\|idObra\|obs` | altera mapa |
| `mostrarClienteObra()` / `mostrarIconeObra()` / `atualizandoTotalPC()` | `cfcs/MapaConcorrenciaF1.cfc` | POST | `method=getClienteObra\|getIconeAnexoObra\|getCalculoTotalPC` | consulta |
| `addPrestadores()` / `addPrestadorMapa()` | `smapa_fase2_getprestadores.cfm` → **`cfcs/mapaConcorrenciaF2.cfc`** | POST | `method=adicionarPrestadoresMapa, id_familia, flag_topContrato, id_requisicao, id_aditivo, id_prestador, nomePrestador, imposto`, **`idSituacaoLogado=8`[js]** | inclui prestador no mapa (`data.ERRO/MESSAGE` → `.html()`) |
| `delPrestadorMapa()` | **`cfcs/MapaConcorrenciaF2.cfc`** | POST | `method=excluirPrestadorMapa, ... , idSituacaoLogado=8`[js] | remove prestador |
| `salvarNovoPrestador()` | `cfcs/mapaConcorrenciaF2.cfc` (`method=existePrestador, cnpj`) → **`_smapa_fase2_prestador_cadastrar.cfm`** | POST | formulário do prestador[f] | cadastra prestador |
| `cadastrarPrestador()` / `abrePrestador()` | `smapa_fase2_prestador_cadastrar.cfm` | POST | ids | formulário |
| `aprovarPrestador()` / `reprovarPrestador()` | **`_prestador_aprovar.cfm`** / **`cfcs/prestadoresDAO.cfc method=reprovarCadastroPrestador`** | POST | `id_prestador, id_rotina` | aprova/reprova cadastro |
| `adicionarMaterial()` / `cadastrarNovoMaterial()` | `smapa_materiais_adicionar.cfm`, `smapa_material_cadastrar.cfm` | POST | ids, `id_servico` | formulários |
| `aprovarNovoServico()` | **`_smapa_servico_aprovar.cfm`** | POST | `unidade, familia, servico, inicio, fim, obs, qtd, pc`[u], `id_servico, id_requisicao, id_aditivo, id_mri, id_rotina` | aprova serviço novo com preço |
| `reprovarNovoServico()` | **`cfcs/mapaConcorrenciaServicos.cfc method=reprovarServico`** | POST | ids | reprova |
| `apagarTodosMateriais()` / `excluirServico()` | **`_smapa_delete_material_full.cfm`** / **`_smapa_delete_material.cfm`** | POST | ids | exclui itens |
| `editarItem()` | **`_smapa_edit_material.cfm`** | POST | `id_mri, id_requisicao, id_aditivo, inicio, fim, qtd, obs, id_rotina, mri_pc`[u] | altera item (inclui preço PC) |
| `cancelarRequisicaoF2()` / `reprovarRequisicaoF2()` / `reprovarCotacaoF3()` | `smapa_fase2_dialog_acoes.cfm` (`funcao=`) → **`cfcs/mapaConcorrenciaF2.cfc method=cancelarRequisicaoF2\|reprovarRequisicaoF2`**, **`cfcs/mapaConcorrenciaCotacao.cfc method=reprovarCotacao`** | POST | ids, `obs` | muda status |
| `aprovarRequisicaoF3()` / `aprovandoRequisicaoF3()` | **`_smapa_fase3_aprovar_validar.cfm`** → **`_smapa_fase3_aprovar.cfm`** | POST | ids, `obs` | aprova fase 3 |
| `gerarContrato()` / `gerarandoContrato()` | **`_smapa_fase3_gerar_contrato.cfm`** | POST | ids, `obs`, `listaPrecos` (JS envia sempre 0) | **gera contratos de serviço** a partir do mapa |
| `enviarEmail()` / `enviarEmailTodosPrestadores()` | `smapa_fase2_prestador_envio_email.cfm`, `smapa_mail_todos.cfm` → **`_smapa_fase2_prestadores_email_send.cfm`**, **`_smapa_email_todos_send.cfm`** | POST | formulário de e-mail[f] | envia e-mails a prestadores |
| `desistir()` / `reintegrar()` | **`_smapa_prestador_declinar.cfm`** / **`_smapa_prestador_reintegrar.cfm`** | POST | `id_smp, id_mrequisicao, motivo, id_aditivo, id_rotina, prestador` | status do prestador no mapa |
| `selecionarPrestadoresItens()` / `selecionarTodosOsItensDoPrestador()` | **`cfcs/MapaConcorrenciaF2.cfc method=selecionaItemPrestador\|selecionarItensFULL`** | POST | `id_smp, id_prestador, flag, id_smi, id_material, ...` | seleciona vencedor por item |
| `abrirMotivoAprovacao()` | `cfcs/MapaConcorrenciaF2.cfc method=adicionaPerguntasPrestadorMapa` | POST | `id_smp` | consulta |
| MAPA3 `alterarQtdPrestador()`, `alterarPrecoInicialPrestador()`, `alterarPrecoNegociadoPrestador()`, `alterarObsPrestador()`, `alteraAdiantamentoPrestador()`, `alteraRetencaoPrestador()`, `alteraImpostoPrestador()`, `alteraTaxaPrestador()`, `alteraFretePrestador()`, `alteraDiasPestador()`, `alterarAlojamentoPrestador()`, `alterarOutrosVPrestador()`, `alteraCondicaoPrestador()`, `alteraObsGeralPrestador()` | **`cfcs/MapaConcorrenciaF2.cfc`** métodos `prestadorAlteraQtd`, `prestadorAlteraPrecoInicial`, `prestadorAlterarPrecoNegociado` (+ **`acimaPreco`**[js 0/1]), `prestadorAlterarObs`, `prestadorAlterarAdiantamento`, `prestadorAlterarRetencao`, `prestadorAlterarImposto`, `prestadorAlterarTaxa`, `prestadorAlterarFrete`, `prestadorAlterarPagamentoDias`, `prestadorAlterarAlojamento`, `prestadorAlterarOutrosValores`, `prestadorAlterarCondicaoPagamento`, `prestadorAlterarObsGeral` | POST | `id_smi, id_smp, preco\|qtd\|valor\|taxa\|frete\|dias\|obs`[u] | **edita a cotação do prestador** (valores financeiros) |
| `atualizaValorPrestador()` | `cfcs/MapaConcorrenciaF2.cfc method=getTotalPrestadorPreco` | POST | `id_smp` | consulta |
| `atualizandoSituacaoRequisicao()` | **`cfcs/MapaConcorrenciaF2.cfc method=salvandoRequisicaoEdicaoPrestador`** | POST | `id_requisicao=3183`[js], `id_aditivo=0`[js], **`id_situacaoLogado=8`[js]**, `obs` | atualiza situação do mapa |
| `mostrarRequisitos()` / `carregarRequisitos()` / `aplicaResposta()` / `salvarNoRequisito()` / `salvarPrazoRequisito()` | `smapa_fase2_requisitos_prestador.cfm`, **`cfcs/mapaConcorrenciaF2.cfc method=aplicarRespostaRequisitoPrestador\|editarDadosRequisitosPrestador\|editarDadosRequisitosPrazoPrestador`** | POST | `id_prp, resposta, obs, id_preq, id_smp, prazo, garantia` | requisitos do prestador |
| `verAnexos()` / `listarAnexos()` | `prestador_anexos.cfm`, `prestador_anexos_listar.cfm` | POST | `id_smp, id_prestador, id_rotina, editar, cotando` | lista anexos |
| `uploadArquivo()` (MAPA3) | **`_prestador_anexos.cfm`** | POST multipart | `anexo`, `id_prestador, id_smp`[h] | upload (retornos: 1 extensão, -5/-10 tamanho MB, 2 erro gravar, 0 ok) |
| `excluirAnexo(id_anexo, arquivo)` | **`cfcs/prestadoresDAO.cfc method=excluirAnexoPrestador`** | POST | `arquivo`[h/js: nome/caminho do arquivo], `id_anexo` | **apaga arquivo** |
| `window.open` | `smapa_fase2_visualizar.cfm?id_requisicao=N&id_aditivo=N&fase=N` | GET | IDs | visualização |
| `window.open` | `../cadastro/nprestadores_listar.cfm?id_rotina=126&razao=<texto>&mapa_pessoa=<erro>` | GET | texto refletido | cadastro de prestador |

### 4.7 Requisição de materiais (suprimento/, rotina 153) — RMS1, RMS2

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `pesquisarRequisicao()` / `mostrarRequisicao()` | `req_materiais_listar2.cfm` | POST | `formPesquisaReq`[f] (`vid_requisicao, vnome_obra, obrasID, vid_situacao, vid_status, botao, clique, campo, ordem, id_rotina`) | lista |
| `editarRequisicao(id_requisicao, lista)` | `req_materiais_editar.cfm` | POST | `id_requisicao, id_rotina, clique, campo, ordem`, **`lista`** (string de IDs "122199,122198,…" do hidden `vlista`) | edição |
| `carregarItens()` / `RecarregarItens()` / `verMateriaisRequisicao()` | `req_materiais_itens_editar.cfm`, `req_materiais_itens_visualizar.cfm` | POST | `id_requisicao, novoCampo, novaOrdem` | itens |
| `alterarItem()` | **`_req_materiais_itens_editar2.cfm`** | POST | `id_requisicao, id_rmItem, quantidade`[u], `Obs`[u], `id_status, id_situacao`[h] | altera item (resposta ignorada) |
| `apagarItem()` / `reativarItem()` | **`_req_materiais_itens_apagar.cfm`** / **`_req_materiais_itens_reativar.cfm`** | POST | ids + `id_status, id_situacao`[h] | cancela/reativa item |
| `gravarCentroCustoItem()` | **`cfcs/requisicao_DAO.cfc?method=gravaCentroCustoItem`** / **`gravaCentroCustoItensTodasFamilias`** | POST | `id_rmItem, ccusto`[u], `id_familia`[h] | centro de custo |
| `#btnAprovaReq` / `aprovarRequisicaoCoordenacao()` | **`_req_aprovar.cfm`** | POST | `id_requisicao, id_obra`[h `eobrasID`], `id_status, id_situacao`[h], `req_tipo=1`[js], `motivoEntrega`[u] | aprova (2 sem itens, 3 sem entrega, 4 sem centro de custo, -1 erro) |
| `#btnSaveReq` | **`_req_editar.cfm`** | POST | idem + `observacao`[u] | salva |
| `#btnComprasReq` | **`_req_aprovar_lista_compras.cfm`** | POST | idem | envia para compras (-9 preço pendente) |
| `reprovarRequisicaoMotivo(valor)` | `req_materiais_reprovar.cfm` (`?cancel=1`) → **`_req_materiais_reprovar2.cfm`** | POST | `id_requisicao, motivo`[u], **`valor`**[js: 1 cancela / 0 reprova] | reprova ou cancela |
| `reativarRequisicaoCancelada()` | **`_req_materiais_reativar.cfm`** | POST | `id_requisicao` | reativa |
| `programarEntregas()` | `req_materiais_entregas.cfm` | POST | `id_requisicao, id_obra, editar` | entregas |
| `listarExtras()`, `carregarObservacoes()`, `apagarObs()` | `req_materiais_observacoes.cfm`, `req_materiais_observacoes_listar.cfm`, **`_req_observacao_apagar.cfm`** (`id_obs` apenas) | POST | ids | observações |
| `anexarRequisicao()`, `anexarArquivoReq()`, `apagarAnexo()` | `req_anexos.cfm`, **`_req_anexos_cadastrar.cfm`** (multipart, retorno 1 = extensão inválida), **`_req_anexos_apagar.cfm`** (`id_anexo, id_requisicao`) | POST | ids, arquivo | anexos |
| `adicionarMaterialRequisicao()`, `pesquisar()`, `mostrarPesquisa()`, `verFoto()` | `req_materiais_adicionar.cfm`, `req_materiais_adicionar_pesquisar.cfm`, `req_materiais_adicionar_pesquisar_foto.cfm` | POST | `formPesquisaMateriais`[f] (`campo_pesquisa, codigo, familia, contenhaPalavra, maxR, pbotao…`), `id_material` | pesquisa de materiais |
| carrinho: `adicionarItemCarrinho()`, `apagarItemCarrinho()`, `alteraQtdCarrinho()`, `mostrarCarrinho()`, `addCarrinho()`, `limparCarrinho()` | `req_materiais_carrinho_adicionar.cfm` (`id_material, quantidade` / `apagar=1` / `editar=1, qtd, obs` / `mostrar=1`), `req_materiais_carrinho_adicionar2.cfm`, `cfcs/carrinho_requisicao_materiais.cfc?method=getLimpaCarro` | POST | — | carrinho em sessão |
| `addItensRequisicao()` | **`_req_materiais_itens_carrinho_inserir.cfm`** | POST | `id_requisicao, id_status, id_situacao`[h] | grava itens do carrinho |
| `cadastrarMaterial()` / `salvarMaterial()` | `nmateriais_cadastrar.cfm` → **`_nmateriais_incluir.cfm`** | POST | `formCadMat`[f] + **`nAprovado=1`**[js] | cria material já aprovado |
| `mostrarPedidos()`, `verHistorico()` | `req_materiais_pedidos.cfm`, `popupHistoricoRequisicao.cfm` | POST | ids | consulta |
| `printerReq()` / form `formPrint` | `printRequisicao.cfm?id_requisicao=N` / `/suprimentos/printRequisicao.cfm` | GET / POST | id | impressão |
| `cadastrarNovaRequisicao()` | `req_materiais_cadastrar.cfm?id_rotina=153` | GET | — | nova |

### 4.8 Remessa de notas fiscais (suprimento/, rotina 161) — REMESSA

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `getRemessas()` | `nRomaneio_Listar.cfm` / `nRomaneio_Listar_So_Notas.cfm` | POST | `frmNF`[f] (`dinicial, dfinal, vRemessa, vNF, getStatus, soNotas`) + `var_obras` | lista |
| DataTables | `nromaneio_listar_ajax.cfm` | POST | `ro_id_setor=8`[js], filtros | dados JSON |
| `cadastrarRemessaNF()` / `editarRemessaNF()` | `nRomaneio_Cadastrar.cfm` (`?edicao=1` + `id_Romaneio`) | POST | — | formulário |
| `vamosAdicionarNF()` | **`_nromaneio_incluir.cfm`** | POST | `vengenheiro`[u], `vidSetor`[u], `id_romaneio`[h], `data, fornecedor, nf, rod_status, obs, rod_obs, id_obra, valorNF, id_qualidade, id_prazo, id_atendimento`[u] | insere NF na remessa (retorna `ID`) |
| `carregaDetalhe()` | `nRomaneio_Detalhe_Listar.cfm` | POST | `id_romaneio` | itens |
| `confirmarEsteRomaneio()` / `aprovarEsteRomaneio()` | **`_nromaneio_confirmar.cfm`** / **`_nromaneio_aprovar.cfm`** | POST | `id_romaneio, vengenheiro, vidSetor` | confirma/aprova (-1/-2/-5) |
| `baixarEsteRomaneio()` | **`_nromaneio_baixar.cfm`** | POST | `id_romaneio` | baixa (3 parcial, 4 total, 5 pendente) |
| `apagarEsteRomaneio()` / `apagarRomaneioNoListar()` | **`cfcs/romaneio_DAO.cfc?method=apagarRomaneio`** | POST | `id_romaneio, motivo`[js] | apaga remessa |
| `apagarDetalhe()`, `baixarDetalhe()`, `desfazerBaixa()`, `baixarDetalheLote()` | **`cfcs/romaneio_DAO.cfc?method=apagarRomaneioDetalhe\|baixarRomaneioDetalhe\|baixarRomaneioDetalheLote`** | POST | `id_RODetalhe`, `id_status` 0/1[js], `id_romaneio` | baixa/desfaz por item |
| `confirmarReprovacaoRomaneio()` | **`cfcs/romaneio_DAO.cfc?method=reprovarRomaneio`** | POST | `id_romaneio, motivo`[u] | reprova |
| `mostrarLog()` | `cfcs/romaneio_DAO.cfc?method=getHistorico` | POST | `id_romaneio` | histórico |
| `printer()` / `printerFrente()` | `nRomaneio_printer.cfm?id_romaneio=N` | GET | id | impressão |

### 4.9 Pedidos e materiais (pedido/, suprimento/npedido_print.cfm, gerencial/)

| Função JS / origem | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `relatorio()` / `mostrar()` (MATERIAIS) | `relatorio_material2.cfm` | POST | `id_rotina=31, idObras, idmaterial, contem, nmaterial, botao, clique, campo, ordem` | relatório |
| autocomplete | `cfcs/pedidos.cfc?method=LookupMaterial`, `../contrato/cfcs/contrato.cfc?method=getObrasFiltros` | GET JSON | `term` | consulta |
| link (MATERIAIS) | `suprimento/npedido_print.cfm?id_rotina=31&id_pedido=N` | GET | ids | imprime pedido |
| link (DESPESA2) | `suprimento/npedido_print.cfm?id_pedido=N` (**sem id_rotina**) | GET | id | imprime pedido |
| link (DESPESA2) | `gerencial/gerencial_pedido_observacao.cfm?id_pedido=N` (**sem id_rotina**; renderizou — REL-TIL) | GET | id | NFs do pedido |
| link (DESPESA2) | `financeiro/titulosPagarVer.cfm?id_Titulo=N&flag_origem=1&id_rotina=96` | GET | id | detalhe do título (favorecido, banco/agência/conta, valores) |
| `pesquisar()` (DESPESA) | `gerencial_obras3.cfm` | POST | `dataInicial, dataFinal, idObra, id_rotina=96, botao, clique, campo, ordem` | despesas |
| URL (DESPESA2) | `gerencial_obras5.cfm?id_obra=N&DataInicial=&DataFinal=&id_rotina=96&idObra=N` | GET | ids/datas | relatório |
| `exportarExcel()` / `exportarExcelNotTributos()` | `gerencial_obras_excel2.cfm?…` / `gerencial_obras_excel3.cfm?…` (`formExcel` serializado: `dataInicial, dataFinal, idObra, id_rotina, agrupado`) | GET | — | exportação |
| link | `gerencial_obras_pdf.cfm` | GET | — | PDF |
| autocomplete | `../cfcs/geral.cfc?method=pegarObras` | GET JSON | `term` | consulta |

### 4.10 Cadastro (cadastro/, rotina 109) — RAMAIS

| Função JS | Endpoint | Método | Parâmetros | Operação |
|---|---|---|---|---|
| `pesquisar()` | `relatorio_nextel2.cfm` | POST | `formPesquisa2`[f] (`nome`, `id_rotina=109`) | lista ramais (nome, ramal, e-mail, celular) |
| `imprimir()` | `relatorio_nextel_print.cfm?nome=<encodeURI(nome)>` | GET | `nome` refletido | impressão |
| link | `_nextel_excel.cfm` | GET | — | exportação |

---

## 5. Mapa de parâmetros (classificação por natureza)

### 5.1 Identificadores de objeto enviados pelo cliente (base do risco IDOR/BOLA — SEC-014)

`id_contrato`, `id_aditivo`, `id_aditivoAtual`, `id_aditivoContrato`, `ID_ADITIVOCONTRATO`, `id_medicao`, `id_medicaott`, `id_med`, `id_medRel`, `id_meds`, `id_material`, `id_servico`, `id_obra`/`idObra`/`id_Obra`, `id_pessoa`, `id_prestador`, `id_fornecedor`/`rod_idFornecedor`, `id_cliente`, `id_pedido`, `id_Titulo`, `id_requisicao`, `id_mrequisicao`, `id_rmItem`, `id_smp`, `id_smi`, `id_mri`, `id_prp`, `id_preq`, `id_romaneio`, `id_RODetalhe`, `id_anexo`, `id_memoria`, `id_obs`, `id_apuracao`, `id_responsavel`, `id_coordenador`, `id_encarregado`, `id_empresa`, `id_familia`, `id_unidade`, `id_setor`/`vidSetor`, `id_centroCusto`/`ccusto`, `id_rotina`.

### 5.2 Flags de papel, permissão e estado de workflow enviadas pelo cliente (novo — SEC-030)

| Parâmetro | Origem | Endpoint(s) | Semântica no JS |
|---|---|---|---|
| `responsavel` | hidden `=0` (MEDIÇÕES2) | `_medicoesAprova.cfm`, `medicao_avalia_percentual.cfm` (`id_responsavel`), `medicao_DAO.cfc atualizarValoresRodape` | "somente o engenheiro responsável pode aprovar a última medição" |
| `coordenador` = `1` / `2` | constante no JS | `_contrato_medicoes_previsto_aprova.cfm`, `_nmedicoes_previsto_edita.cfm`, `_contrato_medicoes_previsto_cancela.cfm`, `_nmedicoes_realizadas_inclui.cfm`, `_nmedicoes_realizadas_edita.cfm` | "1 quando for o coordenador e 2 quando for o engenheiro responsável" (comentário no JS) |
| `vcoordenador` / `coordenador` | hidden `=0` (11 ocorrências) | `nmedicoes_lancamentos_realizados.cfm`, `nmedicoes_lancamentos_previstos_cadastrar.cfm`, `contrato_obras_termos.cfm` | papel do usuário logado |
| `tipo` (1/2) | hidden `tipo3`/`tipo4`, argumento de função | reprovações/cancelamentos de medições de cliente | coordenador × engenheiro |
| `idSituacaoLogado` = `8`, `id_situacaoLogado` = `8` | **constante no JS** (MAPA/MAPA2/MAPA3) | `MapaConcorrenciaF2.cfc` `adicionarPrestadoresMapa`, `excluirPrestadorMapa`, `salvandoRequisicaoEdicaoPrestador` | "situação do usuário logado" |
| `id_status`, `id_situacao` | hidden (`2`, `0`) | `_req_*` (aprovar, editar, itens) | estado da requisição |
| `req_tipo=1`, `valor` (1 cancela/0 reprova), `nAprovado=1`, `flag_faturamento=1`, `previsao=1`, `edicao=1`, `paralisar=1`, `doIncluir=1`, `ajax=1`, `flag_cadastrar=1`, `listaPrecos`, `acimaPreco` (0/1), `campo` (altera lista de preço), `esconder` | constantes/checkbox | vários `_xxx.cfm` e CFCs | seletores de comportamento server-side |
| `lstEngenheiros` (lista de IDs) | hidden | `_contrato_obras_editar.cfm`, `_contrato_obras_coordenacao_aprova.cfm` | define quem pode medir a obra |

### 5.3 Valores financeiros / derivados enviados pelo cliente (SEC-004, SEC-008, SEC-031)

| Deveriam ser recuperados do banco (derivados) | Legitimamente informados pelo usuário (mas exigem autorização + validação) |
|---|---|
| Medição: `preco`, `quantContrato`, `vlContrato`, `qtdAcu`, `acumuladoMedido`, `quantidadeAcumulada2`, `porcentAtual`, `qtdMedidaAnterior`; rodapé: `valorNotaFiscal`, `totalPagar`, `vsaldoContrato`, `retencaoZero` | Medição: `quantMed`, `id_centroCusto`, `vDesconto`, `retencao`, `med_obs_memo` |
| Mapa: `imposto` (em `adicionarPrestadoresMapa`), `mri_pc` (preço PC do item em `_smapa_edit_material.cfm`), `acimaPreco` | Mapa: `preco`/`precoNegociado`, `qtd`, `adiantamento`, `retencao`, `imposto`, `taxa`, `frete`, `dias`, `alojamento`, `outros`, `pc` do serviço novo |
| Contrato: `id_situacao` em `_contratoAlteraImposto.cfm`; `vValorNF` pré-preenchido via CFC e reenviado | Contrato: `valor`, `quantidade` (`_servicosEdita.cfm`), `valorNF`, `novaRetencao`, `vAdiantamento`, `vretencao` |
| Medições de cliente: `id_obra` e `id_aditivo` junto com `id_med`/`id_medRel` (relação deveria vir do banco) | Medições de cliente: `valor`, `reajuste`, `inicial`, `fim`, `processo` |
| Remessa: `rod_status` | Remessa: `valorNF`, `nf`, `data`, notas de avaliação |

### 5.4 Ordenação, paginação e listas (SEC-036)

`botao`, `clique`, `campo`, `ordem`, `pbotao/pclique/pcampo/pordem`, `reqClique/reqCampo/reqOrdem`, `novoCampo`, `novaOrdem`, `frente`, `lista`/`vlista` (string CSV de IDs), `var_obras` (CSV de obras do multiselect), `obraID`/`idObras` (CSV), DataTables server-side: `iDisplayStart`, `iDisplayLength`, `iSortCol_0`, `sSortDir_0`, `sSearch`, `sColumns`.

### 5.5 Texto livre persistido (SEC-012, SEC-022)

`observacao`, `obs`, `obs_reprovar`, `obsContrato`, `obsReprovacao`, `reprova`/`reprovando`, `med_obs_memo{n}`, `motivo`, `motivoR`, `motivoEntrega`, `message`/`message2`, `par_obs`, `obsFatura`, `obsRel`, `obsRepre`, `processo`, `nomePrestador`, `descricao`, `especificacao`, `nome_material`, `nome_obra`, `desc_obra`, `nome_fiscal`, endereços, `condicoes_*`, `reajuste_formula`, `razao`, `nome`.

### 5.6 Arquivos

Upload: `anexo` (5 endpoints: `_anexaContrato.cfm`, `_anexo_memoria_servico.cfm`, `_req_anexos_cadastrar.cfm`, `_prestador_anexos.cfm`, form `anexoMemoriaCalculo.cfm`).
Exclusão: `id_anexo` (+`id_contrato`/`id_requisicao`), `id_memoria`, e **`arquivo`** (nome/caminho) em `prestadoresDAO.cfc excluirAnexoPrestador`.

---

## 6. Mapa de funções JavaScript (resumo por página)

| Página | Funções de leitura (consulta) | Funções de escrita (chamam `_*.cfm` / CFC) | Validações client-side relevantes |
|---|---|---|---|
| LOGIN | — | `lembrarSenha()` (GET) | obrigatoriedade |
| MEDIÇÕES1/2 | `pesquisar`, `mostrar`, `ordenando`, `editarMedicao`, `carregarListaMedicoes`, `carregarObservacao`, `carregarResumaoValores`, `carregarReprovacao`, `mostrarHistorico`, `abrirPontos`, `verDetalhe`, `avaliarPrestador` | `validandoDadosServicoMedicao`, `atualizarValoreRodape`, `aprovacaoUltimaMedicao`, `aprovarMedicaoEdicao`, `baixarMedicao`, `medicaoExcluirEdicao`, `medicaoReprovarEdicao`, `editarObsMedicao`, `alterarPeriodoMedicao`, dialog avaliação | quantidade ≤ contrato (com `eval`), centro de custo `0000000`, total < 0, total = 0, NF obrigatória, motivo, notas |
| NOVO-CONTRATO | `dadosPrestador`, `temImposto`, `mostrarMensagemPrevistos` | `finalizarCadastro` | datas/obra/prestador obrigatórios; confirmações de adiantamento/retenção/NF |
| CONTRATOS-EMP1/2 | `pesquisar*`, `mostrar*`, `gerenciarServicos`, `listarAnexos`, `dadosPrestador`, `mostrarHistorico`, `getFormulario`, `mostrarServicos`, `mostrarTotais`, `pequisarServicos` | `altImposto`, `alterarDadosContrato`, `aprovarContrato`, `diretoriaAprovarContrato`, `aprovarContratoAditivo`, `diretoriaAprovarContratoAditivo`, `salvarObservacaoContrato`, `reprovaContrato`, `reprovandoContratoAditivo` (GET), `cancelarContrato`, `excluiContrato`, `anexaContrato*`, `apagarArquivo`, `salvarRetencaoEdicaoContrato`, `editarServico`, `excluirServico`, `adicionarServico` | motivo obrigatório, datas de serviço, `somenteNumeros` |
| ANEXO1 | — | `uploadArquivo`, `excluirMemoria` | — |
| CLIENTE MEDIÇÕES / CONTRATO | `listarObras`, `mostrar`, `mostrarTermosCoordenacao`, `abrirMedicoes`, `vamosEditarObra`, `listarTudo`, `dadosContratoNew`, `getMenuRealizados`, `getRelatorio`, `getPrevistos`, `vamosRealizado`, `abrirHistorico`, `verAnexos`, `lancarNovosPrevistos`, `Nextel`, `getEndereco*` | `confirmarParalisacao`, `confirmarDesparalisacao`, `editarObra`, `aprovarObraParaMedicao`, `reativarFinalizada`, `flag_esconder` (GET), `salvarPrevisto*`, `alteraDadosPrevisto*`, `cancelaPrevisto*`, `aprovarMedicaoPrevisto*`, `reprovando`, `salvarPrevistoRealizado*`, `aprovarMedicaoPrevistoRealizado`, `salvarRealizado*`, `aprovarRealizado`, `aprovarMedicaoRealizada`, `cancelaRealizado*`, `reprovandoRealizado`, `medicaoFaturar`, `enviarMedicaoFaturamento`, `faturarPrevistoRealizadoCR`, `desfazerRealizadoZeradoCR`, `alterarProcesso` | campos obrigatórios da obra, engenheiros ≥ 1, datas, `updateCharacterCount` |
| CONTRATOS2 | `pesquisar`, `mostrar`, `aditarContrato`, `abrirDialog`, `abrirAtas`, `gestaoEmpenhosContratos` | `cancelarContrato` | `confirm()` |
| NOVO-MAPA / MAPA / MAPA2 / MAPA3 | 20+ funções de carga (`carregarMapa`, `abrirMapaFase*`, `verAnexos*`, `verHistorico`, `mostrarDialogListaPrecos`, `motrarPrecosPrestadores`, `carregarRequisitos`…) | ~40 funções de escrita (ver 4.6) | `validarCNPJ`, `somenteNumeros`, quantidade > 0, comparação preço negociado × PC (só define flag) |
| RMS1/RMS2 | `pesquisarRequisicao`, `mostrarRequisicao`, `editarRequisicao`, `carregarItens`, `RecarregarItens`, `listarExtras`, `verHistorico`, `anexarRequisicao`, `carregarObservacoes`, `mostrarPedidos`, `verMateriaisRequisicao`, `adicionarMaterialRequisicao`, `pesquisar`, `mostrarPesquisa`, `verFoto`, `mostrarCarrinho`, `programarEntregas` | `alterarItem`, `apagarItem`, `reativarItem`, `gravarCentroCustoItem`, `#btnAprovaReq`, `#btnSaveReq`, `#btnComprasReq`, `aprovarRequisicaoCoordenacao`, `reprovarRequisicaoMotivo`, `cancelarRequisicao`, `reativarRequisicaoCancelada`, `anexarArquivoReq`, `apagarAnexo`, `apagarObs`, carrinho (`adicionarItemCarrinho`, `apagarItemCarrinho`, `alteraQtdCarrinho`, `limparCarrinho`, `addCarrinho`, `addItensRequisicao`), `salvarMaterial` | quantidade > 0 (com typo `lenght`), centro de custo `0000000`, obra obrigatória |
| REMESSA | `getRemessas`, `carregaDetalhe`, `mostrarLog`, `cadastrarRemessaNF`, `editarRemessaNF` | `vamosAdicionarNF`, `confirmarEsteRomaneio`, `aprovarEsteRomaneio`, `apagarEsteRomaneio`, `apagarRomaneioNoListar`, `baixarEsteRomaneio`, `apagarDetalhe`, `desfazerBaixa`, `baixarDetalhe`, `baixarDetalheLote`, `confirmarReprovacaoRomaneio` | data/NF/fornecedor/obra/setor/engenheiro obrigatórios |
| REL-PAGTO, MATERIAIS, DESPESA, RAMAIS, REL-CONT, TABELA | funções de pesquisa/paginação/exportação | — | seleção obrigatória |

---

## 7. Fluxos de gravação reconstruídos

### 7.1 Medição de serviço (prestador) — rotina 41

```
medicoesMOLista.cfm ─pesquisar()─► medicoesMOLista2.cfm
   └─editarMedicao()─► medicoesMOEdita.cfm ─► medicaoMOEditaServicos.cfm / ...Observacao / ...RodapeValores / ...RodapeReprovacao
        ├─ por item: validandoDadosServicoMedicao(id) ─► _medicoesEdita.cfm  (0|1|2|3)
        │        └─ sucesso ─► medicao_DAO.cfc?method=atualizarValoresRodape ─► recarrega itens e rodapé
        ├─ alterarPeriodoMedicao() ─► _medicao_periodo_editar.cfm (1|-1|-2|-3|-4|-6)
        ├─ editarObsMedicao() ─► _medicaoEditaObs.cfm
        ├─ aprovarMedicaoEdicao() ─► _medicoesAprova.cfm (-1|0)
        ├─ aprovacaoUltimaMedicao() ─► _medicoesAprova.cfm ─► medicao_avalia_percentual.cfm ─(1)─► medicaoMOAvaliacaoPrestador.cfm ─► _medicoes_prestador_avaliar.cfm (0|-1|23000)
        ├─ medicaoReprovarEdicao() ─► _medicoesReprova.cfm
        └─ medicaoExcluirEdicao() ─► _medicoesExclui.cfm
   └─baixarMedicao()─► _medicoesBaixa.cfm (-1|ok)   [botão desabilitado durante a requisição]
```

### 7.2 Contrato de serviço — rotina 38

```
contratosNovo.cfm ─finalizarCadastro()─► _contratosIncluir.cfm (1 dup | 2 erro | 0 ok) ─► contratosLista.cfm?...&doNovo=1
contratosLista.cfm ─► contratosListaNew2.cfm
   ├─ gerenciarServicos(destino) ─► servicosIncluiNew.cfm ─► servicosIncluiNew2.cfm
   │      ├─ adicionarServico() ─► _servicosEdita.cfm (valor, quantidade)
   │      ├─ editarServico() ─► _servicosQtdEdita.cfm
   │      └─ excluirServico() ─► servicoIncluirAditivoVerMedicao.cfm ─(0)─► _servicosExclui.cfm
   ├─ aprovarContrato()/diretoriaAprovarContrato() ─► _contratoAprova.cfm (campo 0/1 altera lista de preço)
   ├─ aprovarContratoAditivo()/diretoria... ─► _contratoAprovaAditivo.cfm (-7)
   ├─ reprovaContrato() ─► _contratoReprova.cfm ; reprovandoContratoAditivo() ─GET► _contratoReprovaAditivo.cfm
   ├─ altImposto() ─► _contratoAlteraImposto.cfm ; salvarRetencaoEdicaoContrato() ─► _contratoRetencaoEditar.cfm
   ├─ alterarDadosContrato() ─► _contratoEditar.cfm (1|2|-4|0)
   ├─ cancelarContrato() ─► _contratoCancela.cfm (1 bloqueado) ; excluiContrato() ─► _contratoExclui.cfm
   └─ anexaContrato() ─► _anexaContrato.cfm ; apagarArquivo() ─► _contratoAnexoApagar.cfm
anexoMemoriaCalculo.cfm (popup) ─► _anexo_memoria_servico.cfm (upload) / _anexoMemoriaCalculoApagar.cfm
```

### 7.3 Obra e medições de cliente (previsto → realizado → faturamento) — rotina 70

```
contrato_pesquisar_obras_coordenacao.cfm ─► contrato_pesquisar_obras_coordenacao2.cfm
   ├─ vamosEditarObra() ─► contrato_obras_coordenacao_editar.cfm ─► editarObra() ─► _contrato_obras_editar.cfm (8|-2|0)
   │                                                       └─ aprovarObraParaMedicao() ─► _contrato_obras_coordenacao_aprova.cfm
   ├─ paralisarObra()/desparalisarObra() ─► _contrato_obras_paralisar.cfm
   ├─ reativarFinalizada() ─► _contrato_obras_coordenacao_reativar.cfm
   └─ abrirMedicoes() ─► nmedicoes_lancamentos.cfm
          ├─ PREVISTO: salvarPrevisto*() ─► nmedicoes_valida_datas.cfm (1|2|6) ─► _nmedicoes_previsto_edita.cfm
          │            aprovarMedicaoPrevisto[Encarregado|Coordenador]() ─► _contrato_medicoes_previsto_aprova.cfm (coordenador=2|1)
          │            cancelaPrevisto*() ─► _contrato_medicoes_previsto_cancela.cfm ; reprovando() ─► _contrato_medicoes_reprova.cfm
          ├─ REALIZADO: vamosRealizado() ─► nmedicoes_lancamentos_realizados.cfm
          │            salvarPrevistoRealizado*() ─► _nmedicoes_realizadas_inclui.cfm (-4)
          │            aprovarMedicaoPrevistoRealizado() ─► _contrato_medicoes_previsto_realizadas_aprovar.cfm
          │            salvarRealizado*()/aprovarRealizado() ─► _nmedicoes_realizadas_edita.cfm ─► _contrato_medicoes_realizadas_aprova.cfm
          │            cancelaRealizado*() ─► _contrato_medicoes_realizadas_cancela.cfm ; reprovandoRealizado() ─► _contrato_medicoes_realizadas_reprova.cfm
          └─ FATURAMENTO: medicaoFaturar() ─► medicoes.cfc medicaoPlanilha ─► enviarMedicaoFaturamento() ─► _nmedicoes_realizadas_fatura.cfm (2 sem planilha)
                         faturarPrevistoRealizadoCR() ─► _nmedicoes_realizadas_inclui_e_fatura.cfm ─► contrato_medicao_faturamento.cfm?id_medRel=N&id_rotina=82
                         desfazerRealizadoZeradoCR() ─► medicoes.cfc desfazerRealizadoFaturadoZerado
```

### 7.4 Mapa de concorrência (cotação → contrato) — rotina 179

```
smapa_listar.cfm ─► smapa_listar2.cfm
   ├─ Fase 1: cadastrar() ─► _smapa_cadastrar.cfm ; itens: _smapa_edit_material.cfm / _smapa_delete_material*.cfm ; datas/obra/obs: mapaConcorrenciaF1.cfc
   ├─ Fase 2: addPrestadorMapa() ─► MapaConcorrenciaF2.cfc adicionarPrestadoresMapa (idSituacaoLogado=8)
   │          salvarNovoPrestador() ─► existePrestador ─► _smapa_fase2_prestador_cadastrar.cfm ─► _prestador_aprovar.cfm | prestadoresDAO.cfc reprovarCadastroPrestador
   │          e-mails: _smapa_fase2_prestadores_email_send.cfm / _smapa_email_todos_send.cfm
   │          cotação do prestador (MAPA3): MapaConcorrenciaF2.cfc prestadorAlter* (preço, qtd, adiantamento, retenção, imposto, taxa, frete, dias…)
   │          anexos do prestador: _prestador_anexos.cfm (upload) / prestadoresDAO.cfc excluirAnexoPrestador(arquivo, id_anexo)
   │          desistir()/reintegrar() ─► _smapa_prestador_declinar.cfm / _smapa_prestador_reintegrar.cfm
   └─ Fase 3: selecionarPrestadoresItens() ─► MapaConcorrenciaF2.cfc selecionaItemPrestador|selecionarItensFULL
              aprovarRequisicaoF3() ─► _smapa_fase3_aprovar_validar.cfm ─► _smapa_fase3_aprovar.cfm
              gerarContrato() ─► _smapa_fase3_gerar_contrato.cfm  (cria contratos de serviço da rotina 38)
              atualizandoSituacaoRequisicao() ─► MapaConcorrenciaF2.cfc salvandoRequisicaoEdicaoPrestador (id_situacaoLogado=8)
```

### 7.5 Requisição de materiais — rotina 153

```
req_materiais_listar.cfm ─► req_materiais_listar2.cfm ─editarRequisicao(id, lista)─► req_materiais_editar.cfm
   ├─ itens: req_materiais_itens_editar.cfm ─► alterarItem() _req_materiais_itens_editar2.cfm | apagarItem() | reativarItem() | gravarCentroCustoItem() requisicao_DAO.cfc
   ├─ carrinho (sessão): req_materiais_carrinho_adicionar*.cfm ─► addItensRequisicao() _req_materiais_itens_carrinho_inserir.cfm
   │        └─ salvarMaterial() ─► _nmateriais_incluir.cfm (&nAprovado=1)
   ├─ btnSaveReq ─► _req_editar.cfm ; btnAprovaReq / aprovarRequisicaoCoordenacao() ─► _req_aprovar.cfm (2|3|4|-1|0)
   ├─ btnComprasReq ─► _req_aprovar_lista_compras.cfm (-9)
   ├─ reprovarRequisicaoMotivo(valor) ─► _req_materiais_reprovar2.cfm (valor 1 cancela | 0 reprova) ; reativar ─► _req_materiais_reativar.cfm
   └─ anexos/observações: _req_anexos_cadastrar.cfm | _req_anexos_apagar.cfm | _req_observacao_apagar.cfm (só id_obs)
```

### 7.6 Remessa de NF — rotina 161

```
romaneio_NF.cfm ─► nRomaneio_Listar*.cfm ─► nRomaneio_Cadastrar.cfm
   ├─ vamosAdicionarNF() ─► _nromaneio_incluir.cfm (retorna ID) ─► nRomaneio_Detalhe_Listar.cfm
   ├─ confirmar/aprovar ─► _nromaneio_confirmar.cfm / _nromaneio_aprovar.cfm ; baixar ─► _nromaneio_baixar.cfm (3|4|5)
   ├─ por NF: romaneio_DAO.cfc apagarRomaneioDetalhe | baixarRomaneioDetalhe (id_status 0/1) | baixarRomaneioDetalheLote
   └─ apagar/reprovar ─► romaneio_DAO.cfc apagarRomaneio | reprovarRomaneio ; histórico ─► getHistorico
```

### 7.7 Autenticação e senha

```
indexDes.cfm ─POST► login.cfm ─► indexLog.cfm (menu por rotinas)
indexDes.cfm ─GET► _enviarSenha.cfm?login=<e-mail>  (1 = e-mail não existe | 0 = "senha enviada")
menu ─GET► logout.cfm ; senhasEdita.cfm?id_rotina=4
```

---

## 8. Mapa de CFCs (componentes chamados diretamente pelo navegador)

Todos os métodos abaixo são chamados por URL/AJAX e portanto precisam de `access="remote"` (INDÍCIO FORTE). Nenhum token (`_cf_ajaxproxytoken` vazio) ou cabeçalho especial foi observado.

| CFC (caminho) | Métodos observados | Chamado por | Tipo |
|---|---|---|---|
| `/cfcs/geral.cfc` | `buscaRamal`, `pegarObras` | todas as páginas / DESPESA | leitura (HTML/JSON) |
| `/servico/cfcs/medicao_DAO.cfc` | **`atualizarValoresRodape`** | MEDIÇÕES2 | **escrita** (recalcula valores da medição a partir do form) |
| `/servico/cfcs/servico.cfc` | `getAutosuggestContratos`, `getAutosuggestObrasEng`, `getAutosuggestPrestadores` | MEDIÇÕES, REL-PAGTO | leitura JSON (`queryformat=column`) |
| `/servico/cfcs/contrato.cfc` | `getImpostoPrestador` | NOVO-CONTRATO | leitura |
| `/servico/cfcs/servicosIncluiNew.cfc` | `getTotaisServicos` | CONTRATOS-EMP2 | leitura |
| `/servico/cfcs/financeiro.cfc` | `selecionarIDPessoa` | REL-PAGTO | leitura |
| `/contrato/cfcs/contrato.cfc` | `pegarObras`, `pegarContratos`, `pegarAutoSuggestClientes`, `pegarClientes`, `pegarTipoContrato`, `selEmpresas`, `getObrasFiltros` | CONTRATO, CONTRATOS2, RMS, MATERIAIS | leitura (autosuggest e `cfselect bind`) |
| `/contrato/cfcs/medicoes.cfc` | `getLancamentosPrevistos`, `medicaoPlanilha`, **`desfazerRealizadoFaturadoZerado`** | NOVO-CONTRATO, CONTRATO | leitura + **escrita** |
| `/contrato/cfcs/contratoObras.cfc` | **`setExecucaoObra`** (via GET) | CONTRATO | **escrita** |
| `/mapaConcorrencia/cfcs/mapaConcorrenciaF1.cfc` | `getBindStatus`, `getCalculoTotalPC`, `getClienteObra`, `getIconeAnexoObra`, **`validaEdicaoInicioRequisicao`**, **`validaEdicaoFimRequisicao`**, **`alteraObraRequisicao`**, **`alteraObsRequisicao`** | MAPA* | leitura + **escrita** |
| `/mapaConcorrencia/cfcs/MapaConcorrenciaF2.cfc` | `existePrestador`, **`adicionarPrestadoresMapa`**, **`excluirPrestadorMapa`**, **`reprovarRequisicaoF2`**, **`cancelarRequisicaoF2`**, **`selecionaItemPrestador`**, **`selecionarItensFULL`**, `adicionaPerguntasPrestadorMapa`, **`salvandoRequisicaoEdicaoPrestador`**, **`aplicarRespostaRequisitoPrestador`**, **`editarDadosRequisitosPrestador`**, **`editarDadosRequisitosPrazoPrestador`**, `getTotalPrestadorPreco`, **`prestadorAlteraQtd`**, **`prestadorAlteraPrecoInicial`**, **`prestadorAlterarPrecoNegociado`**, **`prestadorAlterarObs`**, **`prestadorAlterarAdiantamento`**, **`prestadorAlterarRetencao`**, **`prestadorAlterarImposto`**, **`prestadorAlterarTaxa`**, **`prestadorAlterarFrete`**, **`prestadorAlterarPagamentoDias`**, **`prestadorAlterarAlojamento`**, **`prestadorAlterarOutrosValores`**, **`prestadorAlterarCondicaoPagamento`**, **`prestadorAlterarObsGeral`** | MAPA* | predominantemente **escrita** (28 métodos) |
| `/mapaConcorrencia/cfcs/mapaConcorrenciaServicos.cfc` | **`reprovarServico`** | MAPA* | escrita |
| `/mapaConcorrencia/cfcs/mapaConcorrenciaCotacao.cfc` | **`reprovarCotacao`** | MAPA* | escrita |
| `/mapaConcorrencia/cfcs/prestadoresDAO.cfc` | **`reprovarCadastroPrestador`**, **`excluirAnexoPrestador(arquivo, id_anexo)`** | MAPA* | escrita / **exclusão de arquivo** |
| `/suprimento/cfcs/requisicao_DAO.cfc` | **`gravaCentroCustoItem`**, **`gravaCentroCustoItensTodasFamilias`** | RMS | escrita |
| `/suprimento/cfcs/carrinho_requisicao_materiais.cfc` | `getLimpaCarro` | RMS | escrita em sessão |
| `/suprimento/cfcs/romaneio_DAO.cfc` | **`apagarRomaneio`**, **`apagarRomaneioDetalhe`**, **`baixarRomaneioDetalhe`**, **`baixarRomaneioDetalheLote`**, **`reprovarRomaneio`**, `getHistorico` | REMESSA | escrita |
| `/pedido/cfcs/pedidos.cfc` | `LookupMaterial` | MATERIAIS | leitura |
| `cfcs/pessoa_DAO.cfc` (funcoes.js) | **`capagarPessoa`** | função global disponível em todas as telas | **exclusão de pessoa** |
| `/suprimento/cfcs/pedido_DAO2.cfc` (baseline) | `GETPRINTORDER` (linha ~141) | `npedido_print.cfm` | leitura com SQL concatenado (SEC-001) |

Padrões de resposta observados: código numérico puro (`0`, `1`, `-1`, `23000`), JSON `{ERRO, MESSAGE}` (mapa), JSON `{ID}` (remessa), JSON `{STATUS, MESSAGE}` (upload memória), XML/WDDX lido com `$(volta).find('string')` (`getLancamentosPrevistos`), HTML injetado com `.html()`.

---

## 9. Matriz de validação client-side × server-side

| Regra | Navegador (arquivo / função) | Servidor (evidência) | Resultado | Risco |
|---|---|---|---|---|
| Quantidade medida ≤ quantidade contratada | MEDIÇÕES2 `validandoDadosServicoMedicao` (com `eval`) | `_medicoesEdita.cfm` retorno `1` | CONTROLE IDENTIFICADO (origem dos valores comparados **A VERIFICAR**: o cliente envia `quantContrato`) | ALTO se comparar com valor enviado |
| Acumulado ≥ medição anterior | — | `_medicoesEdita.cfm` retorno `2` | CONTROLE IDENTIFICADO | idem |
| Centro de custo obrigatório ao medir | JS (`0000000`) | `_medicoesEdita.cfm`: **não observado**; `_medicoesAprova.cfm` / `_medicoesBaixa.cfm` retorno `-1` | Parcial: detectado só na aprovação/baixa | MÉDIO |
| Total a pagar não negativo | JS (`totalPagar < 0`) | não observado | **A VERIFICAR NO SERVIDOR** | ALTO (financeiro) |
| Total a pagar = 0 | `confirm` | não observado | A VERIFICAR | MÉDIO |
| NF (número e data) obrigatória na baixa | JS `baixarMedicao` | não observado | A VERIFICAR | MÉDIO |
| Motivo obrigatório (reprovação medição/contrato/requisição/remessa) | JS | não observado | A VERIFICAR | BAIXO |
| Notas em todos os indicadores da avaliação | JS | `_medicoes_prestador_avaliar.cfm` `-1`, `23000` (duplicidade) | CONTROLE IDENTIFICADO (duplicidade) | BAIXO |
| Período da medição coerente | — | `_medicao_periodo_editar.cfm` `-1,-2,-3,-6` | CONTROLE IDENTIFICADO | — |
| Datas início/término do contrato | JS `validarDados` | `_contratoEditar.cfm` `1` (ordem), `2` (obrigatórias) | CONTROLE IDENTIFICADO | — |
| Prestador não alterável com títulos baixados | — | `_contratoEditar.cfm` `-4` | CONTROLE IDENTIFICADO | — |
| Contrato sem serviços não aprova | — | `_contratoAprova.cfm` `-1` | CONTROLE IDENTIFICADO | — |
| Aditivo sem alteração de valor não aprova | — | `_contratoAprovaAditivo.cfm` `-7` | CONTROLE IDENTIFICADO | — |
| Contrato com adiantamento/medição não cancela/exclui | — | `_contratoCancela.cfm`/`_contratoExclui.cfm` `1` | CONTROLE IDENTIFICADO | — |
| Serviço já medido não exclui | — | `servicoIncluirAditivoVerMedicao.cfm` `1` (mas é chamada **separada** da exclusão: TOCTOU) | Parcial | MÉDIO |
| Código de contrato duplicado | — | `_contratosIncluir.cfm` `1` | CONTROLE IDENTIFICADO | — |
| Adiantamento/retenção/percentual NF = 0 | JS confirmações | não observado | A VERIFICAR | BAIXO |
| Obra/prestador obrigatórios no contrato | JS | não observado | A VERIFICAR | BAIXO |
| Soma das OS ≤ valor do contrato | — | `_contrato_obras_editar.cfm` `-2` | CONTROLE IDENTIFICADO | — |
| Datas da OS coerentes | — | `_contrato_obras_editar.cfm` `8` | CONTROLE IDENTIFICADO | — |
| Soma das medições ≤ valor da OS | — | `nmedicoes_valida_datas.cfm` `6`, `_nmedicoes_realizadas_inclui.cfm` `-4` | CONTROLE IDENTIFICADO (mas a validação de datas é **requisição separada** da gravação) | MÉDIO |
| Datas da medição dentro da OS | — | `nmedicoes_valida_datas.cfm` `1`, `2` | CONTROLE IDENTIFICADO (idem) | MÉDIO |
| Engenheiros, fiscal, telefone, endereço obrigatórios para aprovar obra | JS `aprovarObraParaMedicao` | não observado (callback assume sucesso) | A VERIFICAR | MÉDIO |
| Obra reativada só se contrato não finalizado | — | `_contrato_obras_coordenacao_reativar.cfm` `1` | CONTROLE IDENTIFICADO | — |
| Planilha anexada antes de faturar | — | `medicoes.cfc medicaoPlanilha` e `_nmedicoes_realizadas_fatura.cfm` `2` | CONTROLE IDENTIFICADO | — |
| Requisição: itens, entregas, centro de custo, preço pendente | — | `_req_aprovar.cfm` `2,3,4`; `_req_aprovar_lista_compras.cfm` `-9` | CONTROLE IDENTIFICADO | — |
| Quantidade de item > 0 | JS (`quantidade.lenght` — typo, checagem parcial) | não observado | A VERIFICAR | BAIXO |
| Remessa sem NF não confirma/aprova/baixa | — | `_nromaneio_*` `-1`, `-5` | CONTROLE IDENTIFICADO | — |
| CNPJ válido / prestador existente | JS `validarCNPJ` + `existePrestador` | CFC `existePrestador` | CONTROLE IDENTIFICADO | — |
| Preço negociado acima do PC | JS calcula e **envia `acimaPreco`** | recebe flag do cliente | **A VERIFICAR** (flag deveria ser calculada no servidor) | MÉDIO |
| Extensão e tamanho de anexo | — | `_req_anexos_cadastrar.cfm` `1`; `_prestador_anexos.cfm` `1`, `-5/-10` | CONTROLE IDENTIFICADO (lista permitida × proibida: A VERIFICAR) | MÉDIO |
| `id_material` inteiro na pesquisa | JS `_CF_checkinteger` (cfinput) | não observado | A VERIFICAR | BAIXO |
| Papel do usuário (responsável / coordenador / engenheiro) | botões renderizados + **flags enviadas** | não observável | **A VERIFICAR — PRIORIDADE MÁXIMA** | CRÍTICO |

---

## 10. Lista preliminar de achados (atualização do baseline + novos)

### 10.1 Achados do baseline reclassificados com o novo material

| ID | Situação após esta etapa |
|---|---|
| SEC-001 (SQL concatenado em `pedido_DAO2.cfc`) | Mantido CONFIRMADO. **Deixa de ser caso isolado**: segunda ocorrência em `financeiro/titulosPagarVer.cfm` (ver SEC-027). Padrão (2 de 2 erros SQL/variável observados indicam entrada direta em SQL ou variável sem escopo). |
| SEC-002 (exposição de erros) | CONFIRMADO e **sistêmico**: 3 páginas de erro em 3 módulos (suprimento, servico, financeiro), todas com o mesmo dump (ver SEC-028). |
| SEC-003 / SEC-004 / SEC-005 (medição) | CONFIRMADO o envio dos campos hidden por item (`preco=75.0000`, `quantContrato`, `vlContrato=2543.0816`, etc. em MEDIÇÕES2). SEC-004 permanece INDÍCIO FORTE. Novo: `medicao_DAO.cfc atualizarValoresRodape` recebe `vDesconto`, `retencao`, `totalPagar`, `valorNotaFiscal`, `vsaldoContrato` do formulário. |
| SEC-006 (CFC direto) | CONFIRMADO em escala: **20 CFCs / ~75 métodos** chamados pelo navegador, ~45 de escrita (seção 8). |
| SEC-007 / SEC-010 / SEC-011 (autorização aprovar/excluir/reprovar) | A VERIFICAR, agora agravado por SEC-030 (flag `responsavel` enviada pelo cliente). |
| SEC-008 (valores financeiros na aprovação) | CONFIRMADO o formulário (`formMedicaoAprovar`: `valorNotaFiscal`, `totalPagar`, `vsaldoContrato`, `retencaoZero` hidden). Confiança server-side A VERIFICAR. |
| SEC-009 (duplicidade baixa) | Mantido. Padrão repetido em `_nromaneio_baixar.cfm`, `_smapa_fase3_gerar_contrato.cfm` (botão `btnAddPrestadores` desabilitado no `beforeSend`). |
| SEC-013 / SEC-014 (IDOR em relatórios e objeto a objeto) | INDÍCIO FORTE reforçado por SEC-025/SEC-026. |
| SEC-015 (CSRF) | INDÍCIO FORTE reforçado: nenhum token em 33 páginas, `_cf_ajaxproxytoken=''`, operações de estado via GET (SEC-032). Falta apenas confirmar `SameSite`/`Origin` no servidor. |
| SEC-016 (regras só no cliente) | Matriz completa na seção 9. |
| SEC-017 (`eval`) | CONFIRMADO (3 `eval` em MEDIÇÕES2) + `eval` em `ajaxfileupload.js` (SEC-038). |
| SEC-018 (IDs duplicados) | CONFIRMADO em mais páginas: `medicaoEdita` ×6, `CFForm_1` ×2 (CONTRATO), 56 `<form>` com nomes repetidos (CLIENTE MEDIÇÕES), `id_contrato`/`id_obra` repetidos. |
| SEC-019 / SEC-020 (concorrência/transação) | Nenhum campo de versão/timestamp em nenhum formulário dos 9 módulos. Validação e gravação em requisições separadas (`nmedicoes_valida_datas.cfm` → `_nmedicoes_previsto_edita.cfm`; `servicoIncluirAditivoVerMedicao.cfm` → `_servicosExclui.cfm`) = janela TOCTOU. |
| SEC-021 (dependências) | Inventário completo na seção 1.4 (ver SEC-040). |
| SEC-022 / SEC-023 | Mantidos. `encodeURI` também em `imprimir()` (RAMAIS) e `obs_reprovar`. |
| SEC-024 (POST não é controle) | Mantido; há exceções em GET (SEC-032). |

### 10.2 Novos achados

Formato: ID · Título · Módulo · Arquivo(s) · Função/método · Evidência · Criticidade · Descrição · Evidência técnica · Fluxo · Impacto · Causa · Recomendação · Esforço · Prioridade.

---

**SEC-025 — Autorização por rotina depende do parâmetro `id_rotina` enviado pelo cliente**
- Módulo: transversal (`logon/`).
- Arquivos: `logon/_includeValidacao.cfm` (linha 4), `logon/_verificaPermissoesRotina.cfm` (linha 30), TABELA2.html, REL-CONT2.html, REL-NF.htm, MEDIÇÕES2.html, CONTRATO.html.
- Classificação: **INDÍCIO FORTE**.
- Criticidade: **CRÍTICA se confirmada** (broken access control horizontal e vertical em toda a aplicação).
- Descrição: a checagem de permissão lê `ID_ROTINA` da requisição. Como o mesmo template é aberto com rotinas diferentes conforme o menu de origem, a hipótese é que a verificação seja "o usuário possui a rotina informada?" e não "o usuário possui a rotina à qual esta página pertence".
- Evidência técnica: (a) `relatorio_tabela_rel01.cfm` sem `id_rotina` → erro "Variable ID_ROTINA is undefined" em `_verificaPermissoesRotina.cfm:30`; (b) `relatorio_contrato_rel01.cfm` aberto com `id_rotina=96` (REL-CONT2) e `relatorio_contrato_rel04.cfm` com `id_rotina=41` e `42`; (c) `financeiro/titulosPagarVer.cfm` aberto com `id_rotina=96` (rotina do módulo gerencial); (d) `anexoMemoriaCalculo*.cfm` com `id_rotina=38` e `41`; (e) o JS de CONTRATO.html redireciona para `contrato_medicao_faturamento.cfm?...&id_rotina=82` a partir de uma tela de rotina 70; (f) `id_rotina` viaja em hidden, em constantes JS (`var id_rotina = 38`) e em query string.
- Fluxo afetado: todas as páginas que incluem `_includeValidacao.cfm`.
- Impacto: um usuário autenticado poderia abrir páginas de módulos que não lhe pertencem informando uma rotina que possui. Combinado com SEC-026/SEC-014, acesso a relatórios financeiros, títulos, pedidos, medições de outras obras.
- Causa: acoplamento entre o menu e o controle de acesso; identificador da rotina passado pelo cliente em vez de mapeado no servidor.
- Recomendação: em `_verificaPermissoesRotina.cfm` (ou no `Application.cfc`), mapear `CGI.SCRIPT_NAME` → rotina(s) permitidas em tabela e ignorar `id_rotina` da requisição para fins de autorização; manter o parâmetro apenas para navegação. Registrar tentativas negadas.
- Esforço: médio. Prioridade: **1**.

---

**SEC-026 — Páginas de impressão/relatório/popup acessíveis por GET só com o ID do objeto, algumas sem verificação de rotina**
- Módulo: suprimento, gerencial, financeiro, contrato, servico, mapaConcorrencia, cadastro.
- Arquivos/endpoints: `suprimento/npedido_print.cfm?id_pedido=N` (link em DESPESA2 sem `id_rotina`; PEDIDO.html sem parâmetros falhou na linha 4 do template e não na checagem de rotina), `gerencial/gerencial_pedido_observacao.cfm?id_pedido=N` (REL-TIL renderizou sem `id_rotina`), `financeiro/titulosPagarVer.cfm?id_Titulo=N`, `contrato/popupHistoricoObra.cfm?id_Obra=N`, `contrato/popupHistoricoContrato.cfm?id_contrato=N`, `contrato/relatorio_dados_obra.cfm?id_obra=N`, `contrato/contrato_empenhos_faturas.cfm?id_contrato=N`, `contrato/nmedicoes_lancamentos_relatorio.cfm?vid_contrato=N&printer=1`, `suprimento/nRomaneio_printer.cfm?id_romaneio=N`, `suprimento/printRequisicao.cfm?id_requisicao=N`, `mapaConcorrencia/smapa_fase2_visualizar.cfm?id_requisicao=N&fase=N`, `servico/anexoMemo*.cfm`, `servico/relatorio_contrato_rel0*.cfm`, `cadastro/relatorio_nextel_print.cfm?nome=`.
- Classificação: **CONFIRMADO** quanto ao padrão de acesso; **INDÍCIO FORTE** de ausência de checagem de rotina em `npedido_print.cfm` e `gerencial_pedido_observacao.cfm`; autorização objeto a objeto **A VERIFICAR**.
- Criticidade: **ALTA**.
- Descrição: relatórios com dados de fornecedores, valores, conta bancária da empresa (REL-NF), preços de cotação, são identificados apenas pelo ID sequencial na URL.
- Impacto: leitura indevida entre obras/setores; facilita reconhecimento de IDs para os fluxos de escrita.
- Causa: ausência de função central "usuário pode ver este objeto".
- Recomendação: incluir a validação de sessão + rotina + posse do objeto no topo dessas páginas (função central `podeVerObjeto(tipo, id)`); preferir POST ou tokens de acesso curtos para impressão; não expor sequenciais quando possível.
- Esforço: médio. Prioridade: **1**.

---

**SEC-027 — Segunda evidência de entrada externa concatenada em SQL (`titulosPagarVer.cfm`)**
- Módulo: financeiro. Arquivo: `E:\sistemas\ASEng\financeiro\titulosPagarVer.cfm`, **linha 14 (`CFQUERY`)**. Evidência: REL-NF2.htm.
- Classificação: **CONFIRMADO** (concatenação sem `cfqueryparam`). Explorabilidade: A VERIFICAR.
- Criticidade: **ALTA** (mesma classe da SEC-001).
- Evidência técnica: a URL `titulosPagarVer.cfm?id_Titulo=&flag_origem=1&id_rotina=96` (valor vazio) produziu `[Macromedia][SQLServer JDBC Driver][SQLServer]Incorrect syntax near '='`, `SQLState HY000`, `NativeErrorCode 102`, `DataSource ASNOVO`. Com `cfqueryparam`, um valor vazio gera erro de validação do ColdFusion antes de chegar ao SQL Server; um erro de sintaxe SQL só ocorre quando o valor é interpolado diretamente (`WHERE ... = #url.id_Titulo#`).
- Fluxo: visualização de título a pagar (link de DESPESA2).
- Impacto: leitura/alteração de dados financeiros via injeção, se confirmada.
- Recomendação: `cfqueryparam cfsqltype="cf_sql_integer"` + `cfparam` com validação de tipo; auditoria de todos os `cfquery` do módulo financeiro.
- Esforço: baixo (por arquivo) / alto (varredura). Prioridade: **1**.

---

**SEC-028 — Handler global de exceções faz `cfdump` da exceção para o navegador**
- Módulo: transversal (`Application.cfc`). Arquivos: PEDIDO.html, TABELA2.html, REL-NF2.htm.
- Classificação: **CONFIRMADO**.
- Criticidade: **ALTA**.
- Evidência: as três páginas contêm tabela `class="cfdump_struct"` com "Error details" e as chaves `Cause`, `StackTrace`, `TagContext` (`RAW_TRACE`, `TEMPLATE`, `LINE`), `RootCause`, `DataSource`, `SQLState`, `NativeErrorCode`. Revela `E:\sistemas\ASEng\` (raiz), `Application.cfc:942`, `logon/_includeValidacao.cfm:4`, `logon/_verificaPermissoesRotina.cfm:30`, `financeiro/titulosPagarVer.cfm:14`, `suprimento/npedido_print.cfm:4`, versão do driver JDBC, Tomcat, Java.
- Recomendação: no `onError`, registrar o dump em log interno com ID único e devolver mensagem genérica; desativar "Enable Robust Exception Information" no CF Administrator (A VERIFICAR se está ativo).
- Esforço: baixo. Prioridade: **1**.

---

**SEC-029 — Recuperação de senha sem autenticação, via GET, com enumeração de usuários e envio da senha**
- Módulo: logon. Arquivo: LOGIN.html, função `lembrarSenha()`, endpoint `logon/_enviarSenha.cfm`.
- Classificação: **CONFIRMADO** (GET, enumeração, mensagem); armazenamento reversível de senha: **INDÍCIO FORTE**.
- Criticidade: **ALTA**.
- Evidência: `$.ajax({url:'_enviarSenha.cfm', type:'get', data:{login:email}})`; retorno `1` → "O e-mail informado não existe no sistema"; retorno `0` → "A senha foi enviada com sucesso". Sem CAPTCHA, sem limite observável.
- Impacto: enumeração de contas `@almeidasapata.com.br`; se a senha atual é enviada por e-mail, ela está armazenada em claro ou cifrada de forma reversível; e-mails de logs/proxy registram o `login` na URL.
- Recomendação: resposta uniforme ("se o e-mail existir, enviaremos instruções"), POST, token de redefinição de uso único com expiração, hash de senha (bcrypt/argon2) e limitação de taxa.
- Esforço: médio. Prioridade: **2**.

---

**SEC-030 — Flags de papel/perfil e de estado de workflow enviadas pelo cliente**
- Módulo: servico (medições), contrato (medições de cliente), mapaConcorrencia, suprimento.
- Arquivos: MEDIÇÕES2 (`responsavel` hidden = 0 → `_medicoesAprova.cfm`, `medicao_avalia_percentual.cfm`), CONTRATO.html (`coordenador:1/2`, `tipo`, `vcoordenador` → `_contrato_medicoes_previsto_aprova.cfm`, `_nmedicoes_previsto_edita.cfm`, `_nmedicoes_realizadas_inclui.cfm`, `_nmedicoes_realizadas_edita.cfm`, `_contrato_medicoes_previsto_cancela.cfm`), MAPA/MAPA2/MAPA3 (`idSituacaoLogado = 8` constante no JS → `MapaConcorrenciaF2.cfc adicionarPrestadoresMapa/excluirPrestadorMapa`; `id_situacaoLogado = 8` → `salvandoRequisicaoEdicaoPrestador`), RMS (`id_status`, `id_situacao`, `req_tipo`, `nAprovado=1`, `valor` 1/0).
- Classificação: **CONFIRMADO** quanto ao envio; confiança server-side **A VERIFICAR — PRIORIDADE MÁXIMA**.
- Criticidade: **CRÍTICA se confiados** (escalada de privilégio: aprovar como coordenador/engenheiro responsável; alterar estado de requisições; criar material já aprovado).
- Evidência técnica: comentários do próprio JS — "PARAMETRO TIPO: 1 QUANDO FOR O COORDENADOR E 2 QUANDO FOR O ENGENHEIRO RESPONSÁVEL"; "O parâmetro coordenador vai como valor 2 para identificar que é um encarregado"; "Somente o engenheiro responsável pode aprovar a última medição" (a decisão depende do hidden `responsavel`).
- Recomendação: derivar papel e situação exclusivamente da sessão no servidor (`session.id_usuario` → perfil → vínculo com obra/contrato); ignorar/rejeitar esses parâmetros; ler `id_status/id_situacao` do banco antes de qualquer transição de estado; usar máquina de estados server-side.
- Esforço: médio. Prioridade: **1**.

---

**SEC-031 — Valores financeiros e derivados enviados pelo cliente em outros módulos (extensão de SEC-004/008)**
- Módulo: servico, contrato, mapaConcorrencia, suprimento.
- Evidência: seção 5.3. Destaques: `medicao_DAO.cfc atualizarValoresRodape` (recebe `totalPagar`, `valorNotaFiscal`, `vsaldoContrato`); `_smapa_edit_material.cfm` recebe `mri_pc`; `adicionarPrestadoresMapa` recebe `imposto`; `prestadorAlterarPrecoNegociado` recebe `acimaPreco` calculado no navegador; `_contratoAlteraImposto.cfm` recebe `id_situacao`; `_nmedicoes_realizadas_*` recebem `valor` e `reajuste` junto com `id_obra`/`id_aditivo`.
- Classificação: **INDÍCIO FORTE**. Criticidade: **ALTA** se confiados.
- Recomendação: para cada endpoint, separar "entrada do usuário" de "contexto" e recarregar o contexto do banco; recalcular totais no servidor.
- Esforço: médio/alto. Prioridade: **2**.

---

**SEC-032 — Operações que alteram estado via GET**
- Arquivos: CONTRATOS-EMP1/2 `reprovandoContratoAditivo()` → `_contratoReprovaAditivo.cfm` (`type:'GET'`, com `reprova` e ids na query string); CONTRATO.html handler de `flag_esconder` → `cfcs/contratoObras.cfc method=setExecucaoObra` (`$.ajax` sem `type`, portanto GET); `logon/logout.cfm`; `logon/_enviarSenha.cfm`.
- Classificação: **CONFIRMADO**. Criticidade: **MÉDIA** (ALTA em conjunto com SEC-015).
- Impacto: CSRF por simples `<img>`/link; dados sensíveis em logs de acesso, histórico e cabeçalho Referer.
- Recomendação: converter para POST; no `Application.cfc`, rejeitar GET em templates com prefixo `_` e em métodos CFC de escrita.
- Esforço: baixo. Prioridade: **2**.

---

**SEC-033 — Ausência de qualquer mecanismo anti-CSRF observável nas 33 páginas**
- Evidência: nenhum campo/header `csrf|token|nonce`; `_cf_ajaxproxytoken:''`; formulários e AJAX enviam apenas os dados de negócio; `X-Requested-With` não é verificado (não observável) e não protege formulários HTML clássicos (`formlogin`, `formPrintContrato`, `selmedicao`, `formVoltar`).
- Classificação: **INDÍCIO FORTE** (mantida a ressalva de `SameSite`/`Origin`, não observáveis). Criticidade: **ALTA**.
- Recomendação: `CSRFGenerateToken()`/`CSRFVerifyToken()` nativos do CF (disponíveis a partir do CF 10) injetados por `Application.cfc` em todos os `_*.cfm` e métodos remotos de escrita; `SameSite=Lax` nos cookies de sessão (suportado por `this.sessioncookie.samesite` nas atualizações recentes do CF 2016/2018/2021).
- Esforço: médio. Prioridade: **2**.

---

**SEC-034 — Identificador de cliente do CF Ajax idêntico antes e depois da autenticação**
- Evidência: `_cf_clientid='C3912D2547362D096D26EC692AA0A7DB'` em LOGIN.html (`indexDes.cfm`, não autenticada) e em CONTRATO.html / CONTRATOS-EMP2.html (autenticadas).
- Classificação: **INDÍCIO** de que a sessão do ColdFusion não é rotacionada no login (fixação de sessão). Ressalva: o LOGIN.html pode ter sido salvo na mesma sessão após navegação autenticada.
- Criticidade: **MÉDIA**.
- Recomendação: `SessionRotate()` após autenticação bem-sucedida e `SessionInvalidate()` no logout; confirmar em `login.cfm`/`logout.cfm`.
- Esforço: baixo. Prioridade: **3**.

---

**SEC-035 — Uploads e exclusão de anexos: controles parciais e parâmetro de caminho do arquivo vindo do cliente**
- Endpoints: `_anexaContrato.cfm`, `_anexo_memoria_servico.cfm`, `_req_anexos_cadastrar.cfm`, `_prestador_anexos.cfm`, `anexoMemoriaCalculo.cfm` (upload); `_contratoAnexoApagar.cfm`, `_anexoMemoriaCalculoApagar.cfm`, `_req_anexos_apagar.cfm`, `prestadoresDAO.cfc excluirAnexoPrestador` (exclusão).
- Classificação: extensão/tamanho → **CONTROLE IDENTIFICADO** (retornos `1` extensão inválida, `-5/-10` tamanho em MB); lista permitida × proibida, MIME, renomeação, local de gravação (dentro ou fora do webroot), download com autorização → **A VERIFICAR**. `excluirAnexoPrestador(arquivo, id_anexo)` recebendo o **nome/caminho do arquivo** → **INDÍCIO FORTE** de exclusão arbitrária/path traversal se o servidor usar `arquivo` no `cffile action="delete"` sem reconciliar com `id_anexo`.
- Criticidade: **ALTA**.
- Recomendação: no servidor, resolver o caminho físico exclusivamente a partir de `id_anexo` (registro no banco), validar posse do objeto, allowlist de extensões e verificação de conteúdo, gravar fora do webroot e servir via `cfcontent` com autorização; verificar se o conector CKFinder está publicado (`ckfinder.js` é carregado em 13 páginas).
- Esforço: médio. Prioridade: **2**.

---

**SEC-036 — Ordenação/paginação dinâmica e listas de IDs vindas do cliente (candidatos a `ORDER BY`/`IN (...)` concatenados)**
- Evidência: `campo`, `ordem`, `novoCampo`, `novaOrdem` em 12 listagens; DataTables server-side (`iSortCol_0`, `sSortDir_0`, `sSearch`) em `relatorio/relatorioPagamentos_ajax.cfm` e `nromaneio_listar_ajax.cfm`; `lista`/`vlista` ("122199,122198,…") em `req_materiais_editar.cfm`; `var_obras`, `obraID`, `idObras` (CSV de IDs) em relatórios; `lstEngenheiros` (CSV) em `_contrato_obras_editar.cfm`. A SEC-001 foi disparada justamente por uma lista "a,b" em um parâmetro numérico.
- Classificação: **A VERIFICAR** (mesma classe de risco da SEC-001/027). Criticidade: **ALTA** se concatenados.
- Recomendação: mapear `campo` → nome de coluna por tabela fixa no servidor; `ordem` → `ASC|DESC` por comparação; listas com `cfqueryparam list="true"`.
- Esforço: médio. Prioridade: **2**.

---

**SEC-037 — Parâmetros refletidos em páginas de impressão/listagem e respostas inseridas com `.html()` (candidatos a XSS)**
- Evidência: `relatorio_nextel_print.cfm?nome=<encodeURI(nome)>` (RAMAIS `imprimir()`); `nprestadores_listar.cfm?...&razao=<razao>&mapa_pessoa=<erro>` (MAPA*); `nomePrestador` enviado a `adicionarPrestadoresMapa` e a resposta `data.MESSAGE` inserida via `$("#menItem").html(data.MESSAGE)`; `sSearch` do DataTables; ~120 pontos `.html(retorno)` por página com fragmentos HTML gerados pelo servidor a partir de campos de texto persistidos (seção 5.5); `simpleAutoComplete.js` insere resposta com `.html(r)`.
- Classificação: **A VERIFICAR** (codificação de saída não observável no DOM reserializado). Criticidade: **MÉDIA/ALTA** (sessões de coordenadores/diretoria).
- Recomendação: `encodeForHTML`/`encodeForHTMLAttribute`/`encodeForJavaScript` nos fragmentos; `scriptProtect="all"` no `Application.cfc` como mitigação (não substitui a codificação); revisar as páginas de impressão que recebem texto.
- Esforço: médio. Prioridade: **3**.

---

**SEC-038 — `eval` de respostas JSON em `ajaxfileupload.js` e JSON por concatenação em `serializeFormJson.js`**
- Evidência: `uploadHttpData`: `if (type == "json") eval("data = " + data);` — a resposta dos endpoints de upload é executada como JavaScript. `serializeToJson` monta `'"'+name+'":"'+value+'"'` sem escape.
- Classificação: **CONFIRMADO** quanto ao código; explorabilidade depende de o servidor refletir nome de arquivo/mensagem sem escape (**A VERIFICAR**).
- Criticidade: **MÉDIA**.
- Recomendação: substituir por `JSON.parse` e `FormData`/`fetch`; garantir `serializeJSON()` no servidor.
- Esforço: baixo. Prioridade: **3**.

---

**SEC-039 — Dados pessoais e sensíveis de negócio nas telas (contexto para LGPD e para SEC-025/026)**
- Evidência: RAMAIS.html: ~130 e-mails corporativos, ~45 telefones/celulares e nomes de colaboradores (relatório de ramais em uma única página de 200 KB, exportável em Excel); REL-PAGTO.html: ~2.000 CNPJ/CPF-like de prestadores com valores contratuais, medidos e pagos; DESPESA2.htm: fornecedores com CNPJ e valores por título; REL-NF.htm: favorecido (pessoa física), banco/agência/conta da empresa; MAPA3.html: preços negociados por prestador; CONTRATO.html: `codigo_iss`, `codigo_cno`, endereços e telefone de fiscal.
- Classificação: **CONFIRMADO** (presença). Criticidade: **INFORMATIVA** isoladamente; **ALTA** em conjunto com acesso indevido.
- Recomendação: classificar relatórios por sensibilidade; restringir exportações; minimizar CPF/CNPJ em listagens; logs de acesso a relatórios.
- Esforço: baixo/médio. Prioridade: **3**.

---

**SEC-040 — Plataforma e bibliotecas desatualizadas (extensão de SEC-021)**
- Evidência: seção 1.4 e 2.1 (jQuery 1.3.2/1.4.2/1.11.0/3.6.0; jQuery UI 1.10.2/1.13.1; DataTables 1.9.4/1.10.19; Bootstrap 3.1.1; CKEditor 4.10.1 + CKFinder 2; Highslide 4.1.13; scripts CF © 2012; driver JDBC 6.0.0.1282; Java 11; Tomcat 9; ColdFusion 2018/2021 por inferência).
- Classificação: **CONFIRMADO** quanto às versões; CVEs aplicáveis **A VERIFICAR** (não concluir só pela versão).
- Criticidade: **MÉDIA**.
- Recomendação: inventário e plano de atualização; remover bibliotecas não usadas (CKEditor/CKFinder aparentemente sem uso); consolidar jQuery em uma versão; confirmar nível de patch do ColdFusion e do Java (o CF 2018 encerrou suporte em 2023).
- Esforço: médio/alto. Prioridade: **3**.

---

**SEC-041 — Chamada externa a `viacep.com.br` a partir do navegador em `funcoes.js`**
- Evidência: `buscarEndereco(cep)` faz `fetch('https://viacep.com.br/ws/<cep>/json/')`. Também existem `../cep.cfm`/`../cep_municipio.cfm` no servidor (com referência a `buscacep.correios.com.br`).
- Classificação: **CONFIRMADO**. Criticidade: **BAIXA/INFORMATIVA** (dependência de terceiro; CSP e privacidade).
- Recomendação: centralizar consultas de CEP no servidor; documentar dependência.
- Esforço: baixo. Prioridade: **4**.

---

**SEC-042 — Callbacks que exibem sucesso sem interpretar a resposta (extensão do item 22 do baseline)**
- Evidência: `_medicoesExclui.cfm`, `_medicoesReprova.cfm`, `_medicaoEditaObs.cfm`, `_contratoEditaObs.cfm`, `_contratoReprova.cfm`, `_contratoReprovaAditivo.cfm`, `_contratoRetencaoEditar.cfm`, `_servicosQtdEdita.cfm`, `_req_materiais_itens_editar2.cfm`, `_req_materiais_reativar.cfm`, `_contrato_obras_coordenacao_aprova.cfm`, `_smapa_*` (vários), `romaneio_DAO.cfc apagarRomaneioDetalhe/baixarRomaneioDetalhe`.
- Classificação: **CONFIRMADO**. Criticidade: **BAIXA** (integridade de feedback e auditoria).
- Recomendação: padronizar resposta JSON `{ok, codigo, mensagem}` e tratá-la no cliente.
- Esforço: baixo. Prioridade: **4**.

---

**SEC-043 — Função global `apagarRegistro(id_pessoa)` em `funcoes.js` chama `pessoa_DAO.cfc?method=capagarPessoa` a partir de qualquer tela**
- Evidência: `funcoes.js` é carregado em 22 páginas; a função faz `$.post('cfcs/pessoa_DAO.cfc', {method:'capagarPessoa', id_pessoa})` (caminho relativo — funciona a partir do diretório `cadastro/`).
- Classificação: **CONFIRMADO** quanto à exposição no JS; autorização do método **A VERIFICAR**.
- Criticidade: **MÉDIA** (exclusão de pessoas/fornecedores).
- Recomendação: restringir o método a perfis administrativos no servidor e não distribuir a função globalmente.
- Esforço: baixo. Prioridade: **3**.

### 10.3 Controles positivos adicionais identificados nesta etapa

| ID | Controle | Evidência |
|---|---|---|
| CTRL-008 | Validações de negócio server-side em contratos (código duplicado, sem serviços, aditivo sem alteração, títulos baixados, bloqueio de cancelamento/exclusão) | retornos `1`, `-1`, `-7`, `-4` em CONTRATOS-EMP1/2 |
| CTRL-009 | Validações de datas e somatórios das medições de cliente (dentro da OS, soma ≤ OS, soma OS ≤ contrato) | `nmedicoes_valida_datas.cfm` `1/2/6`, `_nmedicoes_realizadas_inclui.cfm` `-4`, `_contrato_obras_editar.cfm` `8/-2` |
| CTRL-010 | Pré-requisitos de aprovação de requisição (itens, entregas, centro de custo, preço pendente) | `_req_aprovar.cfm` `2/3/4`, `_req_aprovar_lista_compras.cfm` `-9` |
| CTRL-011 | Remessa não confirma/aprova/baixa sem NF | `_nromaneio_*` `-1/-5` |
| CTRL-012 | Validação de extensão e tamanho de anexos | `_req_anexos_cadastrar.cfm` `1`; `_prestador_anexos.cfm` `1`, `-5/-10` |
| CTRL-013 | Verificação de planilha antes de faturar | `medicoes.cfc medicaoPlanilha`, `_nmedicoes_realizadas_fatura.cfm` `2` |
| CTRL-014 | Trilhas de histórico por objeto (medição, contrato, obra, requisição, realizado, mapa, remessa) | `popuphistorico*.cfm`, `smapa_historico.cfm`, `romaneio_DAO.cfc getHistorico` — conteúdo (usuário/IP/valores anteriores) **A VERIFICAR** |
| CTRL-015 | Verificação de existência de prestador por CNPJ | `mapaConcorrenciaF2.cfc existePrestador` |
| CTRL-016 | Sem identificadores de sessão em URLs | nenhum `CFID/CFTOKEN/JSESSIONID` em 33 páginas |
| CTRL-017 | Uso de HTTPS em todos os links absolutos | `https://sistema.almeidasapata.com.br` (3.072 ocorrências) |

### 10.4 Matriz consolidada (baseline + novos)

| ID | Achado | Evidência | Criticidade | Situação |
|---|---|---|---|---|
| SEC-001 | SQL concatenado (`pedido_DAO2.cfc GETPRINTORDER`) | dump | Alta | Confirmado (concatenação) |
| SEC-002 | Erros expostos | 3 dumps | Alta | Confirmado, sistêmico |
| SEC-003 | Endpoint direto de item de medição | JS | Informativo | Confirmado |
| SEC-004 | Dados derivados da medição enviados pelo cliente | hidden MEDIÇÕES2 | Alta se confiados | Indício forte |
| SEC-005 | Limite de quantidade no navegador | JS | Médio/Alto | Confirmado |
| SEC-006 | CFCs chamados diretamente | 20 CFCs / ~75 métodos | A definir | Confirmado |
| SEC-007 | Autorização de aprovação | — | Crítica/Alta | A verificar |
| SEC-008 | Valores financeiros na aprovação | `formMedicaoAprovar` | Alta se confiados | Indício forte |
| SEC-009 | Anti-duplicidade só no botão | JS | Médio | A verificar |
| SEC-010 | Autorização de exclusão | — | Alta | A verificar |
| SEC-011 | Autorização de reprovação | — | Alta | A verificar |
| SEC-012 | Texto persistido (obs) | HTML/JS | Médio/Alto | A verificar |
| SEC-013 | Relatórios com IDs | URLs | Alta | Indício forte (ver SEC-026) |
| SEC-014 | Autorização objeto a objeto | arquitetura | Crítica | A verificar — prioridade máxima |
| SEC-015 | CSRF | 33 páginas | Alta | Indício forte (ver SEC-033) |
| SEC-016 | Regras só no cliente | matriz seção 9 | Médio/Alto | Confirmado |
| SEC-017 | `eval` | JS | Baixa/Média | Confirmado |
| SEC-018 | IDs DOM duplicados | HTML | Média | Confirmado |
| SEC-019 | Concorrência | 9 módulos | Médio | A verificar |
| SEC-020 | Transação multi-item / TOCTOU | fluxos | Médio | A verificar |
| SEC-021 | Bibliotecas legadas | versões | Médio | Confirmado |
| SEC-022 | Sinks `.html()` | JS | Médio/Alto | A verificar |
| SEC-023 | `encodeURI` como tratamento | JS | Baixo | Confirmado |
| SEC-024 | POST não é controle | — | Informativo | Confirmado |
| **SEC-025** | **Autorização por `id_rotina` do cliente** | dumps + URLs | **Crítica se confirmada** | Indício forte |
| **SEC-026** | **Relatórios/impressão por GET só com ID, alguns sem checagem de rotina** | URLs + dump | Alta | Confirmado (padrão) / A verificar (autorização) |
| **SEC-027** | **SQL concatenado em `titulosPagarVer.cfm:14`** | dump SQL | Alta | Confirmado (concatenação) |
| **SEC-028** | **`cfdump` da exceção no handler global** | 3 dumps | Alta | Confirmado |
| **SEC-029** | **Recuperação de senha por GET, enumeração, senha enviada** | LOGIN.html | Alta | Confirmado / Indício forte |
| **SEC-030** | **Flags de papel/estado enviadas pelo cliente** | JS/hidden | Crítica se confiadas | Confirmado (envio) / A verificar |
| **SEC-031** | Valores financeiros do cliente (outros módulos) | JS | Alta se confiados | Indício forte |
| **SEC-032** | Alteração de estado via GET | JS | Média | Confirmado |
| **SEC-033** | Nenhum anti-CSRF observável | 33 páginas | Alta | Indício forte |
| **SEC-034** | `_cf_clientid` igual antes/depois do login | 3 páginas | Média | Indício |
| **SEC-035** | Upload/exclusão de anexos; `arquivo` do cliente | JS | Alta | Controle parcial / Indício forte |
| **SEC-036** | ORDER BY / listas dinâmicas | JS | Alta se concatenados | A verificar |
| **SEC-037** | Parâmetros refletidos / XSS | JS | Média/Alta | A verificar |
| **SEC-038** | `eval` em upload JSON | ajaxfileupload.js | Média | Confirmado (código) |
| **SEC-039** | PII e dados de negócio nas telas | HTML | Informativo/Alta | Confirmado |
| **SEC-040** | Plataforma/bibliotecas desatualizadas | versões | Média | Confirmado (versões) |
| **SEC-041** | Chamada externa viacep | funcoes.js | Baixa | Confirmado |
| **SEC-042** | Sucesso sem interpretar resposta | JS | Baixa | Confirmado |
| **SEC-043** | `capagarPessoa` exposto globalmente | funcoes.js | Média | Confirmado (exposição) |

---

## 11. O que precisa ser analisado em mais profundidade (próximas etapas)

Ordem sugerida (do maior para o menor impacto na conclusão final):

1. **`Application.cfc`** (onRequestStart/onRequest linha ~942, onError, onSessionStart): autenticação global, `sessionRotate`, CSRF, tratamento de erro, `scriptProtect`, configuração de cookies (`this.sessioncookie.httponly/secure/samesite`).
2. **`logon/_includeValidacao.cfm` e `logon/_verificaPermissoesRotina.cfm`** (linha 30): confirmar se a rotina verificada é a da requisição ou a da página (SEC-025) e como o vínculo usuário→rotina é consultado.
3. **`logon/login.cfm`, `logon/_enviarSenha.cfm`, `logon/logout.cfm`, `logon/senhasEdita.cfm`**: armazenamento de senha, rotação de sessão, bloqueio.
4. **Medições de serviço**: `_medicoesEdita.cfm`, `_medicoesAprova.cfm`, `_medicoesBaixa.cfm`, `_medicoesExclui.cfm`, `_medicoesReprova.cfm`, `_medicao_periodo_editar.cfm`, `_medicaoEditaObs.cfm`, `servico/cfcs/medicao_DAO.cfc` (`atualizarValoresRodape`), `medicao_avalia_percentual.cfm`, `_medicoes_prestador_avaliar.cfm` — responder às perguntas 2, 3 e 4 do baseline (origem dos valores, autorização, uso de `responsavel`).
5. **Medições de cliente** (`contrato/`): `_contrato_medicoes_previsto_aprova.cfm`, `_nmedicoes_*.cfm`, `_contrato_medicoes_realizadas_*.cfm`, `contrato/cfcs/medicoes.cfc` — uso dos parâmetros `coordenador`, `tipo`, `flag_faturamento`, `valor`, `reajuste`.
6. **Mapa de concorrência**: `mapaConcorrencia/cfcs/MapaConcorrenciaF2.cfc` (28 métodos, `idSituacaoLogado`, preços), `prestadoresDAO.cfc excluirAnexoPrestador` (parâmetro `arquivo`), `_prestador_anexos.cfm`, `_smapa_fase3_gerar_contrato.cfm`.
7. **SQL**: `suprimento/cfcs/pedido_DAO2.cfc` (GETPRINTORDER ~141), `financeiro/titulosPagarVer.cfm` (linha 14), todos os fragmentos de listagem que recebem `campo/ordem` (`*Lista2.cfm`, `*New2.cfm`, `relatorio/relatorioPagamentos_ajax.cfm`, `nromaneio_listar_ajax.cfm`), `req_materiais_editar.cfm` (`lista`), `_contrato_obras_editar.cfm` (`lstEngenheiros`).
8. **Páginas GET com ID** (SEC-026): `npedido_print.cfm`, `gerencial_pedido_observacao.cfm`, `titulosPagarVer.cfm`, `popupHistorico*.cfm`, `relatorio_dados_obra.cfm`, `nRomaneio_printer.cfm`, `printRequisicao.cfm`, `smapa_fase2_visualizar.cfm`, `anexoMemo*.cfm`, `relatorio_contrato_rel0*.cfm`, `relatorio_nextel_print.cfm`.
9. **Uploads/downloads**: os 5 endpoints de upload, os 4 de exclusão, o local físico dos anexos e como são servidos; existência do conector CKFinder.
10. **Auditoria**: conteúdo real das tabelas de histórico (`popuphistorico*`) — usuário, data/hora, IP, valor anterior/novo.
11. **Concorrência/transações**: uso de `cftransaction` e de `rowversion` nos DAOs de medição, aprovação, baixa e faturamento.
12. **Requisições/remessa**: `_req_aprovar.cfm`, `_req_materiais_reprovar2.cfm` (`valor` 1/0), `_nmateriais_incluir.cfm` (`nAprovado`), `romaneio_DAO.cfc`, `requisicao_DAO.cfc`.

---

## 12. Arquivos adicionais que aumentariam a confiabilidade da análise

| Prioridade | Arquivo / artefato | Motivo |
|---|---|---|
| 1 | `E:\sistemas\ASEng\Application.cfc` | sessão, autenticação, erro, CSRF, cookies |
| 1 | `logon\_includeValidacao.cfm`, `logon\_verificaPermissoesRotina.cfm`, `logon\login.cfm`, `logon\logout.cfm`, `logon\_enviarSenha.cfm`, `logon\senhasEdita.cfm` | SEC-025, SEC-029, SEC-034 |
| 1 | `servico\_medicoesEdita.cfm`, `_medicoesAprova.cfm`, `_medicoesBaixa.cfm`, `_medicoesExclui.cfm`, `_medicoesReprova.cfm`, `_medicao_periodo_editar.cfm`, `_medicaoEditaObs.cfm`, `servico\cfcs\medicao_DAO.cfc`, `medicao_avalia_percentual.cfm`, `_medicoes_prestador_avaliar.cfm` | perguntas 2–4 do baseline |
| 1 | `suprimento\cfcs\pedido_DAO2.cfc`, `financeiro\titulosPagarVer.cfm`, `suprimento\npedido_print.cfm` | SEC-001, SEC-027, SEC-026 |
| 2 | `contrato\_contrato_medicoes_*.cfm`, `contrato\_nmedicoes_*.cfm`, `contrato\cfcs\medicoes.cfc`, `contrato\cfcs\contratoObras.cfc`, `contrato\_contrato_obras_*.cfm` | SEC-030, SEC-031, SEC-032 |
| 2 | `mapaConcorrencia\cfcs\MapaConcorrenciaF2.cfc`, `mapaConcorrenciaF1.cfc`, `prestadoresDAO.cfc`, `_prestador_anexos.cfm`, `_smapa_fase3_gerar_contrato.cfm` | SEC-030, SEC-035 |
| 2 | `servico\_contrato*.cfm`, `_servicos*.cfm`, `_anexaContrato.cfm`, `_anexo_memoria_servico.cfm`, `_contratoAnexoApagar.cfm`, `_anexoMemoriaCalculoApagar.cfm` | contratos e anexos |
| 2 | `suprimento\_req_*.cfm`, `suprimento\cfcs\requisicao_DAO.cfc`, `romaneio_DAO.cfc`, `_nmateriais_incluir.cfm`, `_req_anexos_cadastrar.cfm` | requisições/remessa |
| 2 | Fragmentos de listagem com ordenação (`*Lista2.cfm`, `*New2.cfm`, `relatorio\relatorioPagamentos_ajax.cfm`, `nromaneio_listar_ajax.cfm`, `req_materiais_editar.cfm`) | SEC-036 |
| 2 | **Exportação HAR** de uma sessão completa (login → medição → aprovação → logout) | cabeçalhos, cookies (`Secure/HttpOnly/SameSite`), `Set-Cookie` no login, cabeçalhos de segurança, corpo real das respostas (`X-Requested-With`, `Origin`) |
| 2 | Tela `senhasEdita.cfm` (há `SENHA_files` sem HTML) e a terceira "TABELA" | troca de senha |
| 3 | CF Administrator: versão/patch do ColdFusion e do Java, "Robust Exception Information", configurações de sessão/cookies, datasources (permissões SQL do usuário `ASNOVO`) | SEC-028, SEC-040 |
| 3 | Estrutura do banco: tabelas de histórico/auditoria, colunas `rowversion`, constraints (`23000`) | CTRL-014, SEC-019 |
| 3 | `cfcs\geral.cfc`, `cfcs\pessoa_DAO.cfc`, `servico\cfcs\servico.cfc`, `contrato\cfcs\contrato.cfc` | métodos remotos de leitura (filtragem por usuário) e `capagarPessoa` |
| 3 | Configuração do servidor web frontal (AJP) e existência de `/ckfinder/` e `/CFIDE/` publicados | superfície de infraestrutura |
| 3 | Logs `exception.log`/`application.log` do ColdFusion de um dia típico | frequência real dos erros e dos parâmetros inesperados |

---

## 13. Conclusão desta etapa

Os dois lotes ampliaram a cobertura de 1 para 9 módulos e confirmaram o padrão arquitetural (`página de rotina → fragmentos → ações "_" → DAO/CFC`). As evidências mais relevantes adicionadas são: (1) a autorização por rotina lê `id_rotina` da própria requisição; (2) o handler global de exceções expõe o dump completo em três módulos; (3) uma segunda concatenação de SQL em página financeira; (4) papéis de usuário e situações de workflow trafegam como parâmetros do cliente em três módulos; (5) recuperação de senha por GET com enumeração e envio da senha. Nenhum desses itens foi testado ativamente e nenhum deve ser tratado como explorável antes da revisão do código-fonte listado na seção 12.
