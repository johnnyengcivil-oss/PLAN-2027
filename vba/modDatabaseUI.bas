Attribute VB_Name = "modDatabaseUI"
'==============================================================================
' modDatabaseUI - Aba PENDENCIAS (itens 38, 39, 57)
'==============================================================================
Option Explicit

Public Const ABA_PENDENCIAS As String = "PENDENCIAS"

Public Sub CarregarPendencias()
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim resumo As Collection, i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_PENDENCIAS)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("listar_pendencias", _
        "status", modJson.Texto("ABERTA"), _
        "tipo", modJson.Texto(modUtils.CelulaTexto(ws, "B3")), _
        "limite", "1000")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, 7

    ' Resumo por tipo, no topo.
    Set resumo = modJson.ObterLista(r, "resumo")
    Dim txtResumo As String
    For i = 1 To resumo.Count
        Set item = resumo(i)
        txtResumo = txtResumo & IIf(Len(txtResumo) > 0, "   |   ", "") & _
            modJson.ObterTexto(item, "tipo") & ": " & modJson.ObterNumero(item, "total")
    Next i
    ws.Range("B4").Value = txtResumo

    modUtils.EscreverCabecalho ws, 7, _
        Array("ID", "PRIOR.", "TIPO", "SERVICO", "COMPOSICAO", "REFERENCIA", _
              "CODINS", "DESCRICAO", "DETALHE", "DATA")
    Set lista = modJson.ObterLista(r, "pendencias")
    linha = 8
    For i = 1 To lista.Count
        Set item = lista(i)
        ws.Cells(linha, 1).Value = modJson.ObterNumero(item, "id")
        ws.Cells(linha, 2).Value = modJson.ObterNumero(item, "prioridade")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "tipo")
        ws.Cells(linha, 4).Value = "'" & modJson.ObterTexto(item, "codigo_servico")
        ws.Cells(linha, 5).Value = modJson.ObterTexto(item, "codigo_composicao")
        ws.Cells(linha, 6).Value = modJson.ObterTexto(item, "origem") & " " & _
                                   modJson.ObterTexto(item, "codigo_referencia")
        ws.Cells(linha, 7).Value = "'" & modJson.ObterTexto(item, "codins")
        ws.Cells(linha, 8).Value = modJson.ObterTexto(item, "descricao")
        ws.Cells(linha, 9).Value = modJson.ObterTexto(item, "detalhe")
        ws.Cells(linha, 10).Value = modJson.ObterTexto(item, "data")
        If modJson.ObterNumero(item, "prioridade") <= 2 Then
            ws.Cells(linha, 3).Interior.Color = modUtils.COR_ALERTA
        Else
            ws.Cells(linha, 3).Interior.Color = modUtils.COR_PROVAVEL
        End If
        linha = linha + 1
    Next i
    ws.Range("B6").Value = lista.Count & " pendencia(s) aberta(s), das mais criticas para as menos."
    modUtils.AjustarColunas ws, 10
    modUtils.Aguardar False
End Sub

Public Sub ResolverPendenciaSelecionada()
    Dim ws As Worksheet, r As Object, ident As Long
    Set ws = modUtils.Aba(ABA_PENDENCIAS)
    If ActiveCell.Row < 8 Then
        modUtils.Avisar "Selecione a linha da pendencia."
        Exit Sub
    End If
    ident = CLng(Val(ws.Cells(ActiveCell.Row, 1).Value))
    If ident = 0 Then Exit Sub
    If Not modUtils.Confirmar("Marcar a pendencia " & ident & " como RESOLVIDA?", _
                              "Resolver pendencia") Then Exit Sub
    Set r = modPythonBridge.ChamarAcao("resolver_pendencia", _
        "id", CStr(ident), "novo_status", modJson.Texto("RESOLVIDA"))
    If modPythonBridge.DeuCerto(r) Then
        CarregarPendencias
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub IgnorarPendenciaSelecionada()
    Dim ws As Worksheet, r As Object, ident As Long
    Set ws = modUtils.Aba(ABA_PENDENCIAS)
    If ActiveCell.Row < 8 Then Exit Sub
    ident = CLng(Val(ws.Cells(ActiveCell.Row, 1).Value))
    If ident = 0 Then Exit Sub
    Set r = modPythonBridge.ChamarAcao("resolver_pendencia", _
        "id", CStr(ident), "novo_status", modJson.Texto("IGNORADA"))
    If modPythonBridge.DeuCerto(r) Then CarregarPendencias
End Sub

Public Sub VerHistoricoVinculos()
    ' Historico completo, inclusive vinculos substituidos (item 57).
    Dim r As Object, codigo As String, lista As Collection, item As Object
    Dim i As Long, texto As String

    codigo = InputBox("Codigo do servico interno (vazio = todos os recentes):", _
                      "Historico de vinculos")
    Set r = modPythonBridge.ChamarAcao("historico_vinculos", _
        "codigo_empresa", modJson.Texto(Trim$(codigo)), "limite", "40")
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If
    Set lista = modJson.ObterLista(r, "servicos")
    For i = 1 To lista.Count
        Set item = lista(i)
        texto = texto & modJson.ObterTexto(item, "codigo_empresa") & " -> " & _
            modJson.ObterTexto(item, "origem") & " " & _
            modJson.ObterTexto(item, "codigo_referencia") & "   [" & _
            modJson.ObterTexto(item, "status") & "]  " & _
            modJson.ObterTexto(item, "data") & vbCrLf
    Next i
    If Len(texto) = 0 Then texto = "Nenhum vinculo registrado."
    modUtils.Avisar texto, "Historico de vinculos"
End Sub
