# DIAGNÓSTICO FINAL DE SEGURANÇA — SISTEMA GERENCIAL (ColdFusion / SQL Server)

**Organização:** Almeida Sapata Engenharia
**Sistema:** `sistema.almeidasapata.com.br` (aplicação ColdFusion/CFML sobre SQL Server)
**Base da análise:** baseline de contexto (`00_baseline_contexto_tecnico.md`), lotes `AS.zip` e `AS2.zip` (33 páginas HTML salvas, scripts, 3 páginas de erro, 1 PDF) e a Etapa 1 (`01_etapa1_inventario_arquitetura_superficie.md`)
**Data:** 03/09/2026
**Natureza:** avaliação interna, autorizada, passiva e estática

Documentos anteriores desta série permanecem válidos como anexos de evidência. Este documento consolida as conclusões.

---

# PARTE I — RELATÓRIO EXECUTIVO PARA DIRETORIA

## 1. Objetivo da avaliação

Identificar, de forma preventiva, fragilidades de segurança no Sistema Gerencial que possam afetar a integridade das informações financeiras e contratuais, a confidencialidade de dados de obras, prestadores e fornecedores, e a rastreabilidade das operações, e propor um plano de correção viável, incremental e compatível com o sistema atual.

## 2. Escopo

A avaliação cobriu nove módulos do sistema: autenticação, medições de serviço (prestadores), contratos de serviço, relatórios de contrato e pagamentos, obras e medições de clientes, contratos comerciais, mapa de concorrência, requisições de materiais, remessas de notas fiscais, relatórios gerenciais/financeiros e cadastro de ramais.

**A avaliação foi realizada de forma passiva, por meio da análise dos arquivos, códigos e informações disponibilizados normalmente ao navegador e/ou fornecidos internamente para revisão. Não foram realizados testes de invasão, exploração de vulnerabilidades, tentativa de quebra de autenticação ou acesso a informações não autorizadas.**

O código-fonte do servidor (arquivos `.cfm`/`.cfc`), os cabeçalhos HTTP, os cookies e as configurações do servidor e do banco de dados **não** fizeram parte do material analisado. Por isso, parte das conclusões está classificada como "indício" ou "a verificar" e depende de uma revisão complementar do código no servidor (ver seção Limitações da Avaliação, ao final).

## 3. Resumo executivo

Foram consolidados **30 achados** e **17 controles positivos**. A classificação de evidência indica o grau de certeza; a criticidade indica o impacto potencial para a empresa caso o achado se confirme.

| Criticidade | Confirmados | Indícios fortes | A verificar | Total |
|---|---|---|---|---|
| Crítica | 0 | 2 | 1 | **3** |
| Alta | 4 | 4 | 1 | **9** |
| Média | 5 | 1 | 3 | **9** |
| Baixa | 5 | 0 | 0 | **5** |
| Informativa | 4 | 0 | 0 | **4** |
| **Total** | **18** | **7** | **5** | **30** |

Leitura recomendada da tabela:

- Nenhum achado **crítico** foi comprovado; os três itens críticos são hipóteses fortes sobre o controle de acesso que precisam ser confirmadas ou afastadas pela leitura de dois ou três arquivos do servidor.
- Os achados **altos confirmados** são de natureza estrutural e corrigíveis com esforço baixo a médio: exposição de detalhes técnicos em telas de erro, duas consultas ao banco que incorporam dados recebidos do navegador sem tratamento, e uma rotina de recuperação de senha que permite descobrir e-mails cadastrados e indica que a senha é enviada ao usuário.
- O sistema **possui** validações relevantes no servidor (limites de quantidade, coerência de datas, bloqueios de cancelamento, pré-requisitos de aprovação, verificação de anexos). Isso reduz o risco real e mostra que a base é aproveitável.

## 4. Principais riscos empresariais

| Dimensão | Risco | Base nas evidências |
|---|---|---|
| **Integridade financeira** | Valores de medição, retenção, desconto, imposto e total a pagar chegam ao servidor a partir do navegador; se o servidor os aceitar sem recalcular, um erro ou uso indevido pode alterar o valor pago a um prestador. | Campos ocultos e parâmetros nas telas de medição, contratos, mapa de concorrência e medições de cliente (indício forte; confiança do servidor a verificar). |
| **Integridade contratual** | Aprovações, reprovações, cancelamentos e exclusões de contratos, aditivos, medições e requisições dependem de decisões que, no navegador, são representadas por indicadores de papel ("coordenador", "engenheiro responsável") enviados pelo próprio cliente. | Comentários e parâmetros no código JavaScript de três módulos (indício forte). |
| **Confidencialidade** | Relatórios com CNPJ de fornecedores, valores pagos, dados bancários da empresa, preços negociados em cotações e dados de colaboradores são acessíveis por endereços que contêm apenas o número do registro. Se o servidor não verificar a quem o registro pertence, dados de outras obras ou setores podem ser visualizados. | Padrão confirmado nas URLs; verificação de posse a confirmar. |
| **Acesso indevido** | A permissão por "rotina" (menu) parece depender de um número enviado pelo navegador. Se isso se confirmar, um usuário poderia abrir telas de módulos que não lhe foram atribuídos informando uma rotina que possui. | Mensagem de erro do próprio sistema e uso da mesma tela com rotinas diferentes (indício forte). |
| **Disponibilidade** | Não há evidência de risco direto de indisponibilidade. As consultas que incorporam dados do navegador podem, em caso de uso indevido, causar erros e carga no banco. | Duas ocorrências confirmadas de consulta montada com dados do navegador. |
| **Rastreabilidade** | Existem históricos por objeto (medição, contrato, obra, requisição, remessa), o que é positivo. O conteúdo desses históricos (usuário, data, valor anterior e novo) não pôde ser verificado. Telas de erro expõem estrutura interna, o que facilita reconhecimento por terceiros. | Endpoints de histórico observados; dumps de erro confirmados. |
| **Risco operacional** | Regras de negócio importantes (total negativo, nota fiscal obrigatória na baixa, engenheiros obrigatórios na aprovação de obra) existem apenas no navegador; a integração planejada com Excel, que usará os mesmos endpoints, herdaria essa fragilidade. Bibliotecas de interface com mais de dez anos convivem com versões recentes. | Matriz de validação da Etapa 1 (confirmado). |

## 5. Principais fragilidades estruturais

Os achados individuais são manifestações de sete padrões, todos sustentados por evidências:

1. **Confiança excessiva no navegador.** O servidor recebe do cliente não só o que o usuário digitou, mas também preços, quantidades contratadas, totais, saldos, indicadores de papel e de estado do fluxo. Campos ocultos e constantes no JavaScript não são controles de segurança.
2. **Autorização descentralizada e dependente de parâmetro.** A checagem de rotina é feita por `include` em cada página e lê o identificador de rotina da requisição; páginas de impressão e popups aparentemente não passam por ela; a verificação "este usuário pode operar este contrato/obra/medição" não pôde ser identificada em nenhum arquivo.
3. **Ausência de parametrização consistente nas consultas.** As duas únicas amostras de erro de banco disponíveis mostram dados da requisição incorporados diretamente ao SQL. Parâmetros de ordenação e listas de identificadores seguem o mesmo caminho e precisam ser revisados.
4. **Exposição excessiva de erros.** O tratamento global de exceções entrega ao navegador o dump completo (caminhos físicos, linhas de código, consulta, datasource, versões).
5. **Dependência de validação client-side.** Uma parte relevante das regras de negócio só existe em JavaScript; o servidor cobre outra parte, mas de forma desigual entre módulos.
6. **Ausência de controles transacionais e de concorrência visíveis.** Validação e gravação ocorrem em requisições separadas; não há versão de registro; itens são gravados um a um.
7. **Legado sem camada central de segurança.** Não há token anti-CSRF, não há função central de autorização por objeto, o mecanismo de token do próprio ColdFusion está desativado (`_cf_ajaxproxytoken` vazio), operações de alteração são feitas por GET em alguns pontos, e a recuperação de senha indica armazenamento reversível.

## 6. Top 10 prioridades

| Prioridade | Achado | Risco | Impacto | Complexidade de correção | Prazo recomendado |
|---|---|---|---|---|---|
| 1 | SEC-025 — Autorização por rotina dependente de parâmetro do cliente | Acesso a módulos não atribuídos | Alto a crítico | Baixa (um arquivo central) | Imediato (confirmar e corrigir) |
| 2 | SEC-014 / SEC-026 — Autorização objeto a objeto não identificada; relatórios por GET só com ID | Leitura/alteração de dados de outras obras e contratos | Crítico | Média (função central + aplicação por endpoint) | 0–90 dias |
| 3 | SEC-030 — Indicadores de papel e estado enviados pelo cliente | Aprovação/alteração fora do perfil | Crítico | Média | 0–90 dias |
| 4 | SEC-002 — Dump completo de erros ao navegador | Reconhecimento técnico; suporte a outros ataques | Alto | Baixa | Imediato |
| 5 | SEC-001 / SEC-027 — Consultas com dados do navegador incorporados ao SQL | Alteração/leitura indevida do banco | Alto | Baixa por consulta; média para varredura | Imediato (2 pontos) e 30–90 dias (varredura) |
| 6 | SEC-029 — Recuperação de senha por GET, enumeração e envio da senha | Comprometimento de contas | Alto | Média | 0–60 dias |
| 7 | SEC-004 / SEC-008 / SEC-031 — Valores financeiros enviados pelo cliente | Fraude ou erro em pagamentos | Alto | Média | 30–90 dias |
| 8 | SEC-015 / SEC-033 / SEC-032 — Ausência de proteção anti-CSRF e alterações via GET | Ações executadas sem intenção do usuário | Alto | Média | 30–90 dias |
| 9 | SEC-035 — Uploads e exclusão de anexos com nome de arquivo vindo do cliente | Perda/alteração de documentos; conteúdo malicioso | Alto | Baixa a média | 0–60 dias |
| 10 | SEC-016 / SEC-019 — Regras só no cliente; sem transação/versionamento | Inconsistência de medições e aprovações | Médio | Média | 90–180 dias |

## 7. Plano de correção

### IMEDIATO (0–30 dias) — contenção e confirmação

1. **Tratamento de erro:** substituir o dump por mensagem genérica com código de rastreio; gravar o detalhe em log interno; confirmar no CF Administrator a desativação da exibição robusta de exceções.
2. **Parametrização dos dois pontos confirmados:** `pedido_DAO2.cfc` (função de impressão do pedido) e `financeiro/titulosPagarVer.cfm` (linha 14). Validar tipo dos identificadores antes da consulta.
3. **Revisão de `_verificaPermissoesRotina.cfm` e `Application.cfc`:** confirmar como a rotina é validada; se depender do parâmetro, passar a mapear página → rotina no servidor.
4. **Recuperação de senha:** trocar GET por POST, resposta uniforme (sem revelar se o e-mail existe), limitação de tentativas. Iniciar plano de migração para hash de senha.
5. **Operações via GET:** converter `_contratoReprovaAditivo.cfm` e `contratoObras.cfc setExecucaoObra` para POST; bloquear GET nos templates de ação.
6. **Exclusão de anexo:** `prestadoresDAO.cfc excluirAnexoPrestador` deve resolver o arquivo a partir do `id_anexo`, nunca do nome enviado.
7. **Sessão:** `SessionRotate()` após login, `SessionInvalidate()` no logout, cookies com `HttpOnly`, `Secure` e `SameSite`.
8. **Confirmar/afastar hipóteses críticas** lendo os arquivos listados na seção 12 da Etapa 1 (medições, aprovação, baixa, exclusão).

### CURTO PRAZO (30–90 dias) — camada central

1. **Função central de autorização por objeto** (`podeOperar(usuario, acao, tipoObjeto, id)`), chamada no início de cada endpoint `_*.cfm` e método CFC de escrita, começando por medições, aprovação, baixa, exclusão, contratos e relatórios/impressão.
2. **Papel e estado vindos da sessão e do banco:** ignorar `responsavel`, `coordenador`, `tipo`, `idSituacaoLogado`, `id_status`, `id_situacao`, `nAprovado` recebidos do cliente.
3. **Recálculo server-side de valores financeiros:** medição (`_medicoesEdita.cfm`, `medicao_DAO.cfc`), aprovação/baixa, mapa de concorrência, medições de cliente.
4. **Anti-CSRF:** token por sessão gerado no `Application.cfc` e verificado nos endpoints de escrita e nos métodos remotos; `SameSite=Lax`.
5. **Varredura de `cfquery`:** parametrizar `INSERT/UPDATE/DELETE` e consultas com parâmetros externos; mapear `campo/ordem` para colunas fixas; listas com `cfqueryparam list="true"`.
6. **Senhas:** armazenar com hash forte; fluxo de redefinição por token de uso único.

### MÉDIO PRAZO (90–180 dias) — consolidação

1. **Validação server-side completa** da matriz da Etapa 1 (total negativo, NF na baixa, engenheiros obrigatórios, quantidade > 0, preço acima do PC calculado no servidor).
2. **Transações e concorrência:** `cftransaction` nos fluxos de gravação; validação e gravação na mesma requisição; `rowversion` nas tabelas de medição, aprovação e baixa.
3. **Auditoria:** registro de usuário, data/hora, IP, ação, objeto, valor anterior e novo nas operações de alto impacto, e revisão do conteúdo dos históricos existentes.
4. **Codificação de saída** nos fragmentos HTML que exibem texto livre e nas páginas de impressão que recebem parâmetros.
5. **Higiene técnica:** consolidar jQuery em uma versão, remover CKEditor/CKFinder se não usados, substituir `eval`, corrigir IDs duplicados no DOM, padronizar respostas dos endpoints.
6. **Endpoint de lote para a integração Excel** que receba somente medição, item, quantidade e centro de custo, e recupere o restante do banco.

## 8. Conclusão executiva

O sistema **não precisa ser substituído** para tratar os riscos identificados. A arquitetura existente (páginas de rotina, fragmentos, ações e componentes de acesso a dados) permite introduzir uma **camada central de segurança** no `Application.cfc` e em poucos componentes compartilhados, sem alterar a experiência dos usuários.

As fragilidades de maior impacto concentram-se no controle de acesso e na confiança em dados do navegador; ambas podem ser mitigadas de forma incremental, tratando primeiro os endpoints de medição, aprovação, baixa, exclusão, contratos e relatórios, que são os de maior criticidade financeira e contratual.

Uma revisão progressiva, na ordem proposta, reduz significativamente o risco em 90 dias e permite que a integração com Excel seja construída sobre uma base validada no servidor. Nenhuma conclusão deste relatório afirma que o sistema foi ou pode ser comprometido; ela afirma que **há evidências de fragilidades relevantes** e que os controles correspondentes **não puderam ser identificados nos arquivos analisados**.

---

# PARTE II — RELATÓRIO TÉCNICO

Convenções: **Classificação** = CONFIRMADO / INDÍCIO FORTE / A VERIFICAR; **Criticidade** = impacto potencial caso o achado se confirme; **Probabilidade** = estimativa qualitativa com base na evidência disponível. Referências a linhas vêm das páginas de erro do próprio sistema. Nenhum exemplo contém instrução de exploração.

## Achados críticos

### SEC-025 — Autorização por rotina dependente do parâmetro `id_rotina` enviado pelo cliente
- **Classificação:** INDÍCIO FORTE
- **Criticidade:** CRÍTICA (se confirmada)
- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key), CWE-807 (Reliance on Untrusted Inputs in a Security Decision)
- **OWASP:** A01:2021 Broken Access Control
- **Arquivos:** `logon/_includeValidacao.cfm` (linha 4), `logon/_verificaPermissoesRotina.cfm` (linha 30), `Application.cfc` (linha 942); evidências em TABELA2.html, REL-CONT2.html, REL-NF.htm, MEDIÇÕES2.html, CONTRATO.html
- **Endpoints:** todas as páginas de rotina; exemplos com rotinas divergentes: `servico/relatorio_contrato_rel01.cfm?id_rotina=96`, `servico/relatorio_contrato_rel04.cfm?id_rotina=41|42`, `financeiro/titulosPagarVer.cfm?id_rotina=96`, `servico/anexoMemoriaCalculo*.cfm?id_rotina=38|41`, `contrato/contrato_medicao_faturamento.cfm?id_rotina=82`
- **Funções/métodos:** include de validação; JS `faturarPrevistoRealizadoCR()` fixa `id_rotina=82`
- **Parâmetros:** `id_rotina` (URL, hidden, constantes JS)
- **Descrição:** a checagem de permissão lê `ID_ROTINA` da requisição. O mesmo template é aberto com rotinas diferentes conforme o menu de origem, indicando que a validação é "o usuário possui a rotina informada" e não "a página pertence a uma rotina do usuário".
- **Evidência:** abrir `relatorio_tabela_rel01.cfm` sem `id_rotina` produziu "Variable ID_ROTINA is undefined" em `_verificaPermissoesRotina.cfm:30`; páginas do módulo financeiro abertas com a rotina do módulo gerencial; rotina fixada em JavaScript.
- **Causa raiz:** acoplamento entre o menu e o controle de acesso; identificador de autorização transportado pelo cliente.
- **Cenário de impacto:** um usuário autenticado com poucas rotinas informa uma rotina que possui ao abrir uma tela de outro módulo; se a validação for a hipotetizada, a tela é servida.
- **Impacto:** acesso vertical e horizontal a módulos financeiros, contratuais e de suprimentos.
- **Probabilidade:** média a alta (depende de uma linha de código).
- **Recomendação:** tabela `pagina → rotinas permitidas` no servidor; validar `CGI.SCRIPT_NAME` contra as rotinas do usuário em sessão; ignorar `id_rotina` para autorização; registrar negativas.
- **Exemplo seguro de correção:**
  ```cfml
  <!--- logon/_verificaPermissoesRotina.cfm --->
  <cfset paginaAtual = ListLast(CGI.SCRIPT_NAME, "/")>
  <cfquery name="qPerm" datasource="#application.dsn#">
    SELECT 1 FROM rotina_pagina rp
      JOIN usuario_rotina ur ON ur.id_rotina = rp.id_rotina
     WHERE rp.pagina = <cfqueryparam value="#paginaAtual#" cfsqltype="cf_sql_varchar">
       AND ur.id_usuario = <cfqueryparam value="#session.id_usuario#" cfsqltype="cf_sql_integer">
  </cfquery>
  <cfif NOT qPerm.recordCount>
    <cfset application.seguranca.registrarNegativa(session.id_usuario, paginaAtual, CGI.REMOTE_ADDR)>
    <cflocation url="/logon/semPermissao.cfm" addtoken="false">
  </cfif>
  ```
- **Esforço:** baixo. **Dependências:** inventário página → rotina. **Prioridade:** 1

