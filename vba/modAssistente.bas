Attribute VB_Name = "modAssistente"
'==============================================================================
' modAssistente - Logica do assistente de composicao.
'
' O formulario e so a tela: cada evento dele chama uma rotina daqui. Assim
' a logica fica num modulo normal, versionado em arquivo e revisavel, e
' nao dentro de um objeto binario.
'
' O FLUXO, EM QUATRO PASSOS
'   1. Escolher o servico da empresa
'   2. Escolher a composicao EDIF/INFRA correspondente
'   3. Conferir e ajustar os insumos
'   4. Gravar
'
' Em nenhum momento algo e gravado sem o usuario mandar. O passo 3 permite
' trocar o item da empresa e alterar o coeficiente, e o custo e recalculado
' no Python a cada mudanca - a matematica nunca acontece aqui.
'==============================================================================
Option Explicit

Private Const PASSO_SERVICO As Long = 1
Private Const PASSO_REFERENCIA As Long = 2
Private Const PASSO_COMPOSICAO As Long = 3
Private Const PASSO_FIM As Long = 4

Private mPasso As Long
Private mServicos As Collection          ' todos os servicos, carregados uma vez
Private mVisiveis As Collection          ' os que estao na lista agora
Private mServico As Object               ' o escolhido
Private mCandidatos As Collection
Private mOrigem As String
Private mCodigoRef As String
Private mComposicao As Object            ' resposta do motor
Private mEdicoes As Object               ' codins -> alteracoes do usuario
Private mCarregando As Boolean

'==============================================================================
' Abertura
'==============================================================================

Public Sub Abrir()
    ' Ponto de entrada. Usa late binding de proposito: se os formularios
    ' nao tiverem sido criados, o codigo ainda compila e o sistema cai
    ' para a interface das abas.
    Dim f As Object
    On Error GoTo SemFormulario
    Set f = VBA.UserForms.Add("frmAssistente")
    f.Show
    Exit Sub
SemFormulario:
    If modUtils.Confirmar( _
        "O assistente em janela nao esta disponivel nesta planilha." & vbCrLf & vbCrLf & _
        "Isso acontece quando os formularios nao foram criados na " & _
        "instalacao. Deseja usar a versao em abas?", "Assistente") Then
        modServices.CarregarServicos
        modUtils.IrPara modServices.ABA_SERVICOS
    End If
End Sub

Public Sub Iniciar(ByVal f As Object)
    mPasso = PASSO_SERVICO
    mOrigem = ""
    mCodigoRef = ""
    Set mServico = Nothing
    Set mComposicao = Nothing
    Set mEdicoes = modJson.NovoDicionario
    CarregarTodosOsServicos f
    CarregarFamilias f
    AplicarFiltro f
    MostrarPasso f
End Sub

'==============================================================================
' Passo 1 - escolher o servico
'==============================================================================

Private Sub CarregarTodosOsServicos(ByVal f As Object)
    Dim r As Object
    Set mServicos = New Collection
    Set r = modPythonBridge.ChamarAcao("listar_servicos", "limite", "2000")
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If
    Dim lista As Collection, i As Long
    Set lista = modJson.ObterLista(r, "servicos")
    For i = 1 To lista.Count
        mServicos.Add lista(i)
    Next i
End Sub

Private Sub CarregarFamilias(ByVal f As Object)
    Dim vistas As Object, i As Long, fam As String
    Set vistas = modJson.NovoDicionario
    f.cboFamilia.Clear
    f.cboFamilia.AddItem "(todas as familias)"
    For i = 1 To mServicos.Count
        fam = modJson.ObterTexto(mServicos(i), "familia")
        If Len(fam) > 0 Then
            If Not vistas.Exists(fam) Then
                vistas(fam) = 1
                f.cboFamilia.AddItem fam
            End If
        End If
    Next i
    f.cboFamilia.ListIndex = 0
End Sub

Public Sub CarregarServicos(ByVal f As Object)
    AplicarFiltro f
End Sub

Public Sub AgendarFiltro(ByVal f As Object)
    ' Filtra em memoria a cada tecla. Os 949 servicos ja estao carregados,
    ' entao nao ha ida ao Python - a lista responde imediatamente.
    If mCarregando Then Exit Sub
    AplicarFiltro f
End Sub

