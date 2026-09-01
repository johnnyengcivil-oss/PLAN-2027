Attribute VB_Name = "modEscolherItem"
'==============================================================================
' modEscolherItem - Logica da janela que escolhe o item da base da empresa.
'
' Mostra os candidatos com o score, o preco e - o que mais importa na
' pratica - COMO a unidade sera convertida. Um candidato barato com
' conversao pendente costuma ser pior que um um pouco mais caro com
' conversao resolvida, e a lista deixa isso visivel.
'==============================================================================
Option Explicit

Private mDescricaoRef As String
Private mUnidadeRef As String
Private mTipo As String
Private mCodins As String
Private mCandidatos As Collection

Public Sub Preparar(ByVal descricao As String, ByVal unidade As String, _
                    ByVal tipo As String, ByVal codins As String)
    mDescricaoRef = descricao
    mUnidadeRef = unidade
    mTipo = tipo
    mCodins = codins
End Sub

Public Sub Iniciar(ByVal f As Object)
    f.Escolhido = ""
    f.SemCorrespondente = False
    f.lblInsumoRef.Caption = mCodins & "   " & mDescricaoRef & _
        "     [unidade na referencia: " & mUnidadeRef & "]"
    f.txtBusca.Text = mDescricaoRef
    Buscar f, ""
End Sub

Public Sub Procurar(ByVal f As Object)
    Buscar f, Trim$(f.txtBusca.Text)
End Sub

Private Sub Buscar(ByVal f As Object, ByVal termo As String)
    Dim r As Object, lista As Collection, i As Long, c As Object, conv As Object
    Dim consulta As String

    consulta = termo
    If Len(consulta) = 0 Then consulta = mDescricaoRef

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("buscar_material", _
        "descricao", modJson.Texto(consulta), _
        "unidade", modJson.Texto(mUnidadeRef), _
        "tipo", modJson.Texto(mTipo), _
        "top_n", "15")
    modUtils.Aguardar False

    f.lstCandidatos.Clear
    Set mCandidatos = New Collection
    If Not modPythonBridge.DeuCerto(r) Then
        f.lblDetalhe.Caption = modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    Set lista = modJson.ObterLista(r, "resultados")
    For i = 1 To lista.Count
        Set c = lista(i)
        Set conv = modJson.ObterObjeto(c, "conversao")
        mCandidatos.Add c
        f.lstCandidatos.AddItem Format$(modJson.ObterNumero(c, "score_pct"), "0.0") & "%"
        f.lstCandidatos.List(i - 1, 1) = modJson.ObterTexto(c, "codigo")
        f.lstCandidatos.List(i - 1, 2) = modJson.ObterTexto(c, "descricao")
        f.lstCandidatos.List(i - 1, 3) = modJson.ObterTexto(c, "unidade_orig")
        f.lstCandidatos.List(i - 1, 4) = _
            Format$(modJson.ObterNumero(c, "preco"), "#,##0.00")
        f.lstCandidatos.List(i - 1, 5) = ResumoConversao(conv)
    Next i

    If lista.Count = 0 Then
        f.lblDetalhe.Caption = "Nenhum item encontrado." & vbCrLf & _
            "Tente outras palavras no campo Procurar - por exemplo so o " & _
            "nome do material, sem as especificacoes."
    Else
        f.lstCandidatos.ListIndex = 0
        Selecionado f
    End If
End Sub

Private Function ResumoConversao(ByVal conv As Object) As String
    If conv Is Nothing Then
        ResumoConversao = ""
    ElseIf LCase$(modJson.ObterTexto(conv, "ok")) = "true" Then
        If modJson.ObterNumero(conv, "fator") = 1 Then
            ResumoConversao = "direta"
        Else
            ResumoConversao = "x " & Format$(modJson.ObterNumero(conv, "fator"), "0.####")
        End If
    Else
        ResumoConversao = "PENDENTE"
    End If
End Function

Public Sub Selecionado(ByVal f As Object)
    Dim c As Object, conv As Object, sb As String, lst As Collection, i As Long
    If f.lstCandidatos.ListIndex < 0 Then Exit Sub
    Set c = mCandidatos(f.lstCandidatos.ListIndex + 1)
    Set conv = modJson.ObterObjeto(c, "conversao")

    sb = modJson.ObterTexto(c, "codigo") & "  " & modJson.ObterTexto(c, "descricao") & _
         "   [" & modJson.ObterTexto(c, "unidade_orig") & "]   " & _
         modUtils.FormatarMoeda(modJson.ObterNumero(c, "preco"))
    If Len(modJson.ObterTexto(c, "familia")) > 0 Then
        sb = sb & "   familia: " & modJson.ObterTexto(c, "familia")
    End If
    sb = sb & vbCrLf

    If modJson.ObterTexto(c, "tipo") = "VINCULO_VALIDADO" Then
        sb = sb & ">> Voce ja validou este vinculo antes <<" & vbCrLf
    End If

    If Not conv Is Nothing Then
        If LCase$(modJson.ObterTexto(conv, "ok")) = "true" Then
            sb = sb & "Conversao: " & modJson.ObterTexto(conv, "justificativa") & vbCrLf
        Else
            sb = sb & "CONVERSAO PENDENTE: " & _
                 modJson.ObterTexto(conv, "justificativa") & vbCrLf & _
                 "Voce ainda pode usar este item e digitar o coeficiente na mao." & vbCrLf
        End If
    End If

    Set lst = modJson.ObterLista(c, "penalidades")
    For i = 1 To lst.Count
        sb = sb & "  - " & CStr(lst(i)) & vbCrLf
    Next i

    f.lblDetalhe.Caption = sb
End Sub

Public Sub Confirmar(ByVal f As Object)
    Dim c As Object
    If f.lstCandidatos.ListIndex < 0 Then
        modUtils.Avisar "Escolha um item na lista."
        Exit Sub
    End If
    Set c = mCandidatos(f.lstCandidatos.ListIndex + 1)
    f.Escolhido = modJson.ObterTexto(c, "codigo")
    f.Hide
End Sub
