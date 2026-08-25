Attribute VB_Name = "modUtils"
'==============================================================================
' modUtils - Utilitarios de planilha e formatacao
'==============================================================================
Option Explicit

Public Const COR_CABECALHO As Long = 4210752      ' cinza escuro
Public Const COR_TEXTO_CABECALHO As Long = 16777215
Public Const COR_FORTE As Long = 13561798         ' verde claro
Public Const COR_PROVAVEL As Long = 10086143      ' amarelo claro
Public Const COR_BAIXA As Long = 12040422         ' laranja claro
Public Const COR_VALIDADO As Long = 15773696      ' azul
Public Const COR_ALERTA As Long = 13551615        ' vermelho claro
Public Const COR_ZEBRA As Long = 15921906

Public Function Aba(ByVal nome As String) As Worksheet
    On Error Resume Next
    Set Aba = ThisWorkbook.Worksheets(nome)
    On Error GoTo 0
End Function

Public Sub LimparAba(ByVal ws As Worksheet, Optional ByVal primeiraLinha As Long = 1)
    Dim ultima As Long
    If ws Is Nothing Then Exit Sub
    On Error Resume Next
    ws.Cells.Validation.Delete
    On Error GoTo 0
    ultima = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If ultima < primeiraLinha Then ultima = primeiraLinha
    ws.Range(ws.Rows(primeiraLinha), ws.Rows(WorksheetFunction.Max(ultima, primeiraLinha) + 400)).Clear
End Sub

Public Sub EscreverCabecalho(ByVal ws As Worksheet, ByVal linha As Long, _
                             ByVal titulos As Variant)
    Dim i As Long
    For i = LBound(titulos) To UBound(titulos)
        With ws.Cells(linha, i - LBound(titulos) + 1)
            .Value = titulos(i)
            .Font.Bold = True
            .Font.Color = COR_TEXTO_CABECALHO
            .Interior.Color = COR_CABECALHO
            .HorizontalAlignment = xlLeft
        End With
    Next i
    ws.Rows(linha).RowHeight = 20
End Sub

Public Sub AjustarColunas(ByVal ws As Worksheet, ByVal ateColuna As Long, _
                          Optional ByVal larguraMaxima As Double = 62)
    Dim i As Long
    On Error Resume Next
    ws.Columns(1).Resize(, ateColuna).AutoFit
    For i = 1 To ateColuna
        If ws.Columns(i).ColumnWidth > larguraMaxima Then
            ws.Columns(i).ColumnWidth = larguraMaxima
        End If
    Next i
    On Error GoTo 0
End Sub

Public Function CorDaConfianca(ByVal confianca As String) As Long
    Select Case UCase$(confianca)
        Case "VALIDADO": CorDaConfianca = COR_VALIDADO
        Case "FORTE": CorDaConfianca = COR_FORTE
        Case "PROVAVEL": CorDaConfianca = COR_PROVAVEL
        Case "BAIXA": CorDaConfianca = COR_BAIXA
        Case Else: CorDaConfianca = COR_ALERTA
    End Select
End Function

Public Sub AplicarZebra(ByVal ws As Worksheet, ByVal primeira As Long, _
                        ByVal ultima As Long, ByVal colunas As Long)
    Dim i As Long
    For i = primeira To ultima
        If (i - primeira) Mod 2 = 1 Then
            ws.Range(ws.Cells(i, 1), ws.Cells(i, colunas)).Interior.Color = COR_ZEBRA
        End If
    Next i
End Sub

Public Function FormatarMoeda(ByVal valor As Double) As String
    FormatarMoeda = Format$(valor, "R$ #,##0.00")
End Function

Public Function FormatarPercentual(ByVal valor As Double) As String
    FormatarPercentual = Format$(valor, "0.0") & "%"
End Function

Public Function TextoCurto(ByVal texto As String, ByVal limite As Long) As String
    If Len(texto) <= limite Then
        TextoCurto = texto
    Else
        TextoCurto = Left$(texto, limite - 1) & ChrW$(8230)
    End If
End Function

Public Sub Aguardar(ByVal ligado As Boolean)
    Application.ScreenUpdating = Not ligado
    Application.EnableEvents = Not ligado
    If ligado Then
        Application.Cursor = xlWait
    Else
        Application.Cursor = xlDefault
        Application.StatusBar = False
    End If
End Sub

Public Sub Avisar(ByVal mensagem As String, Optional ByVal titulo As String = "Sistema de Composicoes")
    MsgBox mensagem, vbInformation, titulo
End Sub

Public Sub AvisarErro(ByVal mensagem As String, Optional ByVal titulo As String = "Erro")
    MsgBox mensagem, vbCritical, titulo
End Sub

Public Function Confirmar(ByVal mensagem As String, _
                          Optional ByVal titulo As String = "Confirmar") As Boolean
    Confirmar = (MsgBox(mensagem, vbYesNo + vbQuestion, titulo) = vbYes)
End Function

Public Sub IrPara(ByVal nomeAba As String)
    Dim ws As Worksheet
    Set ws = Aba(nomeAba)
    If Not ws Is Nothing Then
        ws.Activate
        ws.Range("A1").Select
    End If
End Sub

Public Function CelulaTexto(ByVal ws As Worksheet, ByVal endereco As String) As String
    On Error Resume Next
    CelulaTexto = Trim$(CStr(ws.Range(endereco).Value))
    On Error GoTo 0
End Function
