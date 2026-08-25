Attribute VB_Name = "modMaterials"
'==============================================================================
' modMaterials - Montagem, revisao e gravacao da composicao propria
' (itens 23, 24, 25, 28, 29, 30, 31, 34, 39, 59)
'==============================================================================
Option Explicit

Public Const ABA_COMPOSICAO As String = "COMPOSICAO"
' Layout definido em build_xlsm.py: 1-2 titulo, 3-5 campos, 6 mensagem,
' 7 cabecalho da tabela, 8+ dados.
Private Const LINHA_ITENS As Long = 9

Public Sub MontarERevisar(ByVal codigoServico As String)
    Dim ws As Worksheet, r As Object, itens As Collection, item As Object
    Dim i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("montar_composicao", _
        "codigo_empresa", modJson.Texto(codigoServico), "top_sugestoes", "5")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    ws.Activate
    modUtils.LimparAba ws, 7

    ws.Range("B3").Value = "'" & codigoServico
    ws.Range("B4").Value = "COMPOSICAO PROPRIA (proposta) - " & modJson.ObterTexto(r, "descricao")
    ws.Range("B5").Value = "UN: " & modJson.ObterTexto(r, "unidade") & _
        "   |   Escopo: " & modJson.ObterTexto(r, "escopo_servico") & _
        "   |   Referencia: " & modJson.ObterTexto(r, "origem_referencia") & " " & _
        modJson.ObterTexto(r, "codigo_referencia") & _
        "   |   Data-base: " & modJson.ObterTexto(r, "data_base_ref")

    ws.Range("D6").Value = "Revise cada linha. Nada foi gravado ainda - use SALVAR COMPOSICAO."
    ws.Range("D6").Font.Italic = True
    linha = 8
    modUtils.EscreverCabecalho ws, linha, _
        Array("TIPO", "COD. INTERNO", "DESCRICAO INTERNA", "UN", "COEF. FINAL", _
              "PRECO INT.", "CUSTO", "SCORE", "SITUACAO", "CODINS REF.", _
              "DESCRICAO REF.", "UN REF.", "COEF. ORIG.", "CONVERSAO", _
              "CAMINHO DE EXPANSAO", "OBSERVACAO")

    Set itens = modJson.ObterLista(r, "itens")
    linha = LINHA_ITENS
    For i = 1 To itens.Count
        Set item = itens(i)
        Dim incluido As Boolean
        incluido = (LCase$(modJson.ObterTexto(item, "incluido_no_custo")) = "true")
        ws.Cells(linha, 1).Value = modJson.ObterTexto(item, "tipo")
        ws.Cells(linha, 2).Value = "'" & modJson.ObterTexto(item, "codigo_interno")
        ws.Cells(linha, 3).Value = modJson.ObterTexto(item, "descricao_interna")
        ws.Cells(linha, 4).Value = modJson.ObterTexto(item, "unidade_interna")
        ws.Cells(linha, 5).Value = modJson.ObterNumero(item, "coeficiente_final")
        ws.Cells(linha, 5).NumberFormat = "0.000000"
        ws.Cells(linha, 6).Value = modJson.ObterNumero(item, "preco_interno")
        ws.Cells(linha, 7).Value = modJson.ObterNumero(item, "custo_item")
        ws.Range(ws.Cells(linha, 6), ws.Cells(linha, 7)).NumberFormat = "R$ #,##0.0000"
        ws.Cells(linha, 8).Value = modJson.ObterNumero(item, "score")
        ws.Cells(linha, 8).NumberFormat = "0.0%"
        If Not incluido Then
            ws.Cells(linha, 9).Value = "NAO SOMADO"
            ws.Range(ws.Cells(linha, 1), ws.Cells(linha, 16)).Font.Italic = True
            ws.Cells(linha, 9).Interior.Color = modUtils.COR_ZEBRA
        ElseIf Len(modJson.ObterTexto(item, "pendencia")) > 0 Then
            ws.Cells(linha, 9).Value = modJson.ObterTexto(item, "pendencia")
            ws.Cells(linha, 9).Interior.Color = modUtils.COR_ALERTA
        Else
            ws.Cells(linha, 9).Value = modJson.ObterTexto(item, "detalhe_score")
            If InStr(1, modJson.ObterTexto(item, "detalhe_score"), "VALIDADO") > 0 Then
                ws.Cells(linha, 9).Interior.Color = modUtils.COR_VALIDADO
            End If
        End If
        ws.Cells(linha, 10).Value = "'" & modJson.ObterTexto(item, "codins_ref")
        ws.Cells(linha, 11).Value = modJson.ObterTexto(item, "descricao_ref")
        ws.Cells(linha, 12).Value = modJson.ObterTexto(item, "unidade_ref")
        ws.Cells(linha, 13).Value = modJson.ObterNumero(item, "coeficiente_original")
        ws.Cells(linha, 13).NumberFormat = "0.000000"
        ws.Cells(linha, 14).Value = modJson.ObterTexto(item, "metodo_conversao") & _
            IIf(modJson.ObterNumero(item, "fator_conversao") <> 1, _
                " (x" & modJson.ObterNumero(item, "fator_conversao") & ")", "")
        ws.Cells(linha, 15).Value = modJson.ObterTexto(item, "caminho_expansao")
        ws.Cells(linha, 16).Value = modJson.ObterTexto(item, "motivo_exclusao") & _
                                    modJson.ObterTexto(item, "justificativa_conv")
        linha = linha + 1
    Next i

    linha = linha + 1
    ws.Cells(linha, 3).Value = "CUSTO MAO DE OBRA"
    ws.Cells(linha, 7).Value = modJson.ObterNumero(r, "custo_mao_obra")
    ws.Cells(linha + 1, 3).Value = "CUSTO MATERIAIS"
    ws.Cells(linha + 1, 7).Value = modJson.ObterNumero(r, "custo_materiais")
    ws.Cells(linha + 2, 3).Value = "CUSTO EQUIPAMENTOS"
    ws.Cells(linha + 2, 7).Value = modJson.ObterNumero(r, "custo_equipamentos")
    ws.Cells(linha + 3, 3).Value = "CUSTO DIRETO"
    ws.Cells(linha + 3, 7).Value = modJson.ObterNumero(r, "custo_direto")
    ws.Range(ws.Cells(linha, 3), ws.Cells(linha + 3, 7)).Font.Bold = True
    ws.Range(ws.Cells(linha, 7), ws.Cells(linha + 3, 7)).NumberFormat = "R$ #,##0.0000"
    ws.Cells(linha + 3, 9).Value = "STATUS: " & modJson.ObterTexto(r, "status_composicao") & _
                                   "  " & modJson.ObterTexto(r, "motivo_status")

    modUtils.AjustarColunas ws, 16
    modUtils.Aguardar False
