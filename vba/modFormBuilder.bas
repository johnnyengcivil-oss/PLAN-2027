Attribute VB_Name = "modFormBuilder"
'==============================================================================
' modFormBuilder - Constroi os formularios do sistema.
'
' POR QUE OS FORMULARIOS SAO CONSTRUIDOS POR CODIGO
'
' Um UserForm distribuido como arquivo (.frm mais .frx) so e valido se o
' par binario estiver exatamente correto, e um erro ali faz o Excel
' recusar o arquivo inteiro. Construindo pela propria API do Excel, quem
' monta o formulario e o Excel - entao ele e valido por construcao.
'
' Roda uma unica vez, durante a instalacao (instalar_vba.vbs), com a opcao
' "Confiar no acesso ao modelo de objeto do projeto do VBA" ligada
' temporariamente pelo MONTAR_PLANILHA.bat.
'
' Se por algum motivo os formularios nao existirem, o sistema continua
' utilizavel pelas abas da planilha - nenhuma funcionalidade se perde.
'==============================================================================
Option Explicit

Private Const TIPO_FORMULARIO As Long = 3      ' vbext_ct_MSForm

' Paleta, em BGR (o VBA inverte a ordem em relacao ao RGB do HTML).
Private Const COR_FUNDO As Long = 16777215
Private Const COR_PAINEL As Long = 15922158
Private Const COR_TITULO As Long = 6567968   ' RGB(31,56,100) em BGR
Private Const COR_TEXTO As Long = 3355443

'==============================================================================
' Entrada
'==============================================================================

Public Sub CriarFormularios()
    ' Chamada pelo instalador. Recria os dois formularios do zero.
    On Error GoTo Falhou
    RemoverSeExistir "frmAssistente"
    RemoverSeExistir "frmEscolherItem"
    ConstruirAssistente
    ConstruirEscolherItem
    Exit Sub
Falhou:
    ' Nao interrompe a instalacao: as abas continuam funcionando.
    Debug.Print "modFormBuilder: " & Err.Description
End Sub

Public Function FormulariosExistem() As Boolean
    Dim comp As Object
    On Error Resume Next
    Set comp = ThisWorkbook.VBProject.VBComponents("frmAssistente")
    FormulariosExistem = Not (comp Is Nothing)
    On Error GoTo 0
End Function

Private Sub RemoverSeExistir(ByVal nome As String)
    Dim comp As Object
    On Error Resume Next
    Set comp = ThisWorkbook.VBProject.VBComponents(nome)
    If Not comp Is Nothing Then ThisWorkbook.VBProject.VBComponents.Remove comp
    On Error GoTo 0
End Sub

'==============================================================================
' Auxiliares de construcao
'==============================================================================

Private Function NovoFormulario(ByVal nome As String, ByVal titulo As String, _
                                ByVal larg As Single, ByVal alt As Single) As Object
    Dim comp As Object
    Set comp = ThisWorkbook.VBProject.VBComponents.Add(TIPO_FORMULARIO)
    comp.Name = nome
    With comp.Designer
        .Properties("Caption") = titulo
        .Properties("Width") = larg
        .Properties("Height") = alt
        .Properties("BackColor") = COR_FUNDO
    End With
    Set NovoFormulario = comp
End Function

Private Function Ctl(ByVal pai As Object, ByVal tipo As String, ByVal nome As String, _
                     ByVal esq As Single, ByVal topo As Single, _
                     ByVal larg As Single, ByVal alt As Single) As Object
    Dim c As Object
    Set c = pai.Controls.Add(tipo, nome, True)
    c.Left = esq
    c.Top = topo
    c.Width = larg
    c.Height = alt
    Set Ctl = c
End Function

Private Function Rotulo(ByVal pai As Object, ByVal nome As String, ByVal texto As String, _
                        ByVal esq As Single, ByVal topo As Single, _
                        ByVal larg As Single, ByVal alt As Single, _
                        Optional ByVal tamanho As Single = 9, _
                        Optional ByVal negrito As Boolean = False, _
                        Optional ByVal cor As Long = -1) As Object
    Dim c As Object
    Set c = Ctl(pai, "Forms.Label.1", nome, esq, topo, larg, alt)
    c.Caption = texto
    c.Font.Name = "Segoe UI"
    c.Font.Size = tamanho
    c.Font.Bold = negrito
    If cor >= 0 Then c.ForeColor = cor
    Set Rotulo = c
End Function