### SEC-014 — Autorização objeto a objeto não identificada (consolida SEC-007, SEC-010, SEC-011, SEC-013)
- **Classificação:** A VERIFICAR NO CÓDIGO/SERVIDOR
- **Criticidade:** CRÍTICA (se ausente)
- **CWE:** CWE-639, CWE-862 (Missing Authorization)
- **OWASP:** A01:2021
- **Arquivos:** todos os endpoints `_*.cfm` e métodos CFC de escrita (Etapa 1, seções 4 e 8)
- **Endpoints (prioritários):** `_medicoesEdita.cfm`, `_medicoesAprova.cfm`, `_medicoesBaixa.cfm`, `_medicoesExclui.cfm`, `_medicoesReprova.cfm`, `_medicao_periodo_editar.cfm`, `_contratoAprova.cfm`, `_contratoExclui.cfm`, `_contratoCancela.cfm`, `_servicosEdita.cfm`, `_contrato_medicoes_*`, `_nmedicoes_*`, `MapaConcorrenciaF2.cfc`, `romaneio_DAO.cfc`, `requisicao_DAO.cfc`
- **Parâmetros:** `id_contrato`, `id_aditivo`, `id_medicao`, `id_obra`, `id_material`, `id_med`, `id_medRel`, `id_requisicao`, `id_smp`, `id_romaneio`, `id_anexo`, entre outros
- **Descrição:** o servidor recebe identificadores e, nos arquivos analisados, não há qualquer sinal de verificação "usuário → perfil → obra → contrato → medição → item". Botões condicionais no HTML não substituem essa verificação.
- **Evidência:** arquitetura observada em 9 módulos; ausência de qualquer parâmetro ou resposta indicativa de checagem de posse; contraste com validações de negócio que sim retornam códigos.
- **Causa raiz:** ausência de função central de autorização.
- **Cenário de impacto:** troca de identificador em uma requisição de gravação ou de relatório afetaria ou exporia registros de outra obra ou contrato, caso a verificação não exista.
- **Impacto:** integridade financeira e contratual; confidencialidade.
- **Probabilidade:** desconhecida (a verificar).
- **Recomendação:** componente `seguranca/autorizacao.cfc` com métodos `podeVerContrato`, `podeEditarMedicao`, `medicaoPertenceContrato`, `itemPertenceMedicao`, `medicaoEstaAberta`, invocado no topo de cada endpoint.
- **Exemplo seguro de correção:**
  ```cfml
  <!--- topo de _medicoesEdita.cfm --->
  <cfset auth = application.autorizacao>
  <cfif NOT auth.podeEditarMedicao(session.id_usuario, form.id_contrato, form.id_aditivo, form.id_medicao)
        OR NOT auth.itemPertenceMedicao(form.id_medicaott, form.id_medicao)>
    <cfheader statuscode="403"><cfoutput>-99</cfoutput><cfabort>
  </cfif>
  ```
- **Esforço:** médio. **Dependências:** modelo de perfis e vínculos usuário-obra. **Prioridade:** 1

### SEC-030 — Indicadores de papel e de estado de workflow enviados pelo cliente
- **Classificação:** INDÍCIO FORTE (envio CONFIRMADO; confiança do servidor a verificar)
- **Criticidade:** CRÍTICA (se confiados)
- **CWE:** CWE-602 (Client-Side Enforcement of Server-Side Security), CWE-807
- **OWASP:** A01:2021, A04:2021 Insecure Design
- **Arquivos:** MEDIÇÕES2.html, CONTRATO.html, MAPA/MAPA2/MAPA3.html, RMS1/RMS2.html
- **Endpoints:** `_medicoesAprova.cfm`, `medicao_avalia_percentual.cfm`, `medicao_DAO.cfc atualizarValoresRodape`; `_contrato_medicoes_previsto_aprova.cfm`, `_nmedicoes_previsto_edita.cfm`, `_nmedicoes_realizadas_inclui.cfm`, `_nmedicoes_realizadas_edita.cfm`, `_contrato_medicoes_previsto_cancela.cfm`; `MapaConcorrenciaF2.cfc adicionarPrestadoresMapa`, `excluirPrestadorMapa`, `salvandoRequisicaoEdicaoPrestador`; `_req_aprovar.cfm`, `_req_editar.cfm`, `_req_materiais_itens_*`, `_req_materiais_reprovar2.cfm`, `_nmateriais_incluir.cfm`
- **Funções/métodos:** `aprovacaoUltimaMedicao()`, `avaliarPrestador()`, `aprovarMedicaoPrevistoEncarregado()`, `aprovarMedicaoPrevistoCoordenador()`, `salvarPrevistoCoord()`, `addPrestadorMapa()`, `delPrestadorMapa()`, `atualizandoSituacaoRequisicao()`, `salvarMaterial()`, `reprovarRequisicaoMotivo()`
- **Parâmetros:** `responsavel` (hidden), `coordenador` (1/2), `tipo`, `vcoordenador`, `idSituacaoLogado=8` e `id_situacaoLogado=8` (constantes no JS), `id_status`, `id_situacao`, `req_tipo`, `nAprovado=1`, `valor` (1 cancela / 0 reprova)
- **Descrição:** o papel do usuário e o estado do fluxo trafegam como parâmetros. Comentários do próprio código: "1 quando for o coordenador e 2 quando for o engenheiro responsável"; "somente o engenheiro responsável pode aprovar a última medição".
- **Evidência:** valores literais no JavaScript e em campos ocultos (Etapa 1, seção 5.2).
- **Causa raiz:** decisão de autorização delegada à interface.
- **Cenário de impacto:** requisição com indicador de papel diferente do real; se o servidor o utilizar, a operação é executada com privilégio indevido (aprovação como coordenador, cadastro de material já aprovado, cancelamento em vez de reprovação).
- **Impacto:** integridade contratual e financeira; escalada de privilégio.
- **Probabilidade:** média (o padrão sugere uso server-side, mas não foi verificado).
- **Recomendação:** derivar papel de `session` e estado do banco; rejeitar os parâmetros; máquina de estados no servidor.
- **Exemplo seguro de correção:**
  ```cfml
  <cfset papel = application.autorizacao.papelNaObra(session.id_usuario, form.id_obra)> <!--- COORDENADOR | ENGENHEIRO | NENHUM --->
  <cfquery name="qEstado" datasource="#application.dsn#">
    SELECT id_status, id_situacao FROM requisicao
     WHERE id_requisicao = <cfqueryparam value="#form.id_requisicao#" cfsqltype="cf_sql_integer">
  </cfquery>
  <cfif NOT application.workflow.transicaoPermitida(qEstado.id_status, "APROVAR", papel)>
    <cfoutput>-99</cfoutput><cfabort>
  </cfif>
  ```
- **Esforço:** médio. **Dependências:** SEC-014. **Prioridade:** 1

## Achados altos

### SEC-001 — Entrada externa incorporada diretamente à instrução SQL (módulo de pedido)
- **Classificação:** CONFIRMADO (quanto à concatenação); explorabilidade A VERIFICAR
- **Criticidade:** ALTA
- **CWE:** CWE-89 (SQL Injection)
- **OWASP:** A03:2021 Injection
- **Arquivos:** `suprimento/cfcs/pedido_DAO2.cfc` (função `GETPRINTORDER`, linha ~141), `suprimento/npedido_print.cfm` (linha 4), `Application.cfc` (942)
- **Endpoint:** `suprimento/npedido_print.cfm?id_pedido=N` (GET)
- **Parâmetros:** `id_pedido`
- **Descrição:** o valor recebido apareceu literalmente em várias partes da consulta (CTEs e subconsultas) no dump de erro do baseline.
- **Evidência:** dump SQL do baseline (`WHERE PED.ID_PEDIDO = 124991,124992`).
- **Causa raiz:** interpolação `#...#` sem `cfqueryparam` e sem validação de tipo.
- **Cenário de impacto:** entrada não numérica altera a estrutura da consulta; conceitualmente, permite leitura ou alteração de dados além do pedido consultado.
- **Impacto:** confidencialidade e integridade do banco `ASNOVO`.
- **Probabilidade:** alta (a concatenação é certa; a explorabilidade depende de filtros não observados).
- **Recomendação:** `cfqueryparam` tipado; `cfparam type="integer"` na entrada.
- **Exemplo seguro de correção:**
  ```cfml
  <cfparam name="url.id_pedido" type="integer">
  <cfquery name="qPedido" datasource="#application.dsn#">
    ... WHERE PED.ID_PEDIDO = <cfqueryparam value="#url.id_pedido#" cfsqltype="cf_sql_integer"> ...
  </cfquery>
  ```
- **Esforço:** baixo. **Dependências:** nenhuma. **Prioridade:** 1

### SEC-027 — Entrada externa incorporada diretamente à instrução SQL (módulo financeiro)
- **Classificação:** CONFIRMADO (quanto à concatenação)
- **Criticidade:** ALTA
- **CWE:** CWE-89 · **OWASP:** A03:2021
- **Arquivos:** `financeiro/titulosPagarVer.cfm` (linha 14, tag `CFQUERY`); evidência REL-NF2.htm
- **Endpoint:** `financeiro/titulosPagarVer.cfm?id_Titulo=N&flag_origem=1&id_rotina=96` (GET)
- **Parâmetros:** `id_Titulo` (e possivelmente `flag_origem`)
- **Descrição:** valor vazio gerou erro de sintaxe do SQL Server ("Incorrect syntax near '='", código 102, datasource `ASNOVO`). Com parâmetro tipado, o ColdFusion rejeitaria o valor antes de enviar ao banco.
- **Evidência:** dump completo em REL-NF2.htm.
- **Causa raiz:** interpolação direta na cláusula `WHERE`.
- **Cenário de impacto:** idêntico ao SEC-001, em tabela de títulos a pagar (dados bancários e valores).
- **Impacto:** confidencialidade e integridade financeira.
- **Probabilidade:** alta.
- **Recomendação e exemplo:** como SEC-001, com `cf_sql_integer` para `id_Titulo` e `flag_origem`.
- **Esforço:** baixo. **Dependências:** nenhuma. **Prioridade:** 1

### SEC-002 — Exposição de detalhes internos em páginas de erro (consolida SEC-028)
- **Classificação:** CONFIRMADO
- **Criticidade:** ALTA
- **CWE:** CWE-209, CWE-497 · **OWASP:** A05:2021 Security Misconfiguration
- **Arquivos:** `Application.cfc` (handler de erro), PEDIDO.html, TABELA2.html, REL-NF2.htm, dump do baseline
- **Endpoints:** qualquer página que lance exceção
- **Descrição:** o handler global entrega um `cfdump` da exceção (`class="cfdump_struct"`): mensagem, SQL, `SQLState`, stack trace Java, `TagContext` com caminhos `E:\sistemas\ASEng\...` e linhas, datasource, versões de driver, Tomcat e Java.
- **Evidência:** três páginas de erro em três módulos.
- **Causa raiz:** `onError` (ou ausência dele) com saída de depuração em produção.
- **Cenário de impacto:** um terceiro obtém mapa da aplicação, estrutura do banco e pontos frágeis sem interação adicional.
- **Impacto:** reconhecimento; potencializa os demais achados.
- **Probabilidade:** alta (ocorre em uso normal).
- **Recomendação:** `onError` com mensagem genérica + `cflog`/tabela de erros com identificador; desativar "Robust Exception Information".
- **Exemplo seguro de correção:**
  ```cfml
  <cffunction name="onError" returntype="void">
    <cfargument name="exception" required="true">
    <cfargument name="eventName" type="string" required="true">
    <cfset var idErro = CreateUUID()>
    <cflog file="aseng_erros" type="error"
           text="#idErro# | #CGI.SCRIPT_NAME# | usuario=#(isDefined('session.id_usuario') ? session.id_usuario : 'anon')# | #arguments.exception.message# | #arguments.exception.detail#">
    <cfheader statuscode="500">
    <cfoutput>Não foi possível concluir a operação. Código: #idErro#</cfoutput>
  </cffunction>
  ```