End Sub

Public Sub BuscarMaterialDaLinha()
    ' Abre as sugestoes de material/equipamento para a linha ativa (item 23).
    Dim ws As Worksheet, r As Object, lista As Collection, item As Object
    Dim linha As Long, descRef As String, unRef As String, tipo As String
    Dim i As Long, texto As String, conv As Object

    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    linha = ActiveCell.Row
    If linha < LINHA_ITENS Then
        modUtils.Avisar "Selecione a linha do insumo na composicao."
        Exit Sub
    End If
    descRef = Trim$(CStr(ws.Cells(linha, 11).Value))
    unRef = Trim$(CStr(ws.Cells(linha, 12).Value))
    tipo = Trim$(CStr(ws.Cells(linha, 1).Value))
    If Len(descRef) = 0 Then
        modUtils.Avisar "Esta linha nao tem insumo de referencia."
        Exit Sub
    End If

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("buscar_material", _
        "descricao", modJson.Texto(descRef), "unidade", modJson.Texto(unRef), _
        "tipo", modJson.Texto(tipo), "top_n", "8")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    Set lista = modJson.ObterLista(r, "resultados")
    texto = "INSUMO DA REFERENCIA:" & vbCrLf & descRef & "  [" & unRef & "]" & vbCrLf & vbCrLf
    For i = 1 To lista.Count
        Set item = lista(i)
        Set conv = modJson.ObterObjeto(item, "conversao")
        texto = texto & i & ". " & Format$(modJson.ObterNumero(item, "score_pct"), "0.0") & "%  " & _
            IIf(modJson.ObterTexto(item, "tipo") = "VINCULO_VALIDADO", "[VALIDADO] ", "") & _
            "cod " & modJson.ObterTexto(item, "codigo") & vbCrLf & _
            "    " & modUtils.TextoCurto(modJson.ObterTexto(item, "descricao"), 62) & vbCrLf & _
            "    " & modJson.ObterTexto(item, "unidade_orig") & "  " & _
            modUtils.FormatarMoeda(modJson.ObterNumero(item, "preco")) & _
            "   conv: " & IIf(LCase$(modJson.ObterTexto(conv, "ok")) = "true", _
                              modJson.ObterTexto(conv, "metodo"), "PENDENTE") & vbCrLf
    Next i
    texto = texto & vbCrLf & "Digite o numero da opcao para vincular (ou cancele)."

    Dim escolha As String
    escolha = InputBox(texto, "Sugestoes para o insumo")
    If Len(Trim$(escolha)) = 0 Then Exit Sub
    i = CLng(Val(escolha))
    If i < 1 Or i > lista.Count Then Exit Sub

    Set item = lista(i)
    Set r = modPythonBridge.ChamarAcao("confirmar_material", _
        "codins", modJson.Texto(Trim$(CStr(ws.Cells(linha, 10).Value))), _
        "codigo_empresa", modJson.Texto(modJson.ObterTexto(item, "codigo")), _
        "descricao_ref", modJson.Texto(descRef), _
        "unidade_ref", modJson.Texto(unRef), _
        "tipo", modJson.Texto(tipo), _
        "score", modJson.Numero(modJson.ObterNumero(item, "score")))

    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Vinculo confirmado." & vbCrLf & _
            "Escopo: " & modJson.ObterTexto(r, "escopo_vinculo") & vbCrLf & _
            "Fator de conversao: " & modJson.ObterNumero(r, "fator_conversao") & vbCrLf & _
            IIf(Len(modJson.ObterTexto(r, "observacao")) > 0, _
                vbCrLf & modJson.ObterTexto(r, "observacao"), "")
        MontarERevisar modUtils.CelulaTexto(ws, "B3")
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub SalvarComposicao()
    ' Grava a composicao propria apos a revisao humana (itens 14 e 29).
    Dim ws As Worksheet, r As Object, codigo As String
    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    codigo = modUtils.CelulaTexto(ws, "B3")
    If Len(codigo) = 0 Then
        modUtils.Avisar "Nenhuma composicao montada."
        Exit Sub
    End If
    If Not modUtils.Confirmar( _
        "Gravar a composicao propria do servico " & codigo & "?" & vbCrLf & vbCrLf & _
        "Os vinculos de material e equipamento revisados serao gravados " & _
        "como validados e reaproveitados nas proximas composicoes.", _
        "Salvar composicao") Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("salvar_composicao", _
        "codigo_empresa", modJson.Texto(codigo))
    modUtils.Aguardar False

    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Composicao " & modJson.ObterTexto(r, "codigo") & " gravada." & vbCrLf & _
            "Status: " & modJson.ObterTexto(r, "status_composicao") & vbCrLf & _
            modJson.ObterTexto(r, "motivo_status") & vbCrLf & vbCrLf & _
            "Custo direto: " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_direto"))
        modCompositions.CarregarBancoComposicoes
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

