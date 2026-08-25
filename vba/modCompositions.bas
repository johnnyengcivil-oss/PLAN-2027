Attribute VB_Name = "modCompositions"
'==============================================================================
' modCompositions - Abas COMPOSICAO e BANCO_COMPOSICOES
' (itens 16, 20, 21, 22, 29, 30, 31, 37)
'==============================================================================
Option Explicit

Public Const ABA_COMPOSICAO As String = "COMPOSICAO"
Public Const ABA_BANCO As String = "BANCO_COMPOSICOES"

Public Sub AbrirComposicao(ByVal origem As String, ByVal codigo As String, _
                           Optional ByVal codigoServico As String = "")
    ' Mostra a composicao de referencia ja expandida: arvore hierarquica em
    ' cima, consolidado embaixo (item 22).
    Dim ws As Worksheet, r As Object, arvore As Collection, cons As Collection
    Dim linha As Long, i As Long

    If Len(origem) = 0 Or Len(codigo) = 0 Then
        modUtils.Avisar "Selecione um candidato antes."
        Exit Sub
    End If

    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("expandir_composicao", _
        "origem", modJson.Texto(origem), "codigo", modJson.Texto(codigo))
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    ws.Activate
    modUtils.LimparAba ws, 7

    ws.Range("B3").Value = "'" & codigoServico
    ws.Range("B4").Value = origem & " " & codigo & "  -  " & modJson.ObterTexto(r, "descricao")
    ws.Range("B5").Value = "UN: " & modJson.ObterTexto(r, "unidade_orig") & _
        "   |   Data-base: " & modJson.ObterTexto(r, "data_base") & _
        "   |   Custo publicado: " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_total_base")) & _
        "   |   Recalculado: " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_calculado")) & _
        "   |   Auxiliares expandidas: " & modJson.ObterNumero(r, "auxiliares_expandidas")

    ' ------------------------------------------------ arvore hierarquica
    linha = 7
    ws.Cells(linha, 1).Value = "COMPOSICAO HIERARQUICA (estrutura original preservada)"
    ws.Cells(linha, 1).Font.Bold = True
    linha = linha + 1
    modUtils.EscreverCabecalho ws, linha, _
        Array("NIVEL", "CODINS", "DESCRICAO", "UN", "COEF. LOCAL", "COEF. ACUM.", _
              "CUSTO UNIT.", "CLASSE", "SITUACAO")
    linha = linha + 1
    Set arvore = modJson.ObterLista(r, "arvore")
    linha = EscreverNos(ws, arvore, linha)

    ' ------------------------------------------------ consolidado
    linha = linha + 1
    ws.Cells(linha, 1).Value = "COMPOSICAO CONSOLIDADA (coeficientes acumulados ate os insumos folha)"
    ws.Cells(linha, 1).Font.Bold = True
    linha = linha + 1
    modUtils.EscreverCabecalho ws, linha, _
        Array("CLASSE", "CODINS", "DESCRICAO", "UN", "COEF. ACUMULADO", _
              "CUSTO UNIT.", "CUSTO", "OCORRENCIAS", "CAMINHO DE EXPANSAO")
    linha = linha + 1
    Set cons = modJson.ObterLista(r, "consolidado")
    Dim item As Object, caminhos As Collection, j As Long, txtCaminho As String
    For i = 1 To cons.Count
        Set item = cons(i)
        ws.Cells(linha, 1).Value = modJson.ObterTexto(item, "classe")
        ws.Cells(linha, 2).Value = "'" & modJson.ObterTexto(item, "codins")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "unidade_orig")
        ws.Cells(linha, 5).Value = modJson.ObterNumero(item, "coeficiente")
        ws.Cells(linha, 5).NumberFormat = "0.000000"
        ws.Cells(linha, 6).Value = modJson.ObterNumero(item, "custo_unitario")
        ws.Cells(linha, 7).Value = modJson.ObterNumero(item, "custo")
        ws.Range(ws.Cells(linha, 6), ws.Cells(linha, 7)).NumberFormat = "R$ #,##0.0000"
        ws.Cells(linha, 8).Value = modJson.ObterNumero(item, "ocorrencias")
        txtCaminho = ""
        Set caminhos = modJson.ObterLista(item, "caminhos")
        For j = 1 To caminhos.Count
            txtCaminho = txtCaminho & IIf(Len(txtCaminho) > 0, " ; ", "") & CStr(caminhos(j))
        Next j
        ws.Cells(linha, 9).Value = txtCaminho
        If modJson.ObterTexto(item, "classe") = "MAO_DE_OBRA" Then
            ws.Range(ws.Cells(linha, 1), ws.Cells(linha, 9)).Font.Italic = True
        End If
        linha = linha + 1
    Next i

    ' ------------------------------------------------ pendencias
    Dim pend As Collection
    Set pend = modJson.ObterLista(r, "pendencias")
    If pend.Count > 0 Then
        linha = linha + 1
        ws.Cells(linha, 1).Value = "PENDENCIAS DESTA COMPOSICAO"
        ws.Cells(linha, 1).Font.Bold = True
        ws.Cells(linha, 1).Interior.Color = modUtils.COR_ALERTA
        linha = linha + 1
        For i = 1 To pend.Count
            Set item = pend(i)
            ws.Cells(linha, 1).Value = modJson.ObterTexto(item, "tipo")
            ws.Cells(linha, 2).Value = "'" & modJson.ObterTexto(item, "codins")
            ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "descricao")
            ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "detalhe")
            linha = linha + 1
        Next i
    End If

    modUtils.AjustarColunas ws, 9
    modUtils.Aguardar False
End Sub

