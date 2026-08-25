Attribute VB_Name = "modServices"
'==============================================================================
' modServices - Abas SERVICOS e CORRESPONDENCIA (itens 9, 13, 14, 36, 50, 51)
'==============================================================================
Option Explicit

Public Const ABA_SERVICOS As String = "SERVICOS"
Public Const ABA_CORRESP As String = "CORRESPONDENCIA"

' Layout definido em build_xlsm.py (LINHA_CABECALHO / LINHA_DADOS).
' Linhas 1-2 sao a faixa de titulo; 3-5 os campos; 6 a mensagem.
Private Const LINHA_CABECALHO As Long = 7
Private Const LINHA_DADOS As Long = 8

'------------------------------------------------------------- SERVICOS

Public Sub CarregarServicos()
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_SERVICOS)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("listar_servicos", _
        "familia", modJson.Texto(modUtils.CelulaTexto(ws, "B3")), _
        "situacao", modJson.Texto(modUtils.CelulaTexto(ws, "B4")), _
        "termo", modJson.Texto(modUtils.CelulaTexto(ws, "B5")), _
        "limite", "1000")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, LINHA_CABECALHO
    modUtils.EscreverCabecalho ws, LINHA_CABECALHO, _
        Array("CODIGO", "FAMILIA", "UN", "DESCRICAO", "PRECO", "APROVADO", _
              "ESCOPO", "REFERENCIA VINCULADA", "COMPOSICAO", "STATUS")

    Set lista = modJson.ObterLista(r, "servicos")
    linha = LINHA_DADOS
    For i = 1 To lista.Count
        Set item = lista(i)
        ws.Cells(linha, 1).Value = "'" & modJson.ObterTexto(item, "codigo")
        ws.Cells(linha, 2).Value = modJson.ObterTexto(item, "familia")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "unidade_orig")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 5).Value = modJson.ObterNumero(item, "preco")
        ws.Cells(linha, 5).NumberFormat = "R$ #,##0.00"
        ws.Cells(linha, 6).Value = IIf(modJson.ObterNumero(item, "preco_aprovado") = 1, "Sim", "Nao")
        ws.Cells(linha, 7).Value = modJson.ObterTexto(item, "escopo")
        If Len(modJson.ObterTexto(item, "ref_codigo")) > 0 Then
            ws.Cells(linha, 8).Value = modJson.ObterTexto(item, "ref_origem") & " " & _
                                       modJson.ObterTexto(item, "ref_codigo")
            ws.Cells(linha, 8).Interior.Color = modUtils.COR_VALIDADO
        End If
        ws.Cells(linha, 9).Value = modJson.ObterTexto(item, "composicao_propria")
        ws.Cells(linha, 10).Value = modJson.ObterTexto(item, "status_composicao")
        linha = linha + 1
    Next i

    ws.Range("B6").Value = lista.Count & " servico(s) listado(s)"
    modUtils.AjustarColunas ws, 10
    ws.Cells(LINHA_DADOS, 1).Select
    modUtils.Aguardar False
End Sub

Public Sub SelecionarServicoDaLinha()
    ' Leva o codigo da linha ativa para a aba CORRESPONDENCIA.
    Dim ws As Worksheet, codigo As String
    Set ws = modUtils.Aba(ABA_SERVICOS)
    If ws Is Nothing Then Exit Sub
    If ActiveCell.Row < LINHA_DADOS Then
        modUtils.Avisar "Selecione a linha de um servico na lista."
        Exit Sub
    End If
    codigo = Trim$(CStr(ws.Cells(ActiveCell.Row, 1).Value))
    If Len(codigo) = 0 Then Exit Sub
    BuscarCorrespondencia codigo
End Sub

'-------------------------------------------------------- CORRESPONDENCIA