- **Esforço:** baixo. **Dependências:** nenhuma. **Prioridade:** 1

### SEC-029 — Recuperação de senha sem autenticação, via GET, com enumeração de usuários e envio da senha
- **Classificação:** CONFIRMADO (GET, enumeração, mensagem); armazenamento reversível INDÍCIO FORTE
- **Criticidade:** ALTA
- **CWE:** CWE-640, CWE-204, CWE-598, CWE-257 · **OWASP:** A07:2021 Identification and Authentication Failures
- **Arquivos:** LOGIN.html (`logon/indexDes.cfm`); endpoint `logon/_enviarSenha.cfm`
- **Funções:** `lembrarSenha()`
- **Parâmetros:** `login` (e-mail)
- **Descrição:** retorno `1` = "O e-mail informado não existe no sistema"; `0` = "A senha foi enviada com sucesso". Sem CAPTCHA ou limitação observável.
- **Evidência:** código JavaScript da tela de login.
- **Causa raiz:** fluxo de recuperação que reenvia a credencial e diferencia respostas.
- **Cenário de impacto:** confirmação de e-mails válidos; envio repetido de senhas; a senha atual precisa estar recuperável no banco.
- **Impacto:** comprometimento de contas; exposição de credenciais em logs e e-mails.
- **Probabilidade:** alta para enumeração; média para o restante.
- **Recomendação:** POST, resposta uniforme, token de redefinição de uso único com expiração, hash de senha (bcrypt/argon2 via `GenerateBCryptHash`/`GenerateArgon2Hash` no CF 2021, ou biblioteca equivalente), limitação de taxa.
- **Exemplo seguro de correção:**
  ```cfml
  <!--- _enviarSenha.cfm --->
  <cfif CGI.REQUEST_METHOD NEQ "POST"><cfheader statuscode="405"><cfabort></cfif>
  <cfset token = Hash(CreateUUID() & GetTickCount(), "SHA-256")>
  <!--- grava token com validade de 30 min apenas se o e-mail existir; resposta é sempre a mesma --->
  <cfoutput>{"ok":true,"mensagem":"Se o e-mail estiver cadastrado, enviaremos instruções."}</cfoutput>
  ```
- **Esforço:** médio. **Dependências:** migração de senhas. **Prioridade:** 2

### SEC-004 — Valores financeiros e derivados enviados pelo cliente (consolida SEC-008, SEC-031)
- **Classificação:** INDÍCIO FORTE (envio CONFIRMADO; uso no servidor a verificar)
- **Criticidade:** ALTA
- **CWE:** CWE-602, CWE-20 · **OWASP:** A04:2021
- **Arquivos:** MEDIÇÕES2.html, CONTRATOS-EMP1/2.html, CONTRATO.html, MAPA3.html, REMESSA.htm
- **Endpoints:** `_medicoesEdita.cfm`, `medicao_DAO.cfc atualizarValoresRodape`, `_medicoesAprova.cfm`, `_medicoesBaixa.cfm`, `_contratoAlteraImposto.cfm`, `_contratoRetencaoEditar.cfm`, `_smapa_edit_material.cfm`, `MapaConcorrenciaF2.cfc adicionarPrestadoresMapa` e `prestadorAlterarPrecoNegociado`, `_nmedicoes_realizadas_*`
- **Funções:** `validandoDadosServicoMedicao()`, `atualizarValoreRodape()`, `aprovarMedicaoEdicao()`, `altImposto()`, `editarItem()`, `alterarPrecoNegociadoPrestador()`
- **Parâmetros derivados (deveriam vir do banco):** `preco`, `quantContrato`, `vlContrato`, `qtdAcu`, `acumuladoMedido`, `quantidadeAcumulada2`, `porcentAtual`, `valorNotaFiscal`, `totalPagar`, `vsaldoContrato`, `retencaoZero`, `mri_pc`, `imposto`, `acimaPreco`, `id_situacao`
- **Descrição:** o servidor recebe do navegador o contexto financeiro que ele próprio possui. Há controles server-side de quantidade (retornos 1 e 2), mas não se sabe se comparam com o banco ou com os valores enviados.
- **Evidência:** campos ocultos com valores como `preco=75.0000`, `vlContrato=2543.0816`, `totalPagar=1271.5408`.
- **Causa raiz:** interface que reenvia o estado como fonte de verdade.
- **Cenário de impacto:** requisição com valores derivados alterados; se aceitos, medição, retenção ou total a pagar ficam inconsistentes com o contrato.
- **Impacto:** integridade financeira; fraude.
- **Probabilidade:** média.
- **Recomendação:** endpoints aceitam somente `id` + valor informado pelo usuário; o restante é recarregado do banco e recalculado.
- **Exemplo seguro de correção:**
  ```cfml
  <cfquery name="qItem" datasource="#application.dsn#">
    SELECT preco, quant_contrato, acumulado_anterior FROM medicao_item
     WHERE id_medicaott = <cfqueryparam value="#form.id_medicaott#" cfsqltype="cf_sql_integer">
       AND id_medicao   = <cfqueryparam value="#form.id_medicao#"   cfsqltype="cf_sql_integer">
  </cfquery>
  <cfif (qItem.acumulado_anterior + val(form.quantMed)) GT qItem.quant_contrato><cfoutput>1</cfoutput><cfabort></cfif>
  <cfset valorItem = qItem.preco * val(form.quantMed)>  <!--- nunca form.preco --->
  ```
- **Esforço:** médio. **Dependências:** SEC-014. **Prioridade:** 2

### SEC-026 — Relatórios, impressões e popups acessíveis por GET apenas com o ID do objeto, alguns sem checagem de rotina
- **Classificação:** CONFIRMADO (padrão) / INDÍCIO FORTE (ausência de checagem de rotina em dois casos) / A VERIFICAR (posse do objeto)
- **Criticidade:** ALTA
- **CWE:** CWE-639, CWE-862 · **OWASP:** A01:2021
- **Arquivos/endpoints:** `suprimento/npedido_print.cfm?id_pedido`, `gerencial/gerencial_pedido_observacao.cfm?id_pedido` (REL-TIL renderizou sem `id_rotina`), `financeiro/titulosPagarVer.cfm?id_Titulo`, `contrato/popupHistoricoObra.cfm`, `contrato/popupHistoricoContrato.cfm`, `contrato/relatorio_dados_obra.cfm`, `contrato/contrato_empenhos_faturas.cfm`, `contrato/nmedicoes_lancamentos_relatorio.cfm?printer=1`, `suprimento/nRomaneio_printer.cfm`, `suprimento/printRequisicao.cfm`, `mapaConcorrencia/smapa_fase2_visualizar.cfm`, `servico/anexoMemo*.cfm`, `servico/relatorio_contrato_rel0*.cfm`, `cadastro/relatorio_nextel_print.cfm`
- **Parâmetros:** `id_pedido`, `id_Titulo`, `id_Obra`, `id_contrato`, `id_medRel`, `id_romaneio`, `id_requisicao`, `id_medicao`
- **Descrição:** dados de fornecedores, valores, conta bancária da empresa e preços de cotação identificados por sequencial na URL; `npedido_print.cfm` sem parâmetros falhou na linha 4 do próprio template e não na checagem de rotina.
- **Evidência:** URLs nas páginas DESPESA2, MEDIÇÕES, CONTRATO, RMS, REMESSA, MAPA; página REL-TIL.
- **Causa raiz:** páginas de saída fora do pipeline de validação; sem verificação de posse.
- **Cenário de impacto:** consulta de registros de outras obras por variação do identificador, caso não haja verificação.
- **Impacto:** confidencialidade (LGPD, dados bancários, preços).
- **Probabilidade:** média a alta.
- **Recomendação:** incluir validação de sessão, rotina e posse no topo; preferir POST para impressão; tokens de acesso temporários para documentos.
- **Exemplo seguro:** ver SEC-014 (mesma função central, método `podeVerObjeto("pedido", id)`).
- **Esforço:** médio. **Dependências:** SEC-014, SEC-025. **Prioridade:** 1

### SEC-015 — Proteção anti-CSRF não identificada (consolida SEC-033)
- **Classificação:** INDÍCIO FORTE
- **Criticidade:** ALTA
- **CWE:** CWE-352 · **OWASP:** A01:2021
- **Arquivos:** 33 páginas; `_cf_ajaxproxytoken:''` em CONTRATO.html
- **Endpoints:** todos os `_*.cfm` e métodos CFC de escrita; formulários clássicos (`formlogin`, `formPrintContrato`, `selmedicao`)
- **Descrição:** nenhum campo ou cabeçalho de token; o mecanismo nativo do CF Ajax está desativado. `SameSite` e verificação de `Origin` não são observáveis.
- **Evidência:** varredura completa dos HTML e JS.
- **Causa raiz:** ausência de camada central.
- **Cenário de impacto:** um usuário autenticado, ao visitar conteúdo de terceiros, dispara ação de gravação sem intenção (o navegador anexa o cookie de sessão).
- **Impacto:** integridade; combinado com SEC-032, o cenário exige apenas um link.
- **Probabilidade:** média (depende de `SameSite`).
- **Recomendação:** `CSRFGenerateToken()` no `onRequestStart` injetado nos formulários e no `$.ajaxSetup`; `CSRFVerifyToken()` nos endpoints de escrita; `SameSite=Lax`.
- **Exemplo seguro de correção:**
  ```cfml
  <!--- Application.cfc --->
  <cfset this.sessioncookie = { httponly = true, secure = true, samesite = "Lax" }>
  <cffunction name="onRequestStart">
    <cfif Left(ListLast(CGI.SCRIPT_NAME,"/"),1) EQ "_" OR CGI.REQUEST_METHOD EQ "POST">
      <cfif NOT structKeyExists(form, "csrf") OR NOT CSRFVerifyToken(form.csrf)>
        <cfheader statuscode="403"><cfabort>
      </cfif>
    </cfif>
  </cffunction>
  ```
  ```javascript
  // JS global: envia o token em todo AJAX
  $.ajaxSetup({ data: { csrf: window.CSRF_TOKEN } });
  ```
