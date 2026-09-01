Attribute VB_Name = "modUI"
'==============================================================================
' modUI - Construcao dos botoes das abas
'
' Os botoes sao criados por codigo para que o .xlsm possa ser reconstruido
' do zero a partir do repositorio, sem depender de um arquivo binario com
' controles ja desenhados.
'==============================================================================
Option Explicit

Public Sub ReconstruirBotoes()
    ' Silenciosa de proposito: e chamada pelo instalar_vba.vbs com o Excel
    ' invisivel, e um MsgBox ali travaria a instalacao numa janela que
    ' ninguem ve.
    LimparBotoes
    CriarBotoesInicio
    CriarBotoesServicos
    CriarBotoesCorrespondencia
    CriarBotoesComposicao
    CriarBotoesBanco
    CriarBotoesPendencias
    CriarBotoesConfiguracao
End Sub

Public Sub ReconstruirBotoesComAviso()
    ' Versao para o botao da aba CONFIGURACAO, onde ha alguem olhando.
    ReconstruirBotoes
    modUtils.Avisar "Botoes reconstruidos em todas as abas."
End Sub

Private Sub LimparBotoes()
    Dim ws As Worksheet, sh As Shape, i As Long
    On Error Resume Next
    For Each ws In ThisWorkbook.Worksheets
        For i = ws.Shapes.Count To 1 Step -1
            Set sh = ws.Shapes(i)
            If sh.Type = msoFormControl Or sh.Name Like "btn*" Then sh.Delete
        Next i
    Next ws
    On Error GoTo 0
End Sub

Private Sub Botao(ByVal ws As Worksheet, ByVal esquerda As Double, _
                  ByVal topo As Double, ByVal largura As Double, _
                  ByVal texto As String, ByVal macro As String)
    ' Usa Shapes.AddFormControl e escreve o texto por TextFrame: atribuir
    ' .Caption direto no objeto Button falha em algumas versoes do Excel, e
    ' o erro abortava a criacao dos botoes seguintes - deixando um unico
    ' botao com a legenda padrao "Botao 1".
    Const xlButtonControl As Long = 0
    Dim sh As Shape
    On Error Resume Next

    Set sh = ws.Shapes.AddFormControl(xlButtonControl, esquerda, topo, largura, 26)
    If sh Is Nothing Then Exit Sub

    sh.OnAction = macro
    sh.Name = "btn" & Replace(macro, ".", "_")

    sh.TextFrame.Characters.Text = texto
    If Err.Number <> 0 Then
        Err.Clear
        sh.TextFrame2.TextRange.Text = texto     ' alternativa
        Err.Clear
    End If

    sh.TextFrame.Characters.Font.Size = 9
    sh.TextFrame.HorizontalAlignment = xlHAlignCenter
    Err.Clear
    On Error GoTo 0
End Sub

Private Sub CriarBotoesInicio()
    ' O assistente vem primeiro e maior de proposito: e o caminho que o
    ' usuario deve seguir. O resto sao ferramentas de apoio.
    Dim ws As Worksheet, b As Object
    Set ws = modUtils.Aba(modMain.ABA_INICIO)
    If ws Is Nothing Then Exit Sub

    Set b = BotaoGrande(ws, 420, 108, 260, 44, _
                        "COMECAR - ASSISTENTE DE COMPOSICAO", _
                        "modMain.BotaoAssistente")

    Botao ws, 420, 160, 128, "Pendencias", "modMain.BotaoRevisarPendencias"
    Botao ws, 552, 160, 128, "Banco de composicoes", "modMain.BotaoBancoComposicoes"
    Botao ws, 420, 192, 128, "Lista de servicos", "modMain.BotaoIniciarCorrespondencia"
    Botao ws, 552, 192, 128, "Analisar em lote", "modMain.BotaoAnalisarLote"
    Botao ws, 420, 224, 128, "Atualizar bases", "modMain.BotaoAtualizarBases"
    Botao ws, 552, 224, 128, "Configuracoes", "modMain.BotaoConfiguracoes"
    Botao ws, 420, 256, 128, "Como usar", "modMain.BotaoAjuda"
    Botao ws, 552, 256, 128, "Log de auditoria", "modMain.BotaoLog"
    Botao ws, 420, 288, 128, "Testar motor", "modMain.BotaoTestarMotor"
    Botao ws, 552, 288, 128, "Diagnostico", "modPythonBridge.MostrarDiagnostico"
End Sub