Public Sub BuscarCorrespondencia(Optional ByVal codigoServico As String = "")
    Dim ws As Worksheet, r As Object, servico As Object
    Dim lista As Collection, item As Object, comp As Object
    Dim i As Long, linha As Long, origens As String

    Set ws = modUtils.Aba(ABA_CORRESP)
    If ws Is Nothing Then Exit Sub

    If Len(codigoServico) = 0 Then codigoServico = modUtils.CelulaTexto(ws, "B3")
    If Len(codigoServico) = 0 Then
        modUtils.Avisar "Informe o codigo do servico interno em B2."
        Exit Sub
    End If
    origens = modUtils.CelulaTexto(ws, "B4")
    If Len(origens) = 0 Then origens = "EDIF,INFRA"

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("buscar_servico", _
        "codigo_empresa", modJson.Texto(codigoServico), _
        "origens", modJson.Texto(origens), _
        "top_n", "10")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    ws.Activate
    modUtils.LimparAba ws, 7

    Set servico = modJson.ObterObjeto(r, "servico")
    ws.Range("B3").Value = "'" & codigoServico
    ws.Range("B5").Value = modJson.ObterTexto(servico, "descricao")
    ws.Range("B6").Value = "UN: " & modJson.ObterTexto(servico, "unidade_orig") & _
                           "   |   Familia: " & modJson.ObterTexto(servico, "familia") & _
                           "   |   Escopo: " & modJson.ObterTexto(servico, "escopo") & _
                           "   |   Preco interno: " & _
                           modUtils.FormatarMoeda(modJson.ObterNumero(servico, "preco"))

    modUtils.EscreverCabecalho ws, 7, _
        Array("#", "SCORE", "CONFIANCA", "TIPO", "ORIGEM", "CODIGO", "DESCRICAO", _
              "UN", "CUSTO REF.", "TEXTUAL", "SEMANTICA", "TERMOS", "UNIDADE", _
              "TECNICO", "OBSERVACOES")

    Set lista = modJson.ObterLista(r, "resultados")
    linha = 8
    For i = 1 To lista.Count
        Set item = lista(i)
        Set comp = modJson.ObterObjeto(item, "componentes")
        ws.Cells(linha, 1).Value = i
        ws.Cells(linha, 2).Value = modJson.ObterNumero(item, "score_pct") / 100
        ws.Cells(linha, 2).NumberFormat = "0.0%"
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "confianca")
        ws.Cells(linha, 3).Interior.Color = _
            modUtils.CorDaConfianca(modJson.ObterTexto(item, "confianca"))
        ws.Cells(linha, 4).Value = IIf(modJson.ObterTexto(item, "tipo") = "VINCULO_VALIDADO", _
                                       "VINCULO VALIDADO", "sugestao")
        ws.Cells(linha, 5).Value = modJson.ObterTexto(item, "origem")
        ws.Cells(linha, 6).Value = "'" & modJson.ObterTexto(item, "codigo")
        ws.Cells(linha, 7).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 8).Value = modJson.ObterTexto(item, "unidade_orig")
        ws.Cells(linha, 9).Value = modJson.ObterNumero(item, "custo_total")
        ws.Cells(linha, 9).NumberFormat = "R$ #,##0.00"
        ws.Cells(linha, 10).Value = modJson.ObterNumero(comp, "textual")
        ws.Cells(linha, 11).Value = modJson.ObterNumero(comp, "semantico")
        ws.Cells(linha, 12).Value = modJson.ObterNumero(comp, "cobertura")
        ws.Cells(linha, 13).Value = modJson.ObterNumero(comp, "unidade")
        ws.Cells(linha, 14).Value = modJson.ObterNumero(comp, "tecnico")
        ws.Range(ws.Cells(linha, 10), ws.Cells(linha, 14)).NumberFormat = "0.0%"
        ws.Cells(linha, 15).Value = JuntarLista(item, "penalidades", "reforcos")
        linha = linha + 1
    Next i

    ws.Range("D6").Value = lista.Count & " candidato(s). " & _
        "Nenhum e gravado automaticamente: escolha a linha e use ESCOLHER."
    modUtils.AjustarColunas ws, 15
    modUtils.Aguardar False
End Sub

Private Function JuntarLista(ByVal item As Object, ByVal chaveA As String, _
                             ByVal chaveB As String) As String
    Dim col As Collection, i As Long, sb As String
    Set col = modJson.ObterLista(item, chaveA)
    For i = 1 To col.Count
        sb = sb & IIf(Len(sb) > 0, " | ", "") & "- " & CStr(col(i))
    Next i
    Set col = modJson.ObterLista(item, chaveB)
    For i = 1 To col.Count
        sb = sb & IIf(Len(sb) > 0, " | ", "") & "+ " & CStr(col(i))
    Next i
    JuntarLista = sb
End Function