Private Function Botao(ByVal pai As Object, ByVal nome As String, ByVal texto As String, _
                       ByVal esq As Single, ByVal topo As Single, _
                       ByVal larg As Single, Optional ByVal alt As Single = 24) As Object
    Dim c As Object
    Set c = Ctl(pai, "Forms.CommandButton.1", nome, esq, topo, larg, alt)
    c.Caption = texto
    c.Font.Name = "Segoe UI"
    c.Font.Size = 9
    Set Botao = c
End Function

Private Function Lista(ByVal pai As Object, ByVal nome As String, _
                       ByVal esq As Single, ByVal topo As Single, _
                       ByVal larg As Single, ByVal alt As Single, _
                       ByVal colunas As Long, ByVal largColunas As String) As Object
    Dim c As Object
    Set c = Ctl(pai, "Forms.ListBox.1", nome, esq, topo, larg, alt)
    c.ColumnCount = colunas
    c.ColumnWidths = largColunas
    c.Font.Name = "Consolas"
    c.Font.Size = 8
    Set Lista = c
End Function

Private Function Caixa(ByVal pai As Object, ByVal nome As String, _
                       ByVal esq As Single, ByVal topo As Single, _
                       ByVal larg As Single, Optional ByVal alt As Single = 18) As Object
    Dim c As Object
    Set c = Ctl(pai, "Forms.TextBox.1", nome, esq, topo, larg, alt)
    c.Font.Name = "Segoe UI"
    c.Font.Size = 9
    Set Caixa = c
End Function

Private Function Painel(ByVal pai As Object, ByVal nome As String, ByVal titulo As String, _
                        ByVal esq As Single, ByVal topo As Single, _
                        ByVal larg As Single, ByVal alt As Single) As Object
    Dim c As Object
    Set c = Ctl(pai, "Forms.Frame.1", nome, esq, topo, larg, alt)
    c.Caption = titulo
    c.Font.Name = "Segoe UI"
    c.Font.Size = 9
    Set Painel = c
End Function

'==============================================================================
' frmAssistente - o fluxo inteiro em quatro passos
'==============================================================================