Private Sub AplicarFiltro(ByVal f As Object)
    Dim i As Long, item As Object, termo As String, fam As String
    Dim texto As String, mostrar As Boolean, n As Long

    mCarregando = True
    termo = UCase$(Trim$(f.txtBusca.Text))
    fam = ""
    If f.cboFamilia.ListIndex > 0 Then fam = f.cboFamilia.Value

    f.lstServicos.Clear
    Set mVisiveis = New Collection

    For i = 1 To mServicos.Count
        Set item = mServicos(i)
        mostrar = True

        If Len(fam) > 0 Then
            If modJson.ObterTexto(item, "familia") <> fam Then mostrar = False
        End If
        If mostrar And f.chkPendentes.Value Then
            If Len(modJson.ObterTexto(item, "composicao_propria")) > 0 Then mostrar = False
        End If
        If mostrar And f.chkAprovados.Value Then
            If modJson.ObterNumero(item, "preco_aprovado") <> 1 Then mostrar = False
        End If
        If mostrar And Len(termo) > 0 Then
            texto = UCase$(modJson.ObterTexto(item, "codigo") & " " & _
                           modJson.ObterTexto(item, "descricao") & " " & _
                           modJson.ObterTexto(item, "familia"))
            If InStr(1, texto, termo) = 0 Then mostrar = False
        End If

        If mostrar Then
            mVisiveis.Add item
            n = n + 1
            f.lstServicos.AddItem modJson.ObterTexto(item, "codigo")
            f.lstServicos.List(n - 1, 1) = modJson.ObterTexto(item, "familia")
            f.lstServicos.List(n - 1, 2) = modJson.ObterTexto(item, "unidade_orig")
            f.lstServicos.List(n - 1, 3) = modJson.ObterTexto(item, "descricao")
            f.lstServicos.List(n - 1, 4) = _
                modUtils.FormatarMoeda(modJson.ObterNumero(item, "preco"))
            If n >= 400 Then Exit For
        End If
    Next i

    f.lblContagem.Caption = n & " servico(s) na lista, de " & mServicos.Count & _
        " no total. Clique num servico e depois em Avancar - ou de duplo clique."
    mCarregando = False
End Sub

Public Sub ServicoSelecionado(ByVal f As Object)
    If f.lstServicos.ListIndex < 0 Then Exit Sub
    Set mServico = mVisiveis(f.lstServicos.ListIndex + 1)
    f.lblRodape.Caption = "Selecionado: " & modJson.ObterTexto(mServico, "codigo")
End Sub

'==============================================================================
' Passo 2 - escolher a referencia
'==============================================================================

Private Sub CarregarCandidatos(ByVal f As Object)
    Dim r As Object, i As Long, c As Object

    f.lblServico.Caption = modJson.ObterTexto(mServico, "codigo") & "   [" & _
        modJson.ObterTexto(mServico, "unidade_orig") & "]   " & _
        modJson.ObterTexto(mServico, "descricao")

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("buscar_servico", _
        "codigo_empresa", modJson.Texto(modJson.ObterTexto(mServico, "codigo")), _
        "top_n", "12")
    modUtils.Aguardar False

    f.lstCandidatos.Clear
    Set mCandidatos = New Collection
    If Not modPythonBridge.DeuCerto(r) Then
        f.lblExplicacao.Caption = modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    Dim lista As Collection
    Set lista = modJson.ObterLista(r, "resultados")
    For i = 1 To lista.Count
        Set c = lista(i)
        mCandidatos.Add c
        f.lstCandidatos.AddItem Format$(modJson.ObterNumero(c, "score_pct"), "0.0") & "%"
        f.lstCandidatos.List(i - 1, 1) = modJson.ObterTexto(c, "origem")
        f.lstCandidatos.List(i - 1, 2) = modJson.ObterTexto(c, "codigo")
        f.lstCandidatos.List(i - 1, 3) = modJson.ObterTexto(c, "descricao")
    Next i

    If lista.Count = 0 Then
        f.lblExplicacao.Caption = "Nenhum candidato com score suficiente." & vbCrLf & _
            vbCrLf & "Use 'Procurar manualmente' para escolher pela descricao, " & _
            "ou 'Nenhum corresponde' para registrar que este servico nao tem " & _
            "equivalente nas bases de referencia."
    Else
        f.lstCandidatos.ListIndex = 0
        CandidatoSelecionado f
    End If
End Sub