Public Sub EscolherCorrespondencia()
    ' Confirma o vinculo da linha ativa. A escolha final e SEMPRE humana
    ' (item 14): nada aqui e automatico, nem com score de 100%.
    Dim ws As Worksheet, r As Object
    Dim codigoServico As String, origem As String, codigoRef As String
    Dim score As Double, linha As Long

    Set ws = modUtils.Aba(ABA_CORRESP)
    If ws Is Nothing Then Exit Sub
    linha = ActiveCell.Row
    If linha < 8 Then
        modUtils.Avisar "Selecione a linha do candidato desejado."
        Exit Sub
    End If

    codigoServico = modUtils.CelulaTexto(ws, "B3")
    origem = Trim$(CStr(ws.Cells(linha, 5).Value))
    codigoRef = Trim$(CStr(ws.Cells(linha, 6).Value))
    score = 0
    If IsNumeric(ws.Cells(linha, 2).Value) Then score = CDbl(ws.Cells(linha, 2).Value)

    If Len(origem) = 0 Or Len(codigoRef) = 0 Then
        modUtils.Avisar "Linha sem candidato valido."
        Exit Sub
    End If

    If Not modUtils.Confirmar( _
        "Confirmar o vinculo?" & vbCrLf & vbCrLf & _
        "Servico interno: " & codigoServico & vbCrLf & _
        "Referencia: " & origem & " " & codigoRef & vbCrLf & _
        ws.Cells(linha, 7).Value & vbCrLf & vbCrLf & _
        "Score: " & modUtils.FormatarPercentual(score * 100), _
        "Confirmar correspondencia") Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("confirmar_servico", _
        "codigo_empresa", modJson.Texto(codigoServico), _
        "origem", modJson.Texto(origem), _
        "codigo_referencia", modJson.Texto(codigoRef), _
        "score", modJson.Numero(score), _
        "detalhe", modJson.Texto("Escolhido pelo usuario na aba CORRESPONDENCIA"))

    If modPythonBridge.DeuCerto(r) Then
        ws.Cells(linha, 4).Value = "VINCULO VALIDADO"
        ws.Cells(linha, 4).Interior.Color = modUtils.COR_VALIDADO
        If modUtils.Confirmar("Vinculo gravado." & vbCrLf & _
                              "Abrir a composicao de referencia agora?", "Proximo passo") Then
            modCompositions.AbrirComposicao origem, codigoRef, codigoServico
        End If
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub VerComposicaoDaLinha()
    Dim ws As Worksheet, linha As Long
    Set ws = modUtils.Aba(ABA_CORRESP)
    If ws Is Nothing Then Exit Sub
    linha = ActiveCell.Row
    If linha < 8 Then
        modUtils.Avisar "Selecione a linha do candidato."
        Exit Sub
    End If
    modCompositions.AbrirComposicao Trim$(CStr(ws.Cells(linha, 5).Value)), _
                                    Trim$(CStr(ws.Cells(linha, 6).Value)), _
                                    modUtils.CelulaTexto(ws, "B3")
End Sub