Private Sub ConstruirAssistente()
    Dim comp As Object, f As Object, p1 As Object, p2 As Object
    Dim p3 As Object, p4 As Object, ed As Object, c As Object

    Set comp = NovoFormulario("frmAssistente", _
        "Assistente de Composicao - Banco Proprio", 720, 470)
    Set f = comp.Designer

    ' ---------------------------------------------------------- cabecalho
    Rotulo f, "lblPasso", "Passo 1 de 4 - Escolher o servico da empresa", _
           12, 8, 480, 20, 13, True, COR_TITULO
    Rotulo f, "lblAjuda", "", 12, 30, 690, 28, 9, False, COR_TEXTO
    Rotulo f, "lblTrilha", "", 12, 60, 690, 14, 8, False, COR_TEXTO

    ' ------------------------------------------------- passo 1: servico
    Set p1 = Painel(f, "fraPasso1", " O que voce quer compor? ", 8, 78, 700, 300)
    Rotulo p1, "lblBusca", "Procurar por palavra:", 10, 16, 110, 14
    Caixa p1, "txtBusca", 122, 14, 200
    Rotulo p1, "lblFam", "Familia:", 336, 16, 46, 14
    Set c = Ctl(p1, "Forms.ComboBox.1", "cboFamilia", 384, 14, 170, 18)
    c.Font.Name = "Segoe UI": c.Font.Size = 9
    Botao p1, "btnFiltrar", "Filtrar", 566, 13, 70, 20
    Set c = Ctl(p1, "Forms.CheckBox.1", "chkPendentes", 10, 38, 260, 16)
    c.Caption = "Mostrar apenas os que ainda nao tem composicao"
    c.Font.Name = "Segoe UI": c.Font.Size = 9
    c.Value = True
    Set c = Ctl(p1, "Forms.CheckBox.1", "chkAprovados", 280, 38, 200, 16)
    c.Caption = "Apenas com preco aprovado"
    c.Font.Name = "Segoe UI": c.Font.Size = 9
    Lista p1, "lstServicos", 10, 60, 680, 200, 5, "50;90;28;400;60"
    Rotulo p1, "lblContagem", "", 10, 266, 680, 14, 8, False, COR_TEXTO

    ' ---------------------------------------------- passo 2: referencia
    Set p2 = Painel(f, "fraPasso2", " Qual composicao de referencia corresponde? ", _
                    8, 78, 700, 300)
    Rotulo p2, "lblServico", "", 10, 14, 680, 26, 9, True
    Lista p2, "lstCandidatos", 10, 44, 400, 150, 5, "40;36;60;230;0"
    Set c = Rotulo(p2, "lblExplicacao", "", 418, 44, 272, 150, 8)
    c.BackColor = COR_PAINEL
    Botao p2, "btnVerComp", "Ver composicao completa", 10, 200, 150
    Botao p2, "btnManual", "Procurar manualmente", 168, 200, 150
    Botao p2, "btnNenhum", "Nenhum corresponde", 326, 200, 150
    Rotulo p2, "lblAvisoEscolha", _
        "Nada e gravado automaticamente. Mesmo com 100%, a escolha e sua.", _
        10, 228, 680, 14, 8, False, COR_TEXTO

    ' --------------------------------------------- passo 3: composicao
    Set p3 = Painel(f, "fraPasso3", " Confira e ajuste os insumos ", 8, 78, 700, 300)
    Lista p3, "lstItens", 10, 14, 680, 120, 7, "62;46;190;28;62;62;110"
    Set ed = Painel(p3, "fraEdicao", " Item selecionado ", 10, 138, 680, 116)
    Rotulo ed, "lblRefInsumo", "", 8, 12, 660, 22, 8, False, COR_TEXTO
    Rotulo ed, "lblInternoRot", "Item da empresa:", 8, 38, 90, 14, 9, True
    Rotulo ed, "lblInterno", "", 100, 38, 400, 14, 9
    Botao ed, "btnTrocar", "Trocar item...", 508, 34, 90, 20
    Botao ed, "btnExcluir", "Nao usar", 602, 34, 66, 20
    Rotulo ed, "lblCoefRot", "Coeficiente:", 8, 62, 66, 14, 9, True
    Caixa ed, "txtCoef", 76, 60, 80
    Botao ed, "btnMenos", "-10%", 160, 59, 40, 20
    Botao ed, "btnMais", "+10%", 202, 59, 40, 20
    Botao ed, "btnAplicar", "Aplicar", 246, 59, 60, 20
    Rotulo ed, "lblConversao", "", 8, 84, 660, 24, 8, False, COR_TEXTO
    Rotulo ed, "lblCustoItem", "", 316, 62, 350, 14, 9, True
    Set c = Rotulo(p3, "lblTotais", "", 10, 258, 680, 32, 9, True)
    c.BackColor = COR_PAINEL

    ' ----------------------------------------------- passo 4: concluido
    Set p4 = Painel(f, "fraPasso4", " Composicao gravada ", 8, 78, 700, 300)
    Rotulo p4, "lblResumo", "", 12, 16, 676, 250, 10

    ' ------------------------------------------------------------ rodape
    Botao f, "btnVoltar", "< Voltar", 12, 388, 90, 26
    Botao f, "btnProximo", "Avancar >", 108, 388, 110, 26
    Botao f, "btnSalvar", "GRAVAR COMPOSICAO", 224, 388, 160, 26
    Botao f, "btnFechar", "Fechar", 620, 388, 88, 26
    Rotulo f, "lblRodape", "", 392, 393, 222, 16, 8, False, COR_TEXTO

    InserirCodigoAssistente comp
End Sub

Private Sub InserirCodigoAssistente(ByVal comp As Object)
    ' O codigo do formulario e proposital e deliberadamente fino: cada
    ' evento so repassa para modAssistente. Assim a logica fica num modulo
    ' normal, versionado em arquivo e possivel de revisar.
    Dim s As String
    s = "Option Explicit" & vbCrLf & vbCrLf
    s = s & "Private Sub UserForm_Initialize()" & vbCrLf
    s = s & "    modAssistente.Iniciar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnFiltrar_Click()" & vbCrLf
    s = s & "    modAssistente.CarregarServicos Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub txtBusca_Change()" & vbCrLf
    s = s & "    modAssistente.AgendarFiltro Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstServicos_Click()" & vbCrLf
    s = s & "    modAssistente.ServicoSelecionado Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstServicos_DblClick(ByVal Cancel As MSForms.ReturnBoolean)" & vbCrLf
    s = s & "    modAssistente.Avancar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstCandidatos_Click()" & vbCrLf
    s = s & "    modAssistente.CandidatoSelecionado Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstCandidatos_DblClick(ByVal Cancel As MSForms.ReturnBoolean)" & vbCrLf
    s = s & "    modAssistente.Avancar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstItens_Click()" & vbCrLf
    s = s & "    modAssistente.ItemSelecionado Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstItens_DblClick(ByVal Cancel As MSForms.ReturnBoolean)" & vbCrLf
    s = s & "    modAssistente.TrocarItem Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnVerComp_Click()" & vbCrLf
    s = s & "    modAssistente.VerComposicaoReferencia Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnManual_Click()" & vbCrLf
    s = s & "    modAssistente.PesquisaManual Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnNenhum_Click()" & vbCrLf
    s = s & "    modAssistente.NenhumCorresponde Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnTrocar_Click()" & vbCrLf
    s = s & "    modAssistente.TrocarItem Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnExcluir_Click()" & vbCrLf
    s = s & "    modAssistente.ExcluirItem Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnMenos_Click()" & vbCrLf
    s = s & "    modAssistente.AjustarCoeficiente Me, 0.9" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnMais_Click()" & vbCrLf
    s = s & "    modAssistente.AjustarCoeficiente Me, 1.1" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnAplicar_Click()" & vbCrLf
    s = s & "    modAssistente.AplicarCoeficiente Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub txtCoef_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, " & _
            "ByVal Shift As Integer)" & vbCrLf
    s = s & "    If KeyCode = 13 Then modAssistente.AplicarCoeficiente Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnVoltar_Click()" & vbCrLf
    s = s & "    modAssistente.Voltar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnProximo_Click()" & vbCrLf
    s = s & "    modAssistente.Avancar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnSalvar_Click()" & vbCrLf
    s = s & "    modAssistente.Gravar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnFechar_Click()" & vbCrLf
    s = s & "    Unload Me" & vbCrLf
    s = s & "End Sub" & vbCrLf
    comp.CodeModule.AddFromString s
