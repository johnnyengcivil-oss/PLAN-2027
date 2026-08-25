Attribute VB_Name = "modConfig"
'==============================================================================
' modConfig - Abas CONFIGURACAO e LOG (itens 4, 52, 53, 56)
'==============================================================================
Option Explicit

Public Const ABA_CONFIG As String = "CONFIGURACAO"
Public Const ABA_LOG As String = "LOG"

Public Sub CarregarConfiguracao()
    Dim ws As Worksheet, r As Object, cfg As Object, det As Object
    Dim chaves As Variant, i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_CONFIG)
    If ws Is Nothing Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("configuracao")
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    Set cfg = modJson.ObterObjeto(r, "config")
    Set det = modJson.ObterObjeto(r, "arquivos_detectados")

    ws.Range("B4").Value = modJson.ObterTexto(r, "raiz")
    ws.Range("B5").Value = modJson.ObterTexto(r, "pasta_bases")
    ws.Range("B6").Value = modJson.ObterTexto(r, "backend_semantico")
    ws.Range("B7").Value = modJson.ObterTexto(cfg, "politica_preco_material")

    ' Arquivos identificados. A deteccao e pelo CONTEUDO do arquivo; estas
    ' celulas permitem sobrepor manualmente uma unica vez (item 4).
    ' Linha 10 e o cabecalho da tabela; os dados comecam em 11 (Array e
    ' base zero neste modulo, logo linha + i vai de 11 a 15).
    linha = 11
    chaves = Array("SERVICOS", "MATERIAIS", "EDIF", "INFRA", "AUX")
    For i = LBound(chaves) To UBound(chaves)
        ws.Cells(linha + i, 1).Value = chaves(i)
        ws.Cells(linha + i, 2).Value = modJson.ObterTexto(det, CStr(chaves(i)), "(nao localizado)")
        If Len(modJson.ObterTexto(det, CStr(chaves(i)))) = 0 Then
            ws.Cells(linha + i, 2).Interior.Color = modUtils.COR_ALERTA
        Else
            ws.Cells(linha + i, 2).Interior.Color = modUtils.COR_FORTE
        End If
    Next i
    modUtils.AjustarColunas ws, 4
    modUtils.Aguardar False
End Sub

Public Sub SalvarConfiguracao()
    ' Grava a sobreposicao manual de origem dos .xls (item 4) e a politica
    ' de preco. A escolha fica salva em config.json.
    Dim ws As Worksheet, r As Object, pedido As String
    Dim edif As String, infra As String, aux As String, politica As String

    Set ws = modUtils.Aba(ABA_CONFIG)
    If ws Is Nothing Then Exit Sub

    ' Linhas: 11 SERVICOS | 12 MATERIAIS | 13 EDIF | 14 INFRA | 15 AUX
    edif = modUtils.CelulaTexto(ws, "C13")
    infra = modUtils.CelulaTexto(ws, "C14")
    aux = modUtils.CelulaTexto(ws, "C15")
    politica = modUtils.CelulaTexto(ws, "B7")
    If Len(politica) = 0 Then politica = "VALOR_APROVADO"

    pedido = "{""acao"":""configuracao"",""salvar"":true,""config"":{" & _
             """politica_preco_material"":" & modJson.Texto(politica)
    If Len(edif) > 0 Or Len(infra) > 0 Or Len(aux) > 0 Then
        pedido = pedido & ",""origem_forcada"":{"
        Dim partes As String
        If Len(edif) > 0 Then partes = modJson.Texto(edif) & ":" & modJson.Texto("EDIF")
        If Len(infra) > 0 Then partes = partes & IIf(Len(partes) > 0, ",", "") & _
            modJson.Texto(infra) & ":" & modJson.Texto("INFRA")
        If Len(aux) > 0 Then partes = partes & IIf(Len(partes) > 0, ",", "") & _
            modJson.Texto(aux) & ":" & modJson.Texto("AUX")
        pedido = pedido & partes & "}"
    End If
    pedido = pedido & "}}"

    Set r = modPythonBridge.Chamar(pedido)
    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Configuracao gravada em config.json." & vbCrLf & _
                        "Use ATUALIZAR BASES para reimportar com as novas definicoes."
        CarregarConfiguracao
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub AtualizarBases()
    ' Rele as bases sem perder vinculos, composicoes ou conversoes (item 53).
    Dim r As Object, cargas As Collection, ignorados As Collection
    Dim revisar As Collection, i As Long, texto As String, item As Object

    If Not modUtils.Confirmar( _
        "Reler as bases originais?" & vbCrLf & vbCrLf & _
        "Os arquivos NAO sao alterados (leitura apenas)." & vbCrLf & _
        "Vinculos confirmados, composicoes proprias e conversoes " & _
        "cadastradas sao preservados.", "Atualizar bases") Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("atualizar_bases")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    Set cargas = modJson.ObterLista(r, "cargas")
    Set ignorados = modJson.ObterLista(r, "ignorados")
    Set revisar = modJson.ObterLista(r, "composicoes_para_revisar")

    If cargas.Count = 0 Then
        texto = "Nenhuma base mudou desde a ultima importacao." & vbCrLf & _
                "Nada foi reprocessado."
    Else
        texto = "Bases reimportadas:" & vbCrLf
        For i = 1 To cargas.Count
            Set item = cargas(i)
            texto = texto & "  " & modJson.ObterTexto(item, "papel") & ": " & _
                    modJson.ObterTexto(item, "arquivo") & " (" & _
                    modJson.ObterNumero(item, "registros") & " registros)" & vbCrLf
        Next i
    End If
    If ignorados.Count > 0 Then
        texto = texto & vbCrLf & ignorados.Count & " base(s) inalterada(s), nao reprocessada(s)."
    End If
    If revisar.Count > 0 Then
        texto = texto & vbCrLf & vbCrLf & revisar.Count & _
                " composicao(oes) propria(s) marcada(s) como REVISAR " & _
                "porque a referencia mudou."
    End If
    modUtils.Avisar texto, "Atualizar bases"
    modMain.AtualizarInicio
End Sub

Public Sub CarregarLog()
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_LOG)
    If ws Is Nothing Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("ver_log", "limite", "500")
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    modUtils.LimparAba ws, 7
    modUtils.EscreverCabecalho ws, 7, _
        Array("DATA/HORA", "USUARIO", "ACAO", "ENTIDADE", "CHAVE", "DETALHE", "SCORE", "OK")
    Set lista = modJson.ObterLista(r, "log")
    linha = 8
    For i = 1 To lista.Count
        Set item = lista(i)
        ws.Cells(linha, 1).Value = modJson.ObterTexto(item, "data")
        ws.Cells(linha, 2).Value = modJson.ObterTexto(item, "usuario")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "acao")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "entidade")
        ws.Cells(linha, 5).Value = "'" & modJson.ObterTexto(item, "chave")
        ws.Cells(linha, 6).Value = modJson.ObterTexto(item, "detalhe")
        ws.Cells(linha, 7).Value = modJson.ObterNumero(item, "score")
        ws.Cells(linha, 8).Value = IIf(modJson.ObterNumero(item, "sucesso") = 1, "Sim", "NAO")
        If modJson.ObterNumero(item, "sucesso") <> 1 Then
            ws.Cells(linha, 8).Interior.Color = modUtils.COR_ALERTA
        End If
        linha = linha + 1
    Next i
    ws.Range("B3").Value = lista.Count & " registro(s) de auditoria."
    modUtils.AjustarColunas ws, 8
    modUtils.Aguardar False
End Sub