- **Esforço:** médio. **Dependências:** SEC-032. **Prioridade:** 2

### SEC-035 — Uploads com controles parciais e exclusão de anexo com nome de arquivo vindo do cliente
- **Classificação:** CONTROLE IDENTIFICADO (extensão/tamanho) + INDÍCIO FORTE (exclusão por nome) + A VERIFICAR (armazenamento e download)
- **Criticidade:** ALTA
- **CWE:** CWE-434, CWE-73 (External Control of File Name or Path), CWE-22 · **OWASP:** A01:2021, A04:2021
- **Arquivos:** ANEXO1.html, CONTRATOS-EMP2.html, RMS2.html, MAPA3.html, `ajaxfileupload.js`
- **Endpoints:** upload `_anexaContrato.cfm`, `_anexo_memoria_servico.cfm`, `_req_anexos_cadastrar.cfm`, `_prestador_anexos.cfm`, `anexoMemoriaCalculo.cfm`; exclusão `_contratoAnexoApagar.cfm`, `_anexoMemoriaCalculoApagar.cfm`, `_req_anexos_apagar.cfm`, **`prestadoresDAO.cfc excluirAnexoPrestador`**
- **Funções:** `uploadArquivo()`, `anexaContrato()`, `anexarArquivoReq()`, `excluirAnexo(id_anexo, arquivo)`
- **Parâmetros:** `anexo` (arquivo), `id_*`, **`arquivo`** (nome/caminho)
- **Descrição:** o servidor valida extensão (retorno 1) e tamanho (-5/-10 MB) em dois endpoints; a exclusão do anexo do prestador recebe o nome do arquivo do cliente.
- **Evidência:** códigos de retorno e assinatura da função no JS.
- **Causa raiz:** caminho físico derivado de entrada externa.
- **Cenário de impacto:** requisição de exclusão com nome diferente do esperado; se o servidor usar o nome recebido para apagar, arquivos de outros registros ou fora da pasta podem ser afetados.
- **Impacto:** integridade e disponibilidade de documentos contratuais.
- **Probabilidade:** média.
- **Recomendação:** resolver caminho exclusivamente por `id_anexo`; allowlist de extensões; renomear arquivos; gravar fora do webroot; servir via `cfcontent` com autorização; confirmar ausência do conector CKFinder publicado.
- **Exemplo seguro de correção:**
  ```cfml
  <cffunction name="excluirAnexoPrestador" access="remote" returnformat="json">
    <cfargument name="id_anexo" type="numeric" required="true">
    <cfquery name="qAnexo" datasource="#application.dsn#">
      SELECT nome_fisico FROM prestador_anexo
       WHERE id_anexo = <cfqueryparam value="#arguments.id_anexo#" cfsqltype="cf_sql_integer">
    </cfquery>
    <cfif qAnexo.recordCount AND application.autorizacao.podeEditarAnexo(session.id_usuario, arguments.id_anexo)>
      <cfset caminho = ExpandPath(application.pastaAnexos) & "/" & GetFileFromPath(qAnexo.nome_fisico)>
      <cfif FileExists(caminho)><cffile action="delete" file="#caminho#"></cfif>
    </cfif>
  </cffunction>
  ```
- **Esforço:** baixo a médio. **Dependências:** SEC-014. **Prioridade:** 2

### SEC-036 — Ordenação, paginação e listas de identificadores controladas pelo cliente
- **Classificação:** A VERIFICAR
- **Criticidade:** ALTA (se concatenados)
- **CWE:** CWE-89 · **OWASP:** A03:2021
- **Arquivos:** RMS1/RMS2, REL-PAGTO, REMESSA, CONTRATOS-EMP, MEDIÇÕES, CONTRATO, CLIENTE MEDIÇÕES, DESPESA
- **Endpoints:** `*Lista2.cfm`, `*New2.cfm`, `relatorio/relatorioPagamentos_ajax.cfm`, `nromaneio_listar_ajax.cfm`, `req_materiais_editar.cfm`, `req_materiais_itens_editar.cfm`, `_contrato_obras_editar.cfm`, relatórios com multiselect
- **Parâmetros:** `campo`, `ordem`, `novoCampo`, `novaOrdem`, `iSortCol_0`, `sSortDir_0`, `sSearch`, `lista`/`vlista` ("122199,122198,…"), `var_obras`, `obraID`, `idObras`, `lstEngenheiros`
- **Descrição:** ordenação e listas de IDs são construções que, em CFML legado, costumam ser concatenadas (`ORDER BY #campo#`, `IN (#lista#)`). O erro que originou a SEC-001 foi causado justamente por uma lista.
- **Evidência:** presença dos parâmetros; sem código para confirmar.
- **Causa raiz:** hipótese de concatenação (mesma da SEC-001/027).
- **Cenário de impacto:** idêntico ao SEC-001, em listagens com grande volume de dados.
- **Impacto:** confidencialidade e integridade.
- **Probabilidade:** média.
- **Recomendação:** mapa fixo de colunas; direção por comparação; `cfqueryparam list="true"`.
- **Exemplo seguro de correção:**
  ```cfml
  <cfset colunas = { "1" = "data_contrato", "2" = "num_contrato", "3" = "razao_social" }>
  <cfset colOrd = structKeyExists(colunas, form.campo) ? colunas[form.campo] : "data_contrato">
  <cfset dir = (form.ordem EQ 0) ? "DESC" : "ASC">
  <cfquery ...> ... WHERE id_requisicao IN (<cfqueryparam value="#form.lista#" cfsqltype="cf_sql_integer" list="true">)
    ORDER BY #colOrd# #dir# </cfquery>
  ```
- **Esforço:** médio. **Dependências:** nenhuma. **Prioridade:** 2

## Achados médios

### SEC-006 — Componentes CFC com métodos de escrita chamados diretamente pelo navegador
- **Classificação:** CONFIRMADO (exposição); autorização A VERIFICAR
- **Criticidade:** MÉDIA
- **CWE:** CWE-862 · **OWASP:** A01:2021
- **Arquivos:** 20 CFCs, ~75 métodos, ~45 de escrita (Etapa 1, seção 8)
- **Endpoints:** `medicao_DAO.cfc`, `medicoes.cfc`, `contratoObras.cfc`, `mapaConcorrenciaF1.cfc`, `MapaConcorrenciaF2.cfc`, `mapaConcorrenciaServicos.cfc`, `mapaConcorrenciaCotacao.cfc`, `prestadoresDAO.cfc`, `requisicao_DAO.cfc`, `romaneio_DAO.cfc`, `pessoa_DAO.cfc`
- **Parâmetros:** `method`, `returnformat`, `queryformat=column`, ids e valores
- **Descrição:** métodos `access="remote"` são invocados por URL; a autorização por objeto e por papel dentro deles não é observável.
- **Evidência:** chamadas `$.ajax`/`$.post` com `method=` (Etapa 1).
- **Causa raiz:** DAOs expostos como API sem fachada de segurança.
- **Cenário de impacto:** invocação direta de método de escrita fora da tela que o originou.
- **Impacto:** integridade.
- **Probabilidade:** média.
- **Recomendação:** `onCFCRequest` no `Application.cfc` aplicando sessão, CSRF e autorização antes de despachar; restringir `access="remote"` aos métodos realmente usados; DAOs internos com `access="package"`.
- **Exemplo seguro de correção:**
  ```cfml
  <cffunction name="onCFCRequest">
    <cfargument name="cfcname"><cfargument name="method"><cfargument name="args">
    <cfif NOT structKeyExists(session, "id_usuario")><cfheader statuscode="401"><cfabort></cfif>
    <cfif NOT application.autorizacao.podeChamar(session.id_usuario, arguments.cfcname, arguments.method, arguments.args)>
      <cfheader statuscode="403"><cfabort>
    </cfif>
    <cfinvoke component="#arguments.cfcname#" method="#arguments.method#" argumentcollection="#arguments.args#" returnvariable="r">
    <cfoutput>#serializeJSON(r)#</cfoutput>
  </cffunction>
  ```
- **Esforço:** médio. **Dependências:** SEC-014. **Prioridade:** 2

### SEC-032 — Operações que alteram estado executadas via GET
- **Classificação:** CONFIRMADO
- **Criticidade:** MÉDIA
- **CWE:** CWE-598, CWE-352 · **OWASP:** A01:2021
- **Arquivos:** CONTRATOS-EMP1/2.html, CONTRATO.html, LOGIN.html, PRINCIPAL.html
- **Endpoints:** `_contratoReprovaAditivo.cfm` (`type:'GET'`), `cfcs/contratoObras.cfc method=setExecucaoObra` (`$.ajax` sem `type`), `logon/_enviarSenha.cfm`, `logon/logout.cfm`
- **Funções:** `reprovandoContratoAditivo()`, handler de `flag_esconder`, `lembrarSenha()`
- **Parâmetros:** `reprova`, `id_contrato`, `id_aditivo`, `esconder`, `id_obra`, `login`
- **Descrição:** dados de decisão e credenciais trafegam na query string e são registrados em logs, histórico e `Referer`.
- **Evidência:** código JavaScript.
- **Causa raiz:** uso de GET por conveniência.
- **Cenário de impacto:** um link basta para disparar a ação (ver SEC-015).
- **Impacto:** integridade; vazamento em logs.
- **Probabilidade:** alta.
- **Recomendação:** POST em todos; bloquear GET em `_*.cfm` e métodos de escrita.
- **Exemplo seguro:** `<cfif CGI.REQUEST_METHOD NEQ "POST"><cfheader statuscode="405"><cfabort></cfif>` no `onRequestStart` para templates com prefixo `_`.
- **Esforço:** baixo. **Dependências:** nenhuma. **Prioridade:** 2