End Sub

'==============================================================================
' frmEscolherItem - trocar o material ou equipamento de um insumo
'==============================================================================

Private Sub ConstruirEscolherItem()
    Dim comp As Object, f As Object, c As Object

    Set comp = NovoFormulario("frmEscolherItem", _
        "Escolher o item da base da empresa", 620, 440)
    Set f = comp.Designer

    Rotulo f, "lblTitulo", "Insumo da composicao de referencia", _
           12, 8, 580, 16, 11, True, COR_TITULO
    Set c = Rotulo(f, "lblInsumoRef", "", 12, 28, 590, 30, 9)
    c.BackColor = COR_PAINEL

    Rotulo f, "lblAjuda", _
        "Escolha o item da base da empresa que corresponde ao insumo acima. " & _
        "A coluna Conversao mostra como a unidade sera convertida.", _
        12, 62, 590, 24, 8, False, COR_TEXTO

    Rotulo f, "lblBuscaRot", "Procurar:", 12, 92, 50, 14
    Caixa f, "txtBusca", 64, 90, 380
    Botao f, "btnBuscar", "Procurar", 450, 89, 90, 20

    Lista f, "lstCandidatos", 12, 116, 590, 170, 6, "40;46;250;30;66;150"

    Set c = Rotulo(f, "lblDetalhe", "", 12, 292, 590, 56, 8)
    c.BackColor = COR_PAINEL

    Botao f, "btnConfirmar", "USAR ESTE ITEM", 12, 356, 150, 26
    Botao f, "btnSemCorrespondente", "Nenhum corresponde", 170, 356, 150, 26
    Botao f, "btnCancelar", "Cancelar", 514, 356, 88, 26

    InserirCodigoEscolherItem comp
End Sub

Private Sub InserirCodigoEscolherItem(ByVal comp As Object)
    Dim s As String
    s = "Option Explicit" & vbCrLf & vbCrLf
    s = s & "Public Escolhido As String" & vbCrLf
    s = s & "Public SemCorrespondente As Boolean" & vbCrLf & vbCrLf
    s = s & "Private Sub UserForm_Initialize()" & vbCrLf
    s = s & "    modEscolherItem.Iniciar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnBuscar_Click()" & vbCrLf
    s = s & "    modEscolherItem.Procurar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub txtBusca_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, " & _
            "ByVal Shift As Integer)" & vbCrLf
    s = s & "    If KeyCode = 13 Then modEscolherItem.Procurar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstCandidatos_Click()" & vbCrLf
    s = s & "    modEscolherItem.Selecionado Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub lstCandidatos_DblClick(ByVal Cancel As MSForms.ReturnBoolean)" & vbCrLf
    s = s & "    modEscolherItem.Confirmar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnConfirmar_Click()" & vbCrLf
    s = s & "    modEscolherItem.Confirmar Me" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnSemCorrespondente_Click()" & vbCrLf
    s = s & "    Me.SemCorrespondente = True" & vbCrLf
    s = s & "    Me.Hide" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Private Sub btnCancelar_Click()" & vbCrLf
    s = s & "    Me.Escolhido = """"" & vbCrLf
    s = s & "    Me.Hide" & vbCrLf
    s = s & "End Sub" & vbCrLf
    comp.CodeModule.AddFromString s
End Sub