Private Function EscreverNos(ByVal ws As Worksheet, ByVal nos As Collection, _
                             ByVal linha As Long) As Long
    Dim i As Long, no As Object, nivel As Long, recuo As String
    For i = 1 To nos.Count
        Set no = nos(i)
        nivel = CLng(modJson.ObterNumero(no, "nivel"))
        recuo = String$(nivel * 4, " ")
        ws.Cells(linha, 1).Value = nivel
        ws.Cells(linha, 2).Value = "'" & recuo & modJson.ObterTexto(no, "codins")
        ws.Cells(linha, 3).Value = recuo & modJson.ObterTexto(no, "descricao")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(no, "unidade_orig")
        ws.Cells(linha, 5).Value = modJson.ObterNumero(no, "coeficiente")
        ws.Cells(linha, 6).Value = modJson.ObterNumero(no, "coeficiente_acumulado")
        ws.Range(ws.Cells(linha, 5), ws.Cells(linha, 6)).NumberFormat = "0.000000"
        ws.Cells(linha, 7).Value = modJson.ObterNumero(no, "custo_unitario")
        ws.Cells(linha, 7).NumberFormat = "R$ #,##0.0000"
        ws.Cells(linha, 8).Value = modJson.ObterTexto(no, "classe")
        If modJson.ObterTexto(no, "expandido") = "True" Then
            ws.Cells(linha, 9).Value = "AUXILIAR EXPANDIDA"
            ws.Range(ws.Cells(linha, 1), ws.Cells(linha, 9)).Font.Bold = True
        ElseIf Len(modJson.ObterTexto(no, "pendencia")) > 0 Then
            ws.Cells(linha, 9).Value = modJson.ObterTexto(no, "pendencia")
            ws.Cells(linha, 9).Interior.Color = modUtils.COR_ALERTA
        End If
        linha = linha + 1
        linha = EscreverNos(ws, modJson.ObterLista(no, "filhos"), linha)
    Next i
    EscreverNos = linha
End Function

'-------------------------------------------------- BANCO_COMPOSICOES

Public Sub CarregarBancoComposicoes()
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_BANCO)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("listar_composicoes", _
        "status", modJson.Texto(modUtils.CelulaTexto(ws, "B3")), "limite", "1000")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, 7
    modUtils.EscreverCabecalho ws, 7, _
        Array("CODIGO PROPRIO", "COD. MAO DE OBRA", "DESCRICAO", "UN", _
              "ORIGEM REF.", "COD. REF.", "DATA-BASE REF.", "MATERIAIS", _
              "EQUIPAMENTOS", "CUSTO M.O.", "CUSTO MAT.", "CUSTO EQUIP.", _
              "CUSTO DIRETO", "STATUS", "MOTIVO", "ATUALIZADA EM")

    Set lista = modJson.ObterLista(r, "composicoes")
    linha = 8
    For i = 1 To lista.Count
        Set item = lista(i)
        ws.Cells(linha, 1).Value = modJson.ObterTexto(item, "codigo")
        ws.Cells(linha, 2).Value = "'" & modJson.ObterTexto(item, "codigo_servico")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "unidade")
        ws.Cells(linha, 5).Value = modJson.ObterTexto(item, "origem_referencia")
        ws.Cells(linha, 6).Value = "'" & modJson.ObterTexto(item, "codigo_referencia")
        ws.Cells(linha, 7).Value = modJson.ObterTexto(item, "data_base_ref")
        ws.Cells(linha, 8).Value = modJson.ObterNumero(item, "qtd_materiais")
        ws.Cells(linha, 9).Value = modJson.ObterNumero(item, "qtd_equipamentos")
        ws.Cells(linha, 10).Value = modJson.ObterNumero(item, "custo_mao_obra")
        ws.Cells(linha, 11).Value = modJson.ObterNumero(item, "custo_materiais")
        ws.Cells(linha, 12).Value = modJson.ObterNumero(item, "custo_equipamentos")
        ws.Cells(linha, 13).Value = modJson.ObterNumero(item, "custo_direto")
        ws.Range(ws.Cells(linha, 10), ws.Cells(linha, 13)).NumberFormat = "R$ #,##0.0000"
        ws.Cells(linha, 14).Value = modJson.ObterTexto(item, "status")
        Select Case modJson.ObterTexto(item, "status")
            Case "COMPLETA": ws.Cells(linha, 14).Interior.Color = modUtils.COR_FORTE
            Case "PENDENTE": ws.Cells(linha, 14).Interior.Color = modUtils.COR_PROVAVEL
            Case "REVISAR": ws.Cells(linha, 14).Interior.Color = modUtils.COR_BAIXA
            Case Else: ws.Cells(linha, 14).Interior.Color = modUtils.COR_ALERTA
        End Select
        ws.Cells(linha, 15).Value = modJson.ObterTexto(item, "motivo_status")
        ws.Cells(linha, 16).Value = modJson.ObterTexto(item, "data_atualizacao")
        linha = linha + 1
    Next i
    ws.Range("B6").Value = lista.Count & " composicao(oes) propria(s)."
    modUtils.AjustarColunas ws, 16
    modUtils.Aguardar False
End Sub

Public Sub MontarComposicaoPropria()
    ' Monta a composicao propria a partir do vinculo confirmado e mostra
    ' na aba COMPOSICAO para revisao. NAO grava (item 14).
    Dim ws As Worksheet, codigo As String
    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    If ws Is Nothing Then Exit Sub
    codigo = modUtils.CelulaTexto(ws, "B3")
    If Len(codigo) = 0 Then
        codigo = InputBox("Codigo do servico interno:", "Montar composicao propria")
        If Len(Trim$(codigo)) = 0 Then Exit Sub
    End If
    modMaterials.MontarERevisar codigo
End Sub