### SEC-016 — Regras de negócio relevantes existentes apenas no navegador (consolida SEC-005)
- **Classificação:** CONFIRMADO
- **Criticidade:** MÉDIA
- **CWE:** CWE-602 · **OWASP:** A04:2021
- **Arquivos:** MEDIÇÕES2, NOVO-CONTRATO, CONTRATO, RMS, MAPA3
- **Regras sem correspondente observado no servidor:** total a pagar negativo/zero, NF obrigatória na baixa, motivo de reprovação, engenheiros/fiscal/endereço obrigatórios na aprovação de obra, quantidade de item > 0, `acimaPreco` calculado no navegador, `id_material` inteiro
- **Descrição:** ver matriz completa na Etapa 1, seção 9.
- **Evidência:** funções JavaScript e callbacks que assumem sucesso.
- **Causa raiz:** validação de UX tratada como validação de negócio.
- **Cenário de impacto:** integração Excel ou requisição direta grava dados que a tela impediria.
- **Impacto:** integridade operacional e financeira.
- **Probabilidade:** alta (para a integração planejada).
- **Recomendação:** componente `validacao.cfc` com as mesmas regras, chamado pelos endpoints; respostas padronizadas.
- **Exemplo seguro:** `<cfif val(form.totalPagar_calculado) LT 0><cfoutput>-5</cfoutput><cfabort></cfif>` após o recálculo server-side (SEC-004).
- **Esforço:** médio. **Dependências:** SEC-004. **Prioridade:** 3

### SEC-012 — Texto persistido e parâmetros refletidos sem codificação de saída verificável (consolida SEC-022, SEC-037)
- **Classificação:** A VERIFICAR
- **Criticidade:** MÉDIA
- **CWE:** CWE-79 · **OWASP:** A03:2021
- **Arquivos:** todas as páginas com `.html(retorno)` (por exemplo 129 ocorrências em MAPA3, 94 em CONTRATO), RAMAIS, MAPA*, `simpleAutoComplete.js`
- **Endpoints:** fragmentos que exibem `observacao`, `obs`, `motivo`, `med_obs_memo`, `nomePrestador`; `relatorio_nextel_print.cfm?nome=`, `nprestadores_listar.cfm?razao=`, `sSearch`
- **Descrição:** dados de texto livre e parâmetros de URL são renderizados em HTML gerado pelo servidor; a codificação não pode ser verificada no DOM reserializado.
- **Evidência:** pontos de entrada e saída mapeados (Etapa 1, 5.5).
- **Causa raiz:** hipótese de `cfoutput` sem `encodeForHTML`.
- **Cenário de impacto:** texto salvo por um usuário é interpretado pelo navegador de outro (coordenador, diretoria).
- **Impacto:** sessões e ações em nome de usuários privilegiados.
- **Probabilidade:** média.
- **Recomendação:** `encodeForHTML`, `encodeForHTMLAttribute`, `encodeForJavaScript`, `encodeForURL` na saída; `scriptProtect="all"` como mitigação secundária.
- **Exemplo seguro:** `<td>#encodeForHTML(qMed.med_obs_memo)#</td>` e `<input value="#encodeForHTMLAttribute(qMed.obs)#">`.
- **Esforço:** médio. **Dependências:** nenhuma. **Prioridade:** 3

### SEC-034 — Identificador de cliente do CF Ajax idêntico antes e depois da autenticação
- **Classificação:** INDÍCIO
- **Criticidade:** MÉDIA
- **CWE:** CWE-384 (Session Fixation) · **OWASP:** A07:2021
- **Arquivos:** LOGIN.html, CONTRATO.html, CONTRATOS-EMP2.html (`_cf_clientid='C3912D25…A7DB'`)
- **Descrição:** o mesmo identificador de sessão do CF Ajax aparece na tela de login e em telas autenticadas, o que indica que a sessão não é rotacionada no login. Ressalva: a tela de login pode ter sido salva após navegação autenticada.
- **Causa raiz:** ausência de `SessionRotate()`.
- **Cenário de impacto:** sessão preparada antes do login permanece válida depois.
- **Impacto:** sequestro de sessão em cenários específicos.
- **Probabilidade:** baixa a média.
- **Recomendação:** `SessionRotate()` após autenticação; `SessionInvalidate()` no logout; cookies `HttpOnly`/`Secure`/`SameSite`; timeout de sessão adequado.
- **Exemplo seguro:** `<cfif autenticado><cfset SessionRotate()><cfset session.id_usuario = qUser.id_usuario></cfif>`
- **Esforço:** baixo. **Dependências:** nenhuma. **Prioridade:** 2

### SEC-019 — Ausência de controles de concorrência e transação observáveis (consolida SEC-009, SEC-020)
- **Classificação:** A VERIFICAR
- **Criticidade:** MÉDIA
- **CWE:** CWE-362, CWE-367 (TOCTOU) · **OWASP:** A04:2021
- **Arquivos:** todos os formulários dos 9 módulos (nenhum campo de versão); CONTRATO.html, CONTRATOS-EMP2.html, MEDIÇÕES1.html
- **Endpoints:** `nmedicoes_valida_datas.cfm` → `_nmedicoes_previsto_edita.cfm`; `servicoIncluirAditivoVerMedicao.cfm` → `_servicosExclui.cfm`; `_medicoesEdita.cfm` item a item; `_medicoesBaixa.cfm` (anti-duplo clique só no botão)
- **Descrição:** validação e gravação em requisições distintas; itens gravados individualmente; sem `rowversion`.
- **Causa raiz:** ausência de `cftransaction` e de bloqueio otimista.
- **Cenário de impacto:** dois usuários alteram o mesmo item; baixa em duplicidade em caso de reenvio; validação satisfeita e estado alterado entre as requisições.
- **Impacto:** integridade de medições e pagamentos.
- **Probabilidade:** média.
- **Recomendação:** validação e gravação na mesma requisição, dentro de `cftransaction`; `rowversion` comparado na atualização; idempotência na baixa.
- **Exemplo seguro de correção:**
  ```cfml
  <cftransaction>
    <cfquery name="qUpd" datasource="#application.dsn#" result="r">
      UPDATE medicao SET status = 'BAIXADA', nf = <cfqueryparam value="#form.vNumNF#" cfsqltype="cf_sql_varchar">
       WHERE id_medicao = <cfqueryparam value="#form.id_medicao#" cfsqltype="cf_sql_integer">
         AND status = 'APROVADA'
         AND rowversion = <cfqueryparam value="#form.rowversion#" cfsqltype="cf_sql_binary">
    </cfquery>
    <cfif r.recordCount EQ 0><cftransaction action="rollback"><cfoutput>-8</cfoutput><cfabort></cfif>
  </cftransaction>
  ```
- **Esforço:** médio. **Dependências:** alteração de esquema. **Prioridade:** 3

### SEC-021 — Plataforma e bibliotecas desatualizadas (consolida SEC-040)
- **Classificação:** CONFIRMADO (versões); CVEs aplicáveis A VERIFICAR
- **Criticidade:** MÉDIA
- **CWE:** CWE-1104 · **OWASP:** A06:2021 Vulnerable and Outdated Components
- **Arquivos:** `*_files/` (jQuery 1.3.2/1.4.2/1.11.0/3.6.0; jQuery UI 1.10.2/1.13.1; DataTables 1.9.4/1.10.19; Bootstrap 3.1.1; CKEditor 4.10.1; CKFinder 2; Highslide 4.1.13; scripts CF © 2012); páginas de erro (driver JDBC 6.0.0.1282, Java 11, Tomcat 9, CF 2018/2021 por inferência)
- **Descrição:** coexistência de gerações; CKEditor/CKFinder carregados em 13 páginas sem uso observado.
- **Causa raiz:** evolução incremental sem gestão de dependências.
- **Cenário de impacto:** falhas conhecidas em bibliotecas de interface ou no servidor de aplicação.
- **Impacto:** variável.
- **Probabilidade:** desconhecida (não concluir só pela versão).
- **Recomendação:** confirmar nível de patch do CF/Java; consolidar jQuery; remover o que não é usado; SCA periódica.
- **Esforço:** médio a alto. **Dependências:** testes de regressão. **Prioridade:** 3

### SEC-043 — Função de exclusão de pessoa distribuída em todas as telas
- **Classificação:** CONFIRMADO (exposição); autorização A VERIFICAR
- **Criticidade:** MÉDIA
- **CWE:** CWE-862 · **OWASP:** A01:2021
- **Arquivos:** `funcoes.js` (22 páginas)
- **Endpoint:** `cfcs/pessoa_DAO.cfc?method=capagarPessoa` · **Função:** `apagarRegistro(id_pessoa)` · **Parâmetro:** `id_pessoa`
- **Descrição:** função global que exclui pessoa/fornecedor, com regras de bloqueio (1 ativo no Flex, 2 obras/títulos pendentes).
- **Causa raiz:** script compartilhado sem segregação por módulo.
- **Cenário de impacto:** chamada do método a partir de qualquer tela; efeito depende da autorização interna.
- **Impacto:** integridade cadastral.
- **Probabilidade:** média.
- **Recomendação:** restringir por perfil no servidor (SEC-006); mover a função para o módulo de cadastro.
- **Esforço:** baixo. **Dependências:** SEC-006. **Prioridade:** 3