Public Sub CandidatoSelecionado(ByVal f As Object)
    Dim c As Object, comp As Object, sb As String, lst As Collection, i As Long
    If f.lstCandidatos.ListIndex < 0 Then Exit Sub
    Set c = mCandidatos(f.lstCandidatos.ListIndex + 1)
    mOrigem = modJson.ObterTexto(c, "origem")
    mCodigoRef = modJson.ObterTexto(c, "codigo")

    Set comp = modJson.ObterObjeto(c, "componentes")
    sb = "POR QUE ESTE SCORE" & vbCrLf & vbCrLf
    sb = sb & Barra("Texto      ", modJson.ObterNumero(comp, "textual"))
    sb = sb & Barra("Sentido    ", modJson.ObterNumero(comp, "semantico"))
    sb = sb & Barra("Termos-cha", modJson.ObterNumero(comp, "cobertura"))
    sb = sb & Barra("Unidade    ", modJson.ObterNumero(comp, "unidade"))
    sb = sb & Barra("Tecnico    ", modJson.ObterNumero(comp, "tecnico"))
    sb = sb & vbCrLf & "FINAL: " & _
         Format$(modJson.ObterNumero(c, "score_pct"), "0.0") & "%  (" & _
         modJson.ObterTexto(c, "confianca") & ")" & vbCrLf

    If modJson.ObterTexto(c, "tipo") = "VINCULO_VALIDADO" Then
        sb = sb & vbCrLf & ">> VINCULO JA VALIDADO POR VOCE <<" & vbCrLf
    End If

    Set lst = modJson.ObterLista(c, "reforcos")
    If lst.Count > 0 Then
        sb = sb & vbCrLf & "A FAVOR:" & vbCrLf
        For i = 1 To lst.Count
            sb = sb & "  + " & CStr(lst(i)) & vbCrLf
        Next i
    End If
    Set lst = modJson.ObterLista(c, "penalidades")
    If lst.Count > 0 Then
        sb = sb & vbCrLf & "CONTRA:" & vbCrLf
        For i = 1 To lst.Count
            sb = sb & "  - " & CStr(lst(i)) & vbCrLf
        Next i
    End If

    f.lblExplicacao.Caption = sb
    f.lblRodape.Caption = "Referencia: " & mOrigem & " " & mCodigoRef
End Sub

Private Function Barra(ByVal rotulo As String, ByVal valor As Double) As String
    ' Barra de texto: comunica a proporcao mais rapido que o numero sozinho.
    Dim cheias As Long
    cheias = CLng(valor * 10)
    If cheias < 0 Then cheias = 0
    If cheias > 10 Then cheias = 10
    Barra = rotulo & " " & String$(cheias, ChrW$(9608)) & _
            String$(10 - cheias, ChrW$(9617)) & " " & _
            Format$(valor * 100, "0") & "%" & vbCrLf
End Function

Public Sub VerComposicaoReferencia(ByVal f As Object)
    If Len(mCodigoRef) = 0 Then
        modUtils.Avisar "Escolha um candidato na lista primeiro."
        Exit Sub
    End If
    modCompositions.AbrirComposicao mOrigem, mCodigoRef, _
        modJson.ObterTexto(mServico, "codigo")
    modUtils.Avisar "A composicao de referencia foi aberta na aba COMPOSICAO." & _
        vbCrLf & "Volte a esta janela para continuar."
End Sub