Private Function BotaoGrande(ByVal ws As Worksheet, ByVal esquerda As Double, _
                             ByVal topo As Double, ByVal largura As Double, _
                             ByVal altura As Double, ByVal texto As String, _
                             ByVal macro As String) As Object
    Const xlButtonControl As Long = 0
    Dim sh As Shape
    On Error Resume Next
    Set sh = ws.Shapes.AddFormControl(xlButtonControl, esquerda, topo, largura, altura)
    If sh Is Nothing Then Exit Function
    sh.OnAction = macro
    sh.Name = "btn" & Replace(macro, ".", "_")
    sh.TextFrame.Characters.Text = texto
    If Err.Number <> 0 Then
        Err.Clear
        sh.TextFrame2.TextRange.Text = texto
        Err.Clear
    End If
    sh.TextFrame.Characters.Font.Size = 11
    sh.TextFrame.Characters.Font.Bold = True
    sh.TextFrame.HorizontalAlignment = xlHAlignCenter
    Err.Clear
    On Error GoTo 0
    Set BotaoGrande = sh
End Function

Private Sub CriarBotoesServicos()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modServices.ABA_SERVICOS)
    If ws Is Nothing Then Exit Sub
    Botao ws, 460, 12, 150, "APLICAR FILTROS", "modServices.CarregarServicos"
    Botao ws, 460, 44, 150, "BUSCAR CORRESPONDENCIA", "modServices.SelecionarServicoDaLinha"
    Botao ws, 780, 12, 150, "ABRIR ASSISTENTE", "modMain.BotaoAssistente"
    Botao ws, 620, 12, 150, "ANALISAR EM LOTE", "modServices.AnalisarTodosOsServicos"
    Botao ws, 620, 44, 150, "VOLTAR AO INICIO", "modMain.Auto_Open"
End Sub

Private Sub CriarBotoesCorrespondencia()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modServices.ABA_CORRESP)
    If ws Is Nothing Then Exit Sub
    Botao ws, 700, 12, 150, "BUSCAR", "modServices.BuscarCorrespondencia"
    Botao ws, 700, 44, 150, "ESCOLHER", "modServices.EscolherCorrespondencia"
    Botao ws, 860, 12, 150, "VER COMPOSICAO", "modServices.VerComposicaoDaLinha"
    Botao ws, 860, 44, 150, "PESQUISA MANUAL", "modServices.PesquisaManual"
    Botao ws, 1020, 12, 150, "NENHUM CORRESPONDE", "modServices.NenhumCorresponde"
    Botao ws, 1020, 44, 150, "VOLTAR AO INICIO", "modMain.Auto_Open"
End Sub

Private Sub CriarBotoesComposicao()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modCompositions.ABA_COMPOSICAO)
    If ws Is Nothing Then Exit Sub
    Botao ws, 700, 12, 170, "MONTAR COMPOSICAO PROPRIA", "modCompositions.MontarComposicaoPropria"
    Botao ws, 700, 44, 170, "SUGESTOES PARA O INSUMO", "modMaterials.BuscarMaterialDaLinha"
    Botao ws, 880, 12, 170, "CADASTRAR CONVERSAO", "modMaterials.CadastrarConversao"
    Botao ws, 880, 44, 170, "SALVAR COMPOSICAO", "modMaterials.SalvarComposicao"
End Sub

Private Sub CriarBotoesBanco()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modCompositions.ABA_BANCO)
    If ws Is Nothing Then Exit Sub
    Botao ws, 620, 12, 150, "ATUALIZAR LISTA", "modCompositions.CarregarBancoComposicoes"
    Botao ws, 620, 44, 150, "VOLTAR AO INICIO", "modMain.Auto_Open"
End Sub

Private Sub CriarBotoesPendencias()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modDatabaseUI.ABA_PENDENCIAS)
    If ws Is Nothing Then Exit Sub
    Botao ws, 620, 12, 150, "ATUALIZAR LISTA", "modDatabaseUI.CarregarPendencias"
    Botao ws, 620, 44, 150, "MARCAR RESOLVIDA", "modDatabaseUI.ResolverPendenciaSelecionada"
    Botao ws, 780, 12, 150, "IGNORAR", "modDatabaseUI.IgnorarPendenciaSelecionada"
    Botao ws, 780, 44, 150, "HISTORICO DE VINCULOS", "modDatabaseUI.VerHistoricoVinculos"
End Sub

Private Sub CriarBotoesConfiguracao()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modConfig.ABA_CONFIG)
    If ws Is Nothing Then Exit Sub
    Botao ws, 620, 12, 150, "RECARREGAR", "modConfig.CarregarConfiguracao"
    Botao ws, 620, 44, 150, "SALVAR CONFIGURACAO", "modConfig.SalvarConfiguracao"
    Botao ws, 780, 12, 150, "ATUALIZAR BASES", "modConfig.AtualizarBases"
    Botao ws, 780, 44, 150, "RECONSTRUIR BOTOES", "modUI.ReconstruirBotoesComAviso"
End Sub