Public Sub NenhumCorresponde()
    ' Registra explicitamente que o servico nao tem correspondente (item 38).
    ' Marcar isso e informacao util: evita reanalisar o mesmo servico e
    ' alimenta a central de pendencias.
    Dim ws As Worksheet, r As Object, codigo As String, descricao As String
    Set ws = modUtils.Aba(ABA_CORRESP)
    codigo = modUtils.CelulaTexto(ws, "B3")
    descricao = modUtils.CelulaTexto(ws, "B5")
    If Len(codigo) = 0 Then Exit Sub
    If Not modUtils.Confirmar("Registrar que nenhum candidato EDIF/INFRA " & _
                              "corresponde ao servico " & codigo & "?", _
                              "Sem correspondencia") Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("registrar_pendencia", _
        "tipo", modJson.Texto("SERVICO_SEM_CORRESPONDENCIA"), _
        "codigo_servico", modJson.Texto(codigo), _
        "descricao", modJson.Texto(descricao), _
        "detalhe", modJson.Texto("Usuario avaliou os candidatos e nenhum corresponde."), _
        "prioridade", "3")

    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Registrado. O servico " & codigo & " aparece agora na " & _
                        "aba PENDENCIAS como SERVICO_SEM_CORRESPONDENCIA."
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub PesquisaManual()
    ' Pesquisa livre com filtros (item 36).
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim termo As String, i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_CORRESP)
    If ws Is Nothing Then Exit Sub
    termo = InputBox("Pesquisar nas bases EDIF/INFRA/AUX:" & vbCrLf & _
                     "(ex.: bloco concreto 14)", "Pesquisa manual")
    If Len(Trim$(termo)) = 0 Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("pesquisa_manual", _
        "alvo", modJson.Texto("REFERENCIA"), _
        "termo", modJson.Texto(termo), _
        "origens", modJson.Texto(modUtils.CelulaTexto(ws, "B4")), _
        "limite", "80")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, 7
    modUtils.EscreverCabecalho ws, 7, _
        Array("#", "SCORE", "CONFIANCA", "TIPO", "ORIGEM", "CODIGO", "DESCRICAO", _
              "UN", "CUSTO REF.")
    Set lista = modJson.ObterLista(r, "resultados")
    linha = 8
    For i = 1 To lista.Count
        Set item = lista(i)
        ws.Cells(linha, 1).Value = i
        ws.Cells(linha, 3).Value = "PESQUISA MANUAL"
        ws.Cells(linha, 4).Value = "manual"
        ws.Cells(linha, 5).Value = modJson.ObterTexto(item, "origem")
        ws.Cells(linha, 6).Value = "'" & modJson.ObterTexto(item, "codigo")
        ws.Cells(linha, 7).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 8).Value = modJson.ObterTexto(item, "unidade")
        ws.Cells(linha, 9).Value = modJson.ObterNumero(item, "custo_total")
        ws.Cells(linha, 9).NumberFormat = "R$ #,##0.00"
        linha = linha + 1
    Next i
    ws.Range("D6").Value = lista.Count & " resultado(s) da pesquisa manual por """ & termo & """."
    modUtils.AjustarColunas ws, 9
    modUtils.Aguardar False
End Sub

Public Sub AnalisarTodosOsServicos()
    ' Processamento em lote (itens 50 e 51): calcula sugestoes para a fila,
    ' priorizando os casos mais faceis. NAO confirma nada.
    Dim ws As Worksheet, r As Object, fila As Collection, item As Object
    Dim i As Long, linha As Long, limite As String

    limite = InputBox("Quantos servicos pendentes analisar?" & vbCrLf & _
                      "(a analise nao confirma nenhum vinculo)", _
                      "Analisar em lote", "100")
    If Len(Trim$(limite)) = 0 Then Exit Sub

    Set ws = modUtils.Aba(ABA_SERVICOS)
    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("analisar_lote", _
        "limite", CStr(CLng(Val(limite))), "top_n", "5")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, LINHA_CABECALHO
    modUtils.EscreverCabecalho ws, LINHA_CABECALHO, _
        Array("CODIGO", "FAMILIA", "UN", "DESCRICAO", "MELHOR SCORE", "CONFIANCA", _
              "ESCOPO", "MELHOR CANDIDATO", "DESCRICAO DO CANDIDATO", "STATUS")
    Set fila = modJson.ObterLista(r, "fila")
    linha = LINHA_DADOS
    For i = 1 To fila.Count
        Set item = fila(i)
        Dim sug As Collection, melhor As Object
        Set sug = modJson.ObterLista(item, "sugestoes")
        ws.Cells(linha, 1).Value = "'" & modJson.ObterTexto(item, "codigo_empresa")
        ws.Cells(linha, 2).Value = modJson.ObterTexto(item, "familia")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "unidade")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 5).Value = modJson.ObterNumero(item, "melhor_score")
        ws.Cells(linha, 5).NumberFormat = "0.0%"
        ws.Cells(linha, 6).Value = modJson.ObterTexto(item, "confianca")
        ws.Cells(linha, 6).Interior.Color = _
            modUtils.CorDaConfianca(modJson.ObterTexto(item, "confianca"))
        ws.Cells(linha, 7).Value = modJson.ObterTexto(item, "escopo")
        If sug.Count > 0 Then
            Set melhor = sug(1)
            ws.Cells(linha, 8).Value = modJson.ObterTexto(melhor, "origem") & " " & _
                                       modJson.ObterTexto(melhor, "codigo")
            ws.Cells(linha, 9).Value = modJson.ObterTexto(melhor, "descricao")
        End If
        ws.Cells(linha, 10).Value = "AGUARDA VALIDACAO"
        linha = linha + 1
    Next i
    ws.Range("B6").Value = fila.Count & " servico(s) na fila, dos mais faceis " & _
                           "para os mais dificeis. Nenhum vinculo foi confirmado."
    modUtils.AjustarColunas ws, 10
    modUtils.Aguardar False
    ws.Activate
End Sub