Public Sub PesquisaManual(ByVal f As Object)
    Dim termo As String, r As Object, lista As Collection, i As Long, c As Object
    termo = InputBox("Procurar nas bases EDIF, INFRA e AUXILIARES:" & vbCrLf & _
                     "(exemplo: bloco concreto 14)", "Procurar manualmente", _
                     modJson.ObterTexto(mServico, "descricao"))
    If Len(Trim$(termo)) = 0 Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("pesquisa_manual", _
        "alvo", modJson.Texto("REFERENCIA"), _
        "termo", modJson.Texto(termo), "limite", "60")
    modUtils.Aguardar False
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    f.lstCandidatos.Clear
    Set mCandidatos = New Collection
    Set lista = modJson.ObterLista(r, "resultados")
    For i = 1 To lista.Count
        Set c = lista(i)
        mCandidatos.Add c
        f.lstCandidatos.AddItem "manual"
        f.lstCandidatos.List(i - 1, 1) = modJson.ObterTexto(c, "origem")
        f.lstCandidatos.List(i - 1, 2) = modJson.ObterTexto(c, "codigo")
        f.lstCandidatos.List(i - 1, 3) = modJson.ObterTexto(c, "descricao")
    Next i
    f.lblExplicacao.Caption = lista.Count & " resultado(s) para """ & termo & """." & _
        vbCrLf & vbCrLf & "Estes vieram de pesquisa por palavra, entao nao tem " & _
        "score calculado. Escolha pela descricao."
    If lista.Count > 0 Then f.lstCandidatos.ListIndex = 0
End Sub

Public Sub NenhumCorresponde(ByVal f As Object)
    Dim r As Object
    If mServico Is Nothing Then Exit Sub
    If Not modUtils.Confirmar( _
        "Registrar que nenhuma composicao de referencia corresponde ao " & _
        "servico " & modJson.ObterTexto(mServico, "codigo") & "?" & vbCrLf & vbCrLf & _
        "Ele vai aparecer na aba PENDENCIAS.", "Sem correspondencia") Then Exit Sub

    Set r = modPythonBridge.ChamarAcao("registrar_pendencia", _
        "tipo", modJson.Texto("SERVICO_SEM_CORRESPONDENCIA"), _
        "codigo_servico", modJson.Texto(modJson.ObterTexto(mServico, "codigo")), _
        "descricao", modJson.Texto(modJson.ObterTexto(mServico, "descricao")), _
        "detalhe", modJson.Texto("Usuario avaliou os candidatos e nenhum corresponde."), _
        "prioridade", "3")
    If modPythonBridge.DeuCerto(r) Then
        modUtils.Avisar "Registrado. Voltando para escolher outro servico."
        mPasso = PASSO_SERVICO
        AplicarFiltro f
        MostrarPasso f
    Else
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
    End If
End Sub

'==============================================================================
' Passo 3 - conferir e ajustar os insumos
'==============================================================================

Private Sub MontarComposicao(ByVal f As Object)
    Dim r As Object
    modUtils.Aguardar True
    Set r = modPythonBridge.Chamar(PedidoComposicao("montar_composicao"))
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If
    Set mComposicao = r
    PreencherItens f
End Sub

Private Function PedidoComposicao(ByVal acao As String) As String
    ' Monta o JSON com as edicoes que o usuario ja fez, para o Python
    ' recalcular tudo. Os numeros nunca sao calculados aqui.
    Dim sb As String, chaves As Variant, i As Long, ed As Object
    sb = "{""acao"":" & modJson.Texto(acao) & _
         ",""codigo_empresa"":" & modJson.Texto(modJson.ObterTexto(mServico, "codigo")) & _
         ",""origem"":" & modJson.Texto(mOrigem) & _
         ",""codigo_referencia"":" & modJson.Texto(mCodigoRef) & _
         ",""top_sugestoes"":3"

    If mEdicoes.Count > 0 Then
        sb = sb & ",""itens"":["
        chaves = mEdicoes.Keys
        For i = LBound(chaves) To UBound(chaves)
            If i > LBound(chaves) Then sb = sb & ","
            Set ed = mEdicoes(chaves(i))
            sb = sb & "{""codins_ref"":" & modJson.Texto(CStr(chaves(i)))
            If Len(modJson.ObterTexto(ed, "codigo_interno")) > 0 Then
                sb = sb & ",""codigo_interno"":" & _
                     modJson.Texto(modJson.ObterTexto(ed, "codigo_interno"))
            End If
            If ed.Exists("coeficiente_final") Then
                sb = sb & ",""coeficiente_final"":" & _
                     modJson.Numero(modJson.ObterNumero(ed, "coeficiente_final"))
            End If
            If ed.Exists("excluir") Then
                sb = sb & ",""excluir"":true"
            End If
            sb = sb & "}"
        Next i
        sb = sb & "]"
    End If
    PedidoComposicao = sb & "}"
End Function

Private Sub Recalcular(ByVal f As Object)
    Dim r As Object, indice As Long
    indice = f.lstItens.ListIndex
    modUtils.Aguardar True
    Set r = modPythonBridge.Chamar(PedidoComposicao("recalcular_composicao"))
    modUtils.Aguardar False
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If
    Set mComposicao = r
    PreencherItens f
    If indice >= 0 And indice < f.lstItens.ListCount Then
        f.lstItens.ListIndex = indice
    End If
End Sub

Private Sub PreencherItens(ByVal f As Object)
    Dim itens As Collection, i As Long, it As Object, situacao As String

    f.lstItens.Clear
    Set itens = modJson.ObterLista(mComposicao, "itens")
    For i = 1 To itens.Count
        Set it = itens(i)
        f.lstItens.AddItem modJson.ObterTexto(it, "tipo")
        f.lstItens.List(i - 1, 1) = modJson.ObterTexto(it, "codigo_interno")
        f.lstItens.List(i - 1, 2) = ItemDescricao(it)
        f.lstItens.List(i - 1, 3) = modJson.ObterTexto(it, "unidade_interna")
        f.lstItens.List(i - 1, 4) = _
            Format$(modJson.ObterNumero(it, "coeficiente_final"), "0.000000")
        f.lstItens.List(i - 1, 5) = _
            Format$(modJson.ObterNumero(it, "custo_item"), "0.00")
        f.lstItens.List(i - 1, 6) = SituacaoItem(it)
    Next i

    f.lblTotais.Caption = _
        "Mao de obra: " & modUtils.FormatarMoeda(modJson.ObterNumero(mComposicao, "custo_mao_obra")) & _
        "     Materiais: " & modUtils.FormatarMoeda(modJson.ObterNumero(mComposicao, "custo_materiais")) & _
        "     Equipamentos: " & modUtils.FormatarMoeda(modJson.ObterNumero(mComposicao, "custo_equipamentos")) & _
        vbCrLf & "CUSTO DIRETO: " & _
        modUtils.FormatarMoeda(modJson.ObterNumero(mComposicao, "custo_direto")) & _
        "  por " & modJson.ObterTexto(mComposicao, "unidade") & _
        "        Situacao: " & modJson.ObterTexto(mComposicao, "status_composicao") & _
        " " & modJson.ObterTexto(mComposicao, "motivo_status")

    If itens.Count > 0 Then
        f.lstItens.ListIndex = 0
        ItemSelecionado f
    End If
End Sub

Private Function ItemDescricao(ByVal it As Object) As String
    ItemDescricao = modJson.ObterTexto(it, "descricao_interna")
    If Len(ItemDescricao) = 0 Then
        ItemDescricao = "(sem item da empresa) " & modJson.ObterTexto(it, "descricao_ref")
    End If
End Function

Private Function SituacaoItem(ByVal it As Object) As String
    If LCase$(modJson.ObterTexto(it, "incluido_no_custo")) <> "true" Then
        SituacaoItem = "nao somado"
    ElseIf Len(modJson.ObterTexto(it, "pendencia")) > 0 Then
        SituacaoItem = modJson.ObterTexto(it, "pendencia")
    ElseIf InStr(1, modJson.ObterTexto(it, "detalhe_score"), "VALIDADO") > 0 Then
        SituacaoItem = "vinculo validado"
    Else
        SituacaoItem = "sugestao"
    End If
End Function

Private Function ItemAtual(ByVal f As Object) As Object
    Dim itens As Collection
    If f.lstItens.ListIndex < 0 Then Exit Function
    Set itens = modJson.ObterLista(mComposicao, "itens")
    If f.lstItens.ListIndex + 1 > itens.Count Then Exit Function
    Set ItemAtual = itens(f.lstItens.ListIndex + 1)
End Function

Public Sub ItemSelecionado(ByVal f As Object)
    Dim it As Object, mo As Boolean
    Set it = ItemAtual(f)
    If it Is Nothing Then Exit Sub

    mo = (modJson.ObterTexto(it, "tipo") = "MAO_DE_OBRA")

    If Len(modJson.ObterTexto(it, "codins_ref")) > 0 Then
        f.lblRefInsumo.Caption = "Na referencia: " & _
            modJson.ObterTexto(it, "origem_ref") & " " & _
            modJson.ObterTexto(it, "codins_ref") & "  " & _
            modJson.ObterTexto(it, "descricao_ref") & _
            "   [" & modJson.ObterTexto(it, "unidade_ref") & "]" & _
            "   coeficiente original " & _
            Format$(modJson.ObterNumero(it, "coeficiente_original"), "0.000000")
    Else
        f.lblRefInsumo.Caption = "Este e o servico da empresa. Ele entra com " & _
            "coeficiente 1,0000 porque ja representa a execucao completa."
    End If

    f.lblInterno.Caption = modJson.ObterTexto(it, "codigo_interno") & "  " & _
        modJson.ObterTexto(it, "descricao_interna") & _
        "   [" & modJson.ObterTexto(it, "unidade_interna") & "]  " & _
        modUtils.FormatarMoeda(modJson.ObterNumero(it, "preco_interno"))

    f.txtCoef.Text = Format$(modJson.ObterNumero(it, "coeficiente_final"), "0.000000")
    f.lblCustoItem.Caption = "Custo deste item: " & _
        modUtils.FormatarMoeda(modJson.ObterNumero(it, "custo_item"))
    f.lblConversao.Caption = TextoConversao(it)

    ' Mao de obra referencial nao se edita: ela nao entra no custo.
    Dim editavel As Boolean
    editavel = (Len(modJson.ObterTexto(it, "codins_ref")) > 0) And _
               (LCase$(modJson.ObterTexto(it, "incluido_no_custo")) = "true")
    f.btnTrocar.Enabled = editavel
    f.txtCoef.Enabled = editavel Or Not mo
    f.btnMais.Enabled = f.txtCoef.Enabled
    f.btnMenos.Enabled = f.txtCoef.Enabled
    f.btnAplicar.Enabled = f.txtCoef.Enabled
    f.btnExcluir.Enabled = editavel
End Sub

Private Function TextoConversao(ByVal it As Object) As String
    Dim metodo As String, pend As String
    metodo = modJson.ObterTexto(it, "metodo_conversao")
    pend = modJson.ObterTexto(it, "pendencia")

    If LCase$(modJson.ObterTexto(it, "incluido_no_custo")) <> "true" Then
        TextoConversao = "NAO SOMADO: " & modJson.ObterTexto(it, "motivo_exclusao")
    ElseIf pend = "CONVERSAO_PENDENTE" Then
        TextoConversao = "CONVERSAO PENDENTE. " & _
            modJson.ObterTexto(it, "justificativa_conv") & vbCrLf & _
            "Voce pode digitar o coeficiente direto no campo acima."
    ElseIf Len(pend) > 0 Then
        TextoConversao = pend & ": " & modJson.ObterTexto(it, "justificativa_conv")
    ElseIf Len(metodo) > 0 Then
        TextoConversao = "Conversao: " & modJson.ObterTexto(it, "justificativa_conv")
    Else
        TextoConversao = ""
    End If
End Function

'------------------------------------------------------------- edicoes

Private Function EdicaoDe(ByVal codins As String) As Object
    If Not mEdicoes.Exists(codins) Then
        Set mEdicoes(codins) = modJson.NovoDicionario
    End If
    Set EdicaoDe = mEdicoes(codins)
End Function

Public Sub AplicarCoeficiente(ByVal f As Object)
    Dim it As Object, valor As Double, texto As String, ed As Object
    Set it = ItemAtual(f)
    If it Is Nothing Then Exit Sub
    If Len(modJson.ObterTexto(it, "codins_ref")) = 0 Then Exit Sub

    texto = Replace(Trim$(f.txtCoef.Text), ",", ".")
    If Len(texto) = 0 Or Not IsNumeric(texto) Then
        modUtils.Avisar "Digite um numero no coeficiente. Exemplo: 12,5"
        Exit Sub
    End If
    valor = Val(texto)
    If valor < 0 Then
        modUtils.Avisar "O coeficiente nao pode ser negativo."
        Exit Sub
    End If

    Set ed = EdicaoDe(modJson.ObterTexto(it, "codins_ref"))
    ed("coeficiente_final") = valor
    Recalcular f
End Sub

Public Sub AjustarCoeficiente(ByVal f As Object, ByVal fator As Double)
    Dim atual As Double
    If Not f.txtCoef.Enabled Then Exit Sub
    atual = Val(Replace(Trim$(f.txtCoef.Text), ",", "."))
    f.txtCoef.Text = Format$(atual * fator, "0.000000")
    AplicarCoeficiente f
End Sub

Public Sub ExcluirItem(ByVal f As Object)
    Dim it As Object, ed As Object
    Set it = ItemAtual(f)
    If it Is Nothing Then Exit Sub
    If Len(modJson.ObterTexto(it, "codins_ref")) = 0 Then Exit Sub
    If Not modUtils.Confirmar( _
        "Deixar este insumo FORA do custo da composicao?" & vbCrLf & vbCrLf & _
        modJson.ObterTexto(it, "descricao_ref") & vbCrLf & vbCrLf & _
        "Ele continua registrado, para rastreabilidade, mas com custo zero.", _
        "Nao usar este insumo") Then Exit Sub

    Set ed = EdicaoDe(modJson.ObterTexto(it, "codins_ref"))
    ed("excluir") = True
    ed("motivo_exclusao") = "Excluido pelo usuario na revisao da composicao."
    Recalcular f
End Sub

Public Sub TrocarItem(ByVal f As Object)
    Dim it As Object, dlg As Object, ed As Object
    If mPasso <> PASSO_COMPOSICAO Then Exit Sub
    Set it = ItemAtual(f)
    If it Is Nothing Then Exit Sub
    If Len(modJson.ObterTexto(it, "codins_ref")) = 0 Then
        modUtils.Avisar "Esta linha e o proprio servico da empresa - nao ha o " & _
                        "que trocar."
        Exit Sub
    End If

    On Error GoTo SemFormulario
    Set dlg = VBA.UserForms.Add("frmEscolherItem")
    modEscolherItem.Preparar modJson.ObterTexto(it, "descricao_ref"), _
                             modJson.ObterTexto(it, "unidade_ref"), _
                             modJson.ObterTexto(it, "tipo"), _
                             modJson.ObterTexto(it, "codins_ref")
    dlg.Show

    If dlg.SemCorrespondente Then
        Set ed = EdicaoDe(modJson.ObterTexto(it, "codins_ref"))
        ed("excluir") = True
        ed("motivo_exclusao") = "Sem item equivalente na base da empresa."
        Unload dlg
        Recalcular f
        Exit Sub
    End If

    If Len(dlg.Escolhido) > 0 Then
        Set ed = EdicaoDe(modJson.ObterTexto(it, "codins_ref"))
        ed("codigo_interno") = dlg.Escolhido
        If ed.Exists("excluir") Then ed.Remove "excluir"
        If ed.Exists("coeficiente_final") Then ed.Remove "coeficiente_final"
        Unload dlg
        Recalcular f
    Else
        Unload dlg
    End If
    Exit Sub

SemFormulario:
    modUtils.AvisarErro "A janela de escolha de item nao esta disponivel." & vbCrLf & _
        "Use a aba COMPOSICAO para trocar o item."
End Sub

'==============================================================================
' Navegacao entre os passos
'==============================================================================

Public Sub Avancar(ByVal f As Object)
    Select Case mPasso
        Case PASSO_SERVICO
            If mServico Is Nothing Then
                modUtils.Avisar "Escolha um servico na lista antes de avancar."
                Exit Sub
            End If
            mPasso = PASSO_REFERENCIA
            MostrarPasso f
            CarregarCandidatos f

        Case PASSO_REFERENCIA
            If Len(mCodigoRef) = 0 Then
                modUtils.Avisar "Escolha uma composicao de referencia, ou use " & _
                                "'Nenhum corresponde'."
                Exit Sub
            End If
            mPasso = PASSO_COMPOSICAO
            Set mEdicoes = modJson.NovoDicionario
            MostrarPasso f
            MontarComposicao f

        Case PASSO_COMPOSICAO
            Gravar f
    End Select
End Sub

Public Sub Voltar(ByVal f As Object)
    If mPasso = PASSO_FIM Then
        ' Depois de gravar, voltar significa comecar outro servico - e nao
        ' reabrir a composicao que ja foi para o banco.
        Iniciar f
        Exit Sub
    End If
    If mPasso > PASSO_SERVICO Then
        mPasso = mPasso - 1
        If mPasso = PASSO_SERVICO Then AplicarFiltro f
        MostrarPasso f
    End If
End Sub

Private Sub MostrarPasso(ByVal f As Object)
    f.fraPasso1.Visible = (mPasso = PASSO_SERVICO)
    f.fraPasso2.Visible = (mPasso = PASSO_REFERENCIA)
    f.fraPasso3.Visible = (mPasso = PASSO_COMPOSICAO)
    f.fraPasso4.Visible = (mPasso = PASSO_FIM)

    f.btnVoltar.Enabled = (mPasso > PASSO_SERVICO)
    If mPasso = PASSO_FIM Then
        f.btnVoltar.Caption = "< Compor outro"
    Else
        f.btnVoltar.Caption = "< Voltar"
    End If
    f.btnProximo.Visible = (mPasso < PASSO_COMPOSICAO)
    f.btnSalvar.Visible = (mPasso = PASSO_COMPOSICAO)

    Select Case mPasso
        Case PASSO_SERVICO
            f.lblPasso.Caption = "Passo 1 de 4 - Escolher o servico da empresa"
            f.lblAjuda.Caption = _
                "Escolha o servico do seu proprio catalogo para o qual voce quer " & _
                "montar uma composicao. Use a busca para achar mais rapido." & vbCrLf & _
                "Dica: de duplo clique num servico para ja avancar."
        Case PASSO_REFERENCIA
            f.lblPasso.Caption = "Passo 2 de 4 - Escolher a composicao de referencia"
            f.lblAjuda.Caption = _
                "O sistema procurou nas bases EDIF e INFRA e ordenou por " & _
                "semelhanca. O painel da direita explica cada score." & vbCrLf & _
                "A referencia serve para descobrir QUAIS materiais e equipamentos " & _
                "o servico consome - a mao de obra continua sendo a sua."
        Case PASSO_COMPOSICAO
            f.lblPasso.Caption = "Passo 3 de 4 - Conferir e ajustar os insumos"
            f.lblAjuda.Caption = _
                "Clique num insumo para edita-lo abaixo: trocar o item da empresa, " & _
                "mudar o coeficiente ou deixa-lo fora do custo." & vbCrLf & _
                "O custo e recalculado a cada mudanca. Nada e gravado ate voce " & _
                "clicar em GRAVAR COMPOSICAO."
        Case PASSO_FIM
            f.lblPasso.Caption = "Passo 4 de 4 - Composicao gravada"
            f.lblAjuda.Caption = _
                "A composicao entrou no banco proprio da empresa. Os vinculos que " & _
                "voce confirmou serao reaproveitados nas proximas composicoes."
    End Select

    f.lblTrilha.Caption = Trilha()
End Sub

Private Function Trilha() As String
    Dim nomes As Variant, i As Long, sb As String
    nomes = Array("Servico", "Referencia", "Composicao", "Gravar")
    For i = 0 To 3
        If i > 0 Then sb = sb & "   >   "
        If (i + 1) = mPasso Then
            sb = sb & ChrW$(9679) & " " & UCase$(nomes(i))
        ElseIf (i + 1) < mPasso Then
            sb = sb & ChrW$(10003) & " " & nomes(i)
        Else
            sb = sb & ChrW$(9675) & " " & nomes(i)
        End If
    Next i
    Trilha = sb
End Function

'==============================================================================
' Gravacao
'==============================================================================

Public Sub Gravar(ByVal f As Object)
    Dim r As Object, sb As String, pend As Collection, i As Long, p As Object
    If mComposicao Is Nothing Then Exit Sub

    Set pend = modJson.ObterLista(mComposicao, "pendencias")
    sb = "Gravar a composicao do servico " & _
         modJson.ObterTexto(mServico, "codigo") & "?" & vbCrLf & vbCrLf & _
         "Custo direto: " & _
         modUtils.FormatarMoeda(modJson.ObterNumero(mComposicao, "custo_direto")) & _
         " por " & modJson.ObterTexto(mComposicao, "unidade") & vbCrLf & _
         "Situacao: " & modJson.ObterTexto(mComposicao, "status_composicao")
    If pend.Count > 0 Then
        sb = sb & vbCrLf & vbCrLf & pend.Count & " pendencia(s) ficarao registradas " & _
             "para voce resolver depois. A composicao e gravada assim mesmo."
    End If
    sb = sb & vbCrLf & vbCrLf & "Os itens que voce escolheu viram vinculos " & _
         "validados e serao sugeridos automaticamente nas proximas composicoes."
    If Not modUtils.Confirmar(sb, "Gravar composicao") Then Exit Sub

    ' 1) o vinculo servico -> referencia
    Set r = modPythonBridge.ChamarAcao("confirmar_servico", _
        "codigo_empresa", modJson.Texto(modJson.ObterTexto(mServico, "codigo")), _
        "origem", modJson.Texto(mOrigem), _
        "codigo_referencia", modJson.Texto(mCodigoRef), _
        "detalhe", modJson.Texto("Escolhido no assistente"))
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    ' 2) a composicao, com as edicoes
    modUtils.Aguardar True
    Set r = modPythonBridge.Chamar(PedidoComposicao("salvar_composicao"))
    modUtils.Aguardar False
    If Not modPythonBridge.DeuCerto(r) Then
        modUtils.AvisarErro modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    Set mComposicao = r
    mPasso = PASSO_FIM
    MostrarPasso f

    sb = "COMPOSICAO GRAVADA" & vbCrLf & vbCrLf
    sb = sb & "Codigo proprio:  " & modJson.ObterTexto(r, "codigo") & vbCrLf
    sb = sb & "Servico:         " & modJson.ObterTexto(mServico, "codigo") & "  " & _
              modJson.ObterTexto(mComposicao, "descricao") & vbCrLf
    sb = sb & "Referencia:      " & mOrigem & " " & mCodigoRef & _
              "   (base " & modJson.ObterTexto(r, "data_base_ref") & ")" & vbCrLf & vbCrLf
    sb = sb & "Mao de obra:     " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_mao_obra")) & vbCrLf
    sb = sb & "Materiais:       " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_materiais")) & vbCrLf
    sb = sb & "Equipamentos:    " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_equipamentos")) & vbCrLf
    sb = sb & "CUSTO DIRETO:    " & modUtils.FormatarMoeda(modJson.ObterNumero(r, "custo_direto")) & _
              "  por " & modJson.ObterTexto(r, "unidade") & vbCrLf & vbCrLf
    sb = sb & "Situacao:        " & modJson.ObterTexto(r, "status_composicao") & vbCrLf
    If Len(modJson.ObterTexto(r, "motivo_status")) > 0 Then
        sb = sb & "                 " & modJson.ObterTexto(r, "motivo_status") & vbCrLf
    End If

    Set pend = modJson.ObterLista(r, "pendencias")
    If pend.Count > 0 Then
        sb = sb & vbCrLf & "PENDENCIAS REGISTRADAS (" & pend.Count & "):" & vbCrLf
        For i = 1 To pend.Count
            If i > 6 Then
                sb = sb & "  ... e mais " & (pend.Count - 6) & vbCrLf
                Exit For
            End If
            Set p = pend(i)
            sb = sb & "  - " & modJson.ObterTexto(p, "tipo") & ": " & _
                 modUtils.TextoCurto(modJson.ObterTexto(p, "descricao"), 60) & vbCrLf
        Next i
        sb = sb & vbCrLf & "Elas aparecem na aba PENDENCIAS."
    End If
    sb = sb & vbCrLf & vbCrLf & "Clique em Voltar para compor outro servico, " & _
         "ou Fechar para encerrar."
    f.lblResumo.Caption = sb

    f.btnVoltar.Enabled = True
    f.btnVoltar.Caption = "< Compor outro"
    modCompositions.CarregarBancoComposicoes
End Sub