### SEC-044 — Conteúdo da auditoria não verificável
- **Classificação:** A VERIFICAR (existência de histórico: CONTROLE IDENTIFICADO)
- **Criticidade:** MÉDIA
- **CWE:** CWE-778 (Insufficient Logging) · **OWASP:** A09:2021 Security Logging and Monitoring Failures
- **Arquivos/endpoints:** `popuphistoricomedicao.cfm`, `popuphistoricocontrato.cfm`, `popupHistoricoObra.cfm`, `popupHistoricoRequisicao.cfm`, `popupHistoricoRealizada.cfm`, `smapa_historico.cfm`, `romaneio_DAO.cfc getHistorico`
- **Descrição:** existem trilhas por objeto, mas não foi possível verificar se registram usuário, data/hora, IP, valor anterior e novo, nem se cobrem exclusões e alterações financeiras.
- **Cenário de impacto:** alteração financeira sem rastro suficiente para investigação.
- **Impacto:** rastreabilidade.
- **Probabilidade:** desconhecida.
- **Recomendação:** tabela de auditoria única (usuário, data/hora, IP, sessão, ação, objeto, valor anterior, valor novo, motivo, resultado) alimentada pela camada central; retenção definida.
- **Exemplo seguro:** `application.auditoria.registrar(session.id_usuario, CGI.REMOTE_ADDR, "MEDICAO_BAIXA", form.id_medicao, antes, depois)` chamado após cada gravação.
- **Esforço:** médio. **Dependências:** camada central. **Prioridade:** 3

## Achados baixos

### SEC-038 — `eval` de respostas JSON em `ajaxfileupload.js` e JSON por concatenação
- **Classificação:** CONFIRMADO (código); explorabilidade A VERIFICAR · **Criticidade:** BAIXA · **CWE:** CWE-95 · **OWASP:** A03:2021
- **Arquivos:** `ajaxfileupload.js` (`uploadHttpData`), `serializeFormJson.js`
- **Descrição:** respostas de upload são executadas como JavaScript; JSON montado por concatenação quebra com aspas.
- **Recomendação:** `JSON.parse`, `FormData`/`fetch`, `serializeJSON()` no servidor. **Esforço:** baixo. **Prioridade:** 4

### SEC-017 — Uso de `eval()` para converter números
- **Classificação:** CONFIRMADO · **Criticidade:** BAIXA · **CWE:** CWE-95
- **Arquivos:** MEDIÇÕES2.html (`validandoDadosServicoMedicao`: `quantidadeAcumulada2`, `qtdMedidaAnterior`, `quantContrato`)
- **Recomendação:** `parseFloat` com validação. **Esforço:** baixo. **Prioridade:** 4

### SEC-018 — Identificadores duplicados no DOM
- **Classificação:** CONFIRMADO · **Criticidade:** BAIXA · **CWE:** n/a
- **Arquivos:** MEDIÇÕES2 (`medicaoEdita` ×6), CONTRATO (`CFForm_1` ×2), CLIENTE MEDIÇÕES (56 formulários com nomes repetidos), `id_contrato`/`id_obra` repetidos
- **Impacto:** seletores capturam o primeiro elemento; risco de gravação em contexto errado.
- **Recomendação:** IDs únicos, `data-*`, seletores relativos à linha. **Esforço:** médio. **Prioridade:** 4

### SEC-042 — Callbacks exibem sucesso sem interpretar a resposta
- **Classificação:** CONFIRMADO · **Criticidade:** BAIXA · **CWE:** CWE-754
- **Endpoints:** `_medicoesExclui.cfm`, `_medicoesReprova.cfm`, `_medicaoEditaObs.cfm`, `_contratoEditaObs.cfm`, `_contratoReprova.cfm`, `_contratoRetencaoEditar.cfm`, `_servicosQtdEdita.cfm`, `_req_materiais_itens_editar2.cfm`, `_contrato_obras_coordenacao_aprova.cfm`, vários `_smapa_*`, `romaneio_DAO.cfc`
- **Recomendação:** resposta JSON `{ok, codigo, mensagem}` tratada no cliente. **Esforço:** baixo. **Prioridade:** 4

### SEC-023 — `encodeURI` usado como aparente tratamento de entrada
- **Classificação:** CONFIRMADO · **Criticidade:** BAIXA · **CWE:** CWE-116
- **Arquivos:** MEDIÇÕES2 (`obs_reprovar`), RAMAIS (`imprimir()`)
- **Recomendação:** tratar no servidor e na saída. **Esforço:** baixo. **Prioridade:** 4

## Achados informativos

### SEC-039 — Dados pessoais e sensíveis de negócio concentrados em telas exportáveis
- **Classificação:** CONFIRMADO · **Criticidade:** INFORMATIVA (ALTA em conjunto com SEC-025/026) · **CWE:** CWE-200
- **Arquivos:** RAMAIS (~130 e-mails, ~45 telefones), REL-PAGTO (~2.000 CNPJ/CPF-like com valores), DESPESA2 (CNPJ e títulos), REL-NF (favorecido e conta bancária da empresa), MAPA3 (preços negociados), CONTRATO (`codigo_iss`, `codigo_cno`)
- **Recomendação:** classificação por sensibilidade, restrição de exportação, minimização. **Prioridade:** 3

### SEC-041 — Chamada externa a `viacep.com.br` a partir do navegador
- **Classificação:** CONFIRMADO · **Criticidade:** INFORMATIVA · **Arquivo:** `funcoes.js` (`buscarEndereco`)
- **Recomendação:** centralizar no servidor (já existem `cep.cfm`/`cep_municipio.cfm`). **Prioridade:** 4

### SEC-003 — Endpoint direto de atualização de item de medição
- **Classificação:** CONFIRMADO · **Criticidade:** INFORMATIVA (arquitetural)
- **Descrição:** o botão Salvar envia AJAX diretamente a `_medicoesEdita.cfm`; é a base da integração Excel planejada e o principal motivo para a camada central. **Prioridade:** n/a

### SEC-024 — Uso de POST não constitui controle de segurança
- **Classificação:** CONFIRMADO · **Criticidade:** INFORMATIVA
- **Descrição:** operações sensíveis usam POST corretamente, exceto os casos da SEC-032; POST não substitui autenticação, autorização, CSRF, validação e auditoria. **Prioridade:** n/a

## Controles positivos identificados

| ID | Controle | Evidência |
|---|---|---|
| CTRL-001/002 | Limite de quantidade e acumulado na medição | `_medicoesEdita.cfm` retornos `1`, `2` |
| CTRL-003 | Centro de custo obrigatório antes de aprovar/baixar | `_medicoesAprova.cfm`, `_medicoesBaixa.cfm` `-1` |
| CTRL-004 | Validação cronológica do período da medição | `_medicao_periodo_editar.cfm` `-1,-2,-3,-6` |
| CTRL-005 | Avaliação de prestador duplicada bloqueada | `_medicoes_prestador_avaliar.cfm` `23000` |
| CTRL-006/007 | Confirmações e anti-duplo clique (UX) | JavaScript |
| CTRL-008 | Regras de contratos (duplicidade, sem serviços, aditivo sem alteração, títulos baixados, bloqueio de cancelamento) | `1`, `-1`, `-7`, `-4` |
| CTRL-009 | Datas e somatórios das medições de cliente | `1/2/6`, `-4`, `8/-2` |
| CTRL-010 | Pré-requisitos de aprovação de requisição | `2/3/4`, `-9` |
| CTRL-011 | Remessa sem NF não avança | `-1/-5` |
| CTRL-012 | Extensão e tamanho de anexos | `1`, `-5/-10` |
| CTRL-013 | Planilha obrigatória para faturar | `medicaoPlanilha`, `2` |
| CTRL-014 | Históricos por objeto | `popuphistorico*`, `getHistorico` |
| CTRL-015 | Verificação de CNPJ existente | `existePrestador` |
| CTRL-016 | Sem identificadores de sessão em URL | 33 páginas |
| CTRL-017 | HTTPS em todos os links | 3.072 ocorrências |

## MATRIZ FINAL

| ID | Achado | Módulo | Evidência | Criticidade | Impacto | Correção | Esforço |
|---|---|---|---|---|---|---|---|
| SEC-025 | Autorização por `id_rotina` do cliente | transversal (logon) | Indício forte | Crítica | Acesso a módulos não atribuídos | Mapear página→rotina no servidor | Baixo |
| SEC-014 | Autorização objeto a objeto não identificada | transversal | A verificar | Crítica | Dados de outras obras/contratos | Função central `podeOperar` | Médio |
| SEC-030 | Papel/estado enviados pelo cliente | medições, contrato, mapa, suprimento | Indício forte | Crítica | Aprovação fora do perfil | Papel da sessão, estado do banco | Médio |
| SEC-001 | SQL concatenado (pedido) | suprimento | Confirmado | Alta | Banco `ASNOVO` | `cfqueryparam` | Baixo |
| SEC-027 | SQL concatenado (financeiro) | financeiro | Confirmado | Alta | Títulos a pagar | `cfqueryparam` | Baixo |
| SEC-002 | Dump de erros ao navegador | transversal | Confirmado | Alta | Reconhecimento | `onError` genérico + log | Baixo |
| SEC-029 | Recuperação de senha (GET, enumeração, senha enviada) | logon | Confirmado | Alta | Contas | Token de redefinição, hash, POST | Médio |
| SEC-004 | Valores financeiros do cliente | medições, contratos, mapa, cliente | Indício forte | Alta | Pagamentos | Recálculo server-side | Médio |
| SEC-026 | Relatórios GET só com ID | vários | Indício forte | Alta | Confidencialidade | Validação de posse | Médio |
| SEC-015 | Anti-CSRF não identificado | transversal | Indício forte | Alta | Ações não intencionais | Token CSRF + SameSite | Médio |
| SEC-035 | Anexos: exclusão por nome de arquivo | mapa, contratos, requisições | Indício forte | Alta | Documentos | Caminho por `id_anexo` | Baixo/Médio |
| SEC-036 | ORDER BY / listas dinâmicas | listagens | A verificar | Alta | Banco | Mapa de colunas, `list="true"` | Médio |
| SEC-006 | CFCs de escrita expostos | 11 CFCs | Confirmado (exposição) | Média | Integridade | `onCFCRequest` central | Médio |
| SEC-032 | Alteração de estado via GET | contratos, obras, logon | Confirmado | Média | CSRF/logs | POST obrigatório | Baixo |
| SEC-016 | Regras só no cliente | medições, contratos, obras, requisições | Confirmado | Média | Dados inválidos | `validacao.cfc` | Médio |
| SEC-012 | Codificação de saída não verificável | transversal | A verificar | Média | XSS | `encodeFor*` | Médio |
| SEC-034 | Sessão não rotacionada no login | logon | Indício | Média | Sessão | `SessionRotate()` | Baixo |
| SEC-019 | Concorrência/transação | medições, contratos, cliente | A verificar | Média | Inconsistência | `cftransaction`, `rowversion` | Médio |
| SEC-021 | Plataforma/bibliotecas desatualizadas | transversal | Confirmado (versões) | Média | Variável | Atualização/consolidação | Médio/Alto |
| SEC-043 | `capagarPessoa` global | cadastro | Confirmado (exposição) | Média | Cadastro | Restrição por perfil | Baixo |
| SEC-044 | Auditoria não verificável | transversal | A verificar | Média | Rastreabilidade | Tabela de auditoria central | Médio |
| SEC-038 | `eval` em upload JSON | JS compartilhado | Confirmado | Baixa | XSS potencial | `JSON.parse` | Baixo |
| SEC-017 | `eval` numérico | medições | Confirmado | Baixa | Robustez | `parseFloat` | Baixo |
| SEC-018 | IDs DOM duplicados | várias | Confirmado | Baixa | Contexto errado | IDs únicos | Médio |
| SEC-042 | Sucesso sem interpretar resposta | várias | Confirmado | Baixa | Feedback | Resposta padronizada | Baixo |
| SEC-023 | `encodeURI` como tratamento | medições, ramais | Confirmado | Baixa | — | Tratar no servidor | Baixo |
| SEC-039 | PII em telas exportáveis | ramais, relatórios | Confirmado | Informativa | LGPD | Classificação/restrição | Baixo |
| SEC-041 | Chamada externa viacep | JS compartilhado | Confirmado | Informativa | Dependência | Centralizar | Baixo |
| SEC-003 | Endpoint direto de item | medições | Confirmado | Informativa | Arquitetural | Camada central | — |
| SEC-024 | POST não é controle | transversal | Confirmado | Informativa | — | — | — |