Public Sub CadastrarConversao()
    ' Resolve uma pendencia de conversao dependente do produto (item 26).
    Dim ws As Worksheet, r As Object, linha As Long
    Dim codigoInterno As String, unOrigem As String, unDestino As String, fator As String

    Set ws = modUtils.Aba(ABA_COMPOSICAO)
    linha = ActiveCell.Row
    If linha < LINHA_ITENS Then
        modUtils.Avisar "Selecione a linha do insumo com conversao pendente."
        Exit Sub
    End If
    codigoInterno = Trim$(CStr(ws.Cells(linha, 2).Value))
    unOrigem = Trim$(CStr(ws.Cells(linha, 4).Value))
    unDestino = Trim$(CStr(ws.Cells(linha, 12).Value))
    If Len(codigoInterno) = 0 Then
        modUtils.Avisar "A linha precisa ter um item interno vinculado."
        Exit Sub
    End If

    fator = InputBox( _
        "Quantas unidades de """ & unDestino & """ ha em 1 """ & unOrigem & """?" & vbCrLf & _
        "Item interno: " & ws.Cells(linha, 3).Value & vbCrLf & vbCrLf & _
        "Exemplo: cimento em saco de 50 kg -> 50", _
        "Cadastrar conversao do produto")
    If Len(Trim$(fator)) = 0 Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("cadastrar_conversao", _
        "escopo", modJson.Texto("MATERIAL"), _
        "chave", modJson.Texto(codigoInterno), _
        "unidade_origem", modJson.Texto(unOrigem), _
        "unidade_destino", modJson.Texto(unDestino), _
        "fator", modJson.Numero(Val(Replace(fator, ",", "."))), _
        "justificativa", modJson.Texto("Cadastrado pelo usuario na aba COMPOSICAO"))

    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Conversao cadastrada: 1 " & unOrigem & " = " & _
                        modJson.ObterNumero(r, "fator") & " " & unDestino
        MontarERevisar modUtils.CelulaTexto(ws, "B3")
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub
