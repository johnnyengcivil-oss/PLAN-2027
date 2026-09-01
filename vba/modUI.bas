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
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modMain.ABA_INICIO)
    If ws Is Nothing Then Exit Sub
    Botao ws, 420, 120, 190, "INICIAR CORRESPONDENCIA", "modMain.BotaoIniciarCorrespondencia"
    Botao ws, 420, 152, 190, "REVISAR PENDENCIAS", "modMain.BotaoRevisarPendencias"
    Botao ws, 420, 184, 190, "BANCO DE COMPOSICOES", "modMain.BotaoBancoComposicoes"
    Botao ws, 420, 216, 190, "ATUALIZAR BASES", "modMain.BotaoAtualizarBases"
    Botao ws, 420, 248, 190, "CONFIGURACOES", "modMain.BotaoConfiguracoes"
    Botao ws, 420, 280, 190, "LOG", "modMain.BotaoLog"
    Botao ws, 420, 312, 190, "ANALISAR EM LOTE", "modMain.BotaoAnalisarLote"
    Botao ws, 420, 344, 190, "TESTAR MOTOR", "modMain.BotaoTestarMotor"
    Botao ws, 420, 376, 190, "DIAGNOSTICO DO MOTOR", "modPythonBridge.MostrarDiagnostico"
End Sub

Private Sub CriarBotoesServicos()
    Dim ws As Worksheet
    Set ws = modUtils.Aba(modServices.ABA_SERVICOS)
    If ws Is Nothing Then Exit Sub
    Botao ws, 460, 12, 150, "APLICAR FILTROS", "modServices.CarregarServicos"
    Botao ws, 460, 44, 150, "BUSCAR CORRESPONDENCIA", "modServices.SelecionarServicoDaLinha"
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