## MAPA DE CORREÇÃO ARQUITETURAL

### Arquitetura-alvo (incremental)

```
INTERFACE
HTML / JavaScript / Excel / integrações
        ↓  (POST + token CSRF; envia apenas ids e valores digitados)
CAMADA DE AUTENTICAÇÃO           Application.cfc: onSessionStart, onRequestStart
        ↓                        sessão rotacionada no login, cookies HttpOnly/Secure/SameSite, timeout
CAMADA CENTRAL DE AUTORIZAÇÃO    seguranca/autorizacao.cfc: rotina por página, papel por obra, posse do objeto
        ↓                        onRequestStart (páginas/_*.cfm) e onCFCRequest (métodos remotos)
CAMADA CENTRAL DE VALIDAÇÃO      seguranca/validacao.cfc: tipos, obrigatoriedade, limites, estados permitidos
        ↓
REGRAS DE NEGÓCIO                recálculo de totais, máquina de estados, transação por operação
        ↓
DAO COM CONSULTAS PARAMETRIZADAS *_DAO.cfc com cfqueryparam, colunas de ordenação mapeadas, access="package"
        ↓
BANCO DE DADOS                   SQL Server ASNOVO: rowversion, constraints, tabela de auditoria
```

### Como adaptar o legado progressivamente

1. **Fase 0 (sem mudar telas):** `Application.cfc` ganha `onError` seguro, bloqueio de GET em `_*.cfm`, `SessionRotate`, cookies seguros, `onCFCRequest` com exigência de sessão. Nenhum endpoint precisa ser alterado.
2. **Fase 1 (wrappers):** criar `autorizacao.cfc`, `validacao.cfc` e `auditoria.cfc` em `application`. Inserir uma chamada no topo dos endpoints críticos (medição, aprovação, baixa, exclusão, contratos, relatórios). O corpo legado permanece.
3. **Fase 2 (contexto do banco):** nos mesmos endpoints, substituir o uso de `form.preco`, `form.quantContrato`, `form.responsavel`, `form.coordenador` etc. por consultas ao banco e à sessão. As telas continuam enviando os campos, que passam a ser ignorados; depois são removidos.
4. **Fase 3 (parametrização):** varredura de `cfquery` por módulo, começando pelos DAOs de escrita e pelas listagens com `campo/ordem`.
5. **Fase 4 (transação e auditoria):** `cftransaction` e `rowversion` nos fluxos de medição/aprovação/baixa; auditoria alimentada pelos wrappers.
6. **Fase 5 (integração Excel):** endpoint `medicaoLote.cfm` (ou método CFC) que recebe `id_medicao` e itens (`id_medicaott`, `quantMed`, `id_centroCusto`, `obs`), passa pelas camadas centrais, valida tudo antes da primeira gravação e executa em uma única transação com rollback total em caso de erro.

### Recomendações específicas para ColdFusion/CFML

| Tema | Recomendação |
|---|---|
| `cfqueryparam` | Em toda entrada externa: `cf_sql_integer` para ids, `cf_sql_varchar` com `maxlength` para textos, `cf_sql_decimal` com `scale` para valores, `list="true"` para listas. Nunca interpolar `URL.`, `FORM.`, `arguments.` ou `session.` em SQL. |
| `Application.cfc` | Centralizar `onRequestStart` (sessão, método HTTP, CSRF, rotina), `onCFCRequest` (métodos remotos), `onError` (log + mensagem genérica), `onSessionEnd`. Definir `this.sessionTimeout`, `this.sessioncookie`, `this.scriptProtect = "all"`. |
| `onError` | Nunca `cfdump` da exceção em produção; registrar com `cflog` ou tabela, com identificador único devolvido ao usuário. Desativar "Enable Robust Exception Information" no CF Administrator. |
| Autorização central | `autorizacao.cfc` com funções por objeto (`podeVerContrato`, `podeEditarMedicao`, `medicaoPertenceContrato`, `itemPertenceMedicao`, `medicaoEstaAberta`); mapa página→rotina; papel derivado de `session`. |
| Validação server-side | `validacao.cfc` com as regras da matriz (Etapa 1, seção 9); `cfparam type=` para tipos básicos; respostas padronizadas em JSON. |
| CSRF | `CSRFGenerateToken()` / `CSRFVerifyToken()` (CF 10+); token no `$.ajaxSetup` e nos formulários; `SameSite=Lax`. |
| Cookies seguros | `this.sessioncookie = {httponly=true, secure=true, samesite="Lax"}`; `SessionRotate()` no login; `SessionInvalidate()` no logout. |
| Transações | `cftransaction` envolvendo validação + gravação + auditoria; `rowversion`/`timestamp` no SQL Server comparado no `UPDATE`. |
| Logs | `cflog` estruturado por evento de segurança (negativas de autorização, falhas de login, erros); retenção e revisão periódica. |
| Auditoria | Tabela única (usuário, data/hora, IP, sessão, ação, objeto, valor anterior, valor novo, motivo, resultado), alimentada pelos wrappers; cobrir medição, aprovação, baixa, exclusão, reprovação, contrato, pedido. |
| Consultas parametrizadas em listagens | Mapa fixo `campo → coluna`; `ordem → ASC/DESC`; DataTables server-side com allowlist de colunas. |
| Métodos remotos | `access="remote"` apenas na fachada; DAOs com `access="package"`; `returnformat="json"`; nunca expor `queryformat=column` com dados sensíveis sem filtro por usuário. |
| Senhas | Hash forte (`GenerateArgon2Hash`/`GenerateBCryptHash` no CF 2021 ou biblioteca Java equivalente); redefinição por token; bloqueio progressivo. |
| Uploads | Allowlist de extensões e tipo de conteúdo (`cffile accept` com `strict`), renomear com UUID, gravar fora do webroot, servir via `cfcontent` após autorização. |

## LIMITAÇÕES DA AVALIAÇÃO

Esta avaliação foi estática e passiva, restrita aos arquivos disponibilizados: páginas HTML salvas pelo navegador, JavaScript, CSS, três páginas de erro geradas pelo próprio sistema, um PDF e o baseline técnico. Esse tipo de análise permite identificar diversas classes de risco (exposição de erros, incorporação de entrada em SQL, dependência de validação client-side, dados de negócio transportados pelo cliente, ausência de tokens, padrões de acesso a relatórios, versões de componentes), mas **não comprova integralmente** aspectos que dependem de:

- **código-fonte do servidor** (`.cfm`/`.cfc`), incluindo `Application.cfc`, os includes de validação, os endpoints de gravação e os DAOs, dos quais depende a confirmação dos achados classificados como "indício forte" e "a verificar";
- **cabeçalhos HTTP e cookies** (`Secure`, `HttpOnly`, `SameSite`, `Set-Cookie` no login, cabeçalhos de segurança), não presentes em páginas salvas;
- **configuração do ColdFusion** (versão e nível de patch, "Robust Exception Information", tempo de sessão, datasources e privilégios do usuário de banco);
- **banco de dados** (constraints, triggers, tabelas de auditoria, `rowversion`, permissões);
- **infraestrutura** (servidor web frontal, conector AJP, firewall, WAF, proxy, segmentação de rede, monitoramento), que pode mitigar ou agravar os riscos descritos;
- **controles organizacionais** (perfis efetivamente atribuídos, processos de aprovação fora do sistema, revisão de logs).

Nenhum controle ou vulnerabilidade foi presumido além do que aparece nas evidências. Conclusões classificadas como "confirmado" referem-se ao comportamento demonstrado pelos próprios arquivos; as demais exigem confirmação por revisão do código no servidor, cujos arquivos prioritários estão listados na seção 12 da Etapa 1. Não foi realizado nenhum teste ativo, e nenhuma afirmação deste documento deve ser interpretada como demonstração de que o sistema foi ou pode ser comprometido.
