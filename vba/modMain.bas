Attribute VB_Name = "modMain"
'==============================================================================
' modMain - Tela INICIO e navegacao (itens 8 e 46)
'
' Este e o unico modulo que os botoes da planilha chamam diretamente.
'==============================================================================
Option Explicit

Public Const ABA_INICIO As String = "INICIO"

Public Sub AtualizarInicio()
    ' Preenche os indicadores da tela INICIO (item 8).
    Dim ws As Worksheet, r As Object, ind As Object, bases As Collection
    Dim item As Object, i As Long, linha As Long

    Set ws = modUtils.Aba(ABA_INICIO)
    If ws Is Nothing Then Exit Sub

    modUtils.Aguardar True
    Set r = modPythonBridge.ChamarAcao("status")
    modUtils.Aguardar False

    If Not modPythonBridge.DeuCerto(r) Then
        ws.Range("C8").Value = "MOTOR INDISPONIVEL"
        ws.Range("C6").Interior.Color = modUtils.COR_ALERTA
        ws.Range("C9").Value = modPythonBridge.MensagemErro(r)
        Exit Sub
    End If

    modUtils.Aguardar True
    Set ind = modJson.ObterObjeto(r, "indicadores")

    ws.Range("C6").Value = "OK"
    ws.Range("C6").Interior.Color = modUtils.COR_FORTE
    ws.Range("C7").Value = modJson.ObterTexto(r, "backend_semantico")

    ws.Range("C12").Value = modJson.ObterNumero(ind, "servicos_empresa")
    ws.Range("C13").Value = modJson.ObterNumero(ind, "servicos_vinculados")
    ws.Range("C14").Value = modJson.ObterNumero(ind, "servicos_pendentes")
    ws.Range("C16").Value = modJson.ObterNumero(ind, "composicoes_proprias")
    ws.Range("C17").Value = modJson.ObterNumero(ind, "composicoes_completas")
    ws.Range("C18").Value = modJson.ObterNumero(ind, "composicoes_pendentes")
    ws.Range("C19").Value = modJson.ObterNumero(ind, "composicoes_revisar")
    ws.Range("C21").Value = modJson.ObterNumero(ind, "materiais_vinculados")
    ws.Range("C22").Value = modJson.ObterNumero(ind, "equipamentos_vinculados")
    ws.Range("C23").Value = modJson.ObterNumero(ind, "pendencias_abertas")
    ws.Range("C25").Value = modJson.ObterNumero(ind, "materiais_base")
    ws.Range("C26").Value = modJson.ObterNumero(ind, "composicoes_referencia")

    ' Bases carregadas, com data-base e como cada uma foi identificada.
    linha = 30
    ws.Range(ws.Cells(linha, 2), ws.Cells(linha + 8, 6)).ClearContents
    modUtils.EscreverCabecalho ws, linha, _
        Array("", "BASE", "ARQUIVO", "DATA-BASE", "REGISTROS", "IDENTIFICADA POR")
    Set bases = modJson.ObterLista(r, "bases")
    For i = 1 To bases.Count
        Set item = bases(i)
        ws.Cells(linha + i, 2).Value = modJson.ObterTexto(item, "papel")
        ws.Cells(linha + i, 3).Value = modJson.ObterTexto(item, "nome_arquivo")
        ws.Cells(linha + i, 4).Value = modJson.ObterTexto(item, "data_base")
        ws.Cells(linha + i, 5).Value = modJson.ObterNumero(item, "registros")
        ws.Cells(linha + i, 6).Value = modJson.ObterTexto(item, "detectado_por")
    Next i
    modUtils.Aguardar False
End Sub

'------------------------------------------------------------ botoes

Public Sub BotaoAssistente()
    ' A porta de entrada do sistema. Conduz o usuario do servico ate a
    ' composicao gravada, explicando cada passo.
    modAssistente.Abrir
End Sub

Public Sub BotaoIniciarCorrespondencia()
    modUtils.IrPara modServices.ABA_SERVICOS
    modServices.CarregarServicos
End Sub

Public Sub BotaoRevisarPendencias()
    modUtils.IrPara modDatabaseUI.ABA_PENDENCIAS
    modDatabaseUI.CarregarPendencias
End Sub

Public Sub BotaoBancoComposicoes()
    modUtils.IrPara modCompositions.ABA_BANCO
    modCompositions.CarregarBancoComposicoes
End Sub

Public Sub BotaoAtualizarBases()
    modConfig.AtualizarBases
End Sub

Public Sub BotaoConfiguracoes()
    modUtils.IrPara modConfig.ABA_CONFIG
    modConfig.CarregarConfiguracao
End Sub

Public Sub BotaoLog()
    modUtils.IrPara modConfig.ABA_LOG
    modConfig.CarregarLog
End Sub

Public Sub BotaoTestarMotor()
    modPythonBridge.TestarConexao
End Sub

Public Sub BotaoAnalisarLote()
    modServices.AnalisarTodosOsServicos
End Sub

'------------------------------------------------------------ abertura

Public Sub Auto_Open()
    On Error Resume Next
    modUtils.IrPara ABA_INICIO
    AtualizarInicio
End Sub

Public Sub BotaoAjuda()
    modUtils.IrPara "AJUDA"
End Sub
