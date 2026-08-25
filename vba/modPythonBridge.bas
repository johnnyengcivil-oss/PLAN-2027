Attribute VB_Name = "modPythonBridge"
'==============================================================================
' modPythonBridge - Ponte VBA -> Python (itens 46, 47, 48)
'
' O VBA nunca processa milhares de linhas: monta um pedido JSON, chama o
' motor e le a resposta. Toda a leitura de bases, matching, expansao,
' conversao e calculo acontece no Python.
'
' A comunicacao e por ARQUIVO, nao por linha de comando:
'   - nao esbarra no limite de tamanho do comando;
'   - nao sofre com aspas nem com pagina de codigo do Windows;
'   - permite gravar o pedido para depuracao.
'
' Todos os caminhos derivam de ThisWorkbook.Path. Nada e absoluto.
'==============================================================================
Option Explicit

Private Const PASTA_TEMP As String = "_temp"
Private Const TIMEOUT_PADRAO As Long = 600      ' segundos

'--------------------------------------------------------------- caminhos

Public Function RaizSistema() As String
    RaizSistema = ThisWorkbook.Path
End Function

Public Function CaminhoMotor() As String
    ' Preferencia: executavel empacotado. Em desenvolvimento, usa o Python
    ' do sistema com python\main.py (item 61).
    Dim fso As Object, base As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    base = RaizSistema()

    If fso.FileExists(base & "\motor.exe") Then
        CaminhoMotor = """" & base & "\motor.exe"""
    ElseIf fso.FileExists(base & "\motor\motor.exe") Then
        CaminhoMotor = """" & base & "\motor\motor.exe"""
    ElseIf fso.FileExists(base & "\python\main.py") Then
        CaminhoMotor = ExecutavelPython() & " """ & base & "\python\main.py"""
    Else
        CaminhoMotor = ""
    End If
End Function

Private Function ExecutavelPython() As String
    Dim fso As Object, base As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    base = RaizSistema()
    ' Ambiente virtual local tem prioridade: nao depende do PATH do usuario.
    If fso.FileExists(base & "\.venv\Scripts\python.exe") Then
        ExecutavelPython = """" & base & "\.venv\Scripts\python.exe"""
    ElseIf fso.FileExists(base & "\python\.venv\Scripts\python.exe") Then
        ExecutavelPython = """" & base & "\python\.venv\Scripts\python.exe"""
    Else
        ExecutavelPython = "python"
    End If
End Function

Private Function PastaTemp() As String
    Dim fso As Object, caminho As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    caminho = RaizSistema() & "\" & PASTA_TEMP
    If Not fso.FolderExists(caminho) Then fso.CreateFolder caminho
    PastaTemp = caminho
End Function

'--------------------------------------------------------------- chamada

Public Function Chamar(ByVal pedidoJson As String, _
                       Optional ByVal timeoutSeg As Long = TIMEOUT_PADRAO) As Object
    ' Devolve o dicionario da resposta. Em caso de falha, devolve um
    ' dicionario com status="erro" e "erro" preenchido - o chamador nunca
    ' precisa tratar excecao.
    Dim fso As Object, wsh As Object
    Dim arqPedido As String, arqResposta As String
    Dim comando As String, codigo As Long, respostaTexto As String
    Dim motor As String
    Dim erroDic As Object

    On Error GoTo TratarErro
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set wsh = CreateObject("WScript.Shell")

    motor = CaminhoMotor()
    If Len(motor) = 0 Then
        Set Chamar = RespostaErro( _
            "Motor nao encontrado. Esperado motor.exe ou python\main.py em: " _
            & RaizSistema())
        Exit Function
    End If

    arqPedido = PastaTemp() & "\pedido.json"
    arqResposta = PastaTemp() & "\resposta.json"
    GravarUtf8 arqPedido, pedidoJson
    If fso.FileExists(arqResposta) Then fso.DeleteFile arqResposta, True

    comando = motor & " --pedido """ & arqPedido & """" & _
              " --resposta """ & arqResposta & """" & _
              " --raiz """ & RaizSistema() & """"

    Application.StatusBar = "Processando no motor Python..."
    codigo = wsh.Run("cmd /c " & comando, 0, True)   ' 0 = janela oculta, True = aguarda
    Application.StatusBar = False

    If Not fso.FileExists(arqResposta) Then
        Set Chamar = RespostaErro( _
            "O motor nao gerou resposta (codigo " & codigo & "). Comando: " & comando)
        Exit Function
    End If

    respostaTexto = LerUtf8(arqResposta)
    If Len(Trim$(respostaTexto)) = 0 Then
        Set Chamar = RespostaErro("Resposta vazia do motor.")
        Exit Function
    End If

    Set Chamar = modJson.Parse(respostaTexto)
    Exit Function

TratarErro:
    Application.StatusBar = False
    Set Chamar = RespostaErro("Falha na ponte VBA/Python: " & Err.Description)
End Function

Public Function ChamarAcao(ByVal acao As String, _
                           ParamArray pares() As Variant) As Object
    ' ChamarAcao("buscar_servico", "codigo_empresa", modJson.Texto("140006"))
    Dim i As Long, sb As String
    sb = "{""acao"":" & modJson.Texto(acao)
    For i = LBound(pares) To UBound(pares) Step 2
        sb = sb & "," & modJson.Texto(CStr(pares(i))) & ":" & CStr(pares(i + 1))
    Next i
    sb = sb & "}"
    Set ChamarAcao = Chamar(sb)
End Function

Public Function RespostaErro(ByVal mensagem As String) As Object
    Dim dic As Object
    Set dic = modJson.NovoDicionario
    dic("status") = "erro"
    dic("erro") = mensagem
    Set RespostaErro = dic
End Function

Public Function DeuCerto(ByVal resposta As Object) As Boolean
    If resposta Is Nothing Then Exit Function
    DeuCerto = (modJson.ObterTexto(resposta, "status") = "ok")
End Function

Public Function MensagemErro(ByVal resposta As Object) As String
    MensagemErro = modJson.ObterTexto(resposta, "erro", "Erro desconhecido.")
End Function

'------------------------------------------------------- arquivos UTF-8

Private Sub GravarUtf8(ByVal caminho As String, ByVal conteudo As String)
    Dim fluxo As Object
    Set fluxo = CreateObject("ADODB.Stream")
    fluxo.Type = 2                    ' texto
    fluxo.Charset = "utf-8"
    fluxo.Open
    fluxo.WriteText conteudo
    ' Remove o BOM: o Python le utf-8-sig, mas outros consumidores nao.
    fluxo.Position = 3
    Dim semBom As Object
    Set semBom = CreateObject("ADODB.Stream")
    semBom.Type = 1                   ' binario
    semBom.Open
    fluxo.CopyTo semBom
    semBom.SaveToFile caminho, 2      ' sobrescreve
    semBom.Close
    fluxo.Close
End Sub

Private Function LerUtf8(ByVal caminho As String) As String
    Dim fluxo As Object
    Set fluxo = CreateObject("ADODB.Stream")
    fluxo.Type = 2
    fluxo.Charset = "utf-8"
    fluxo.Open
    fluxo.LoadFromFile caminho
    LerUtf8 = fluxo.ReadText
    fluxo.Close
End Function

'------------------------------------------------------------- diagnostico

Public Sub TestarConexao()
    Dim r As Object
    Set r = ChamarAcao("status")
    If DeuCerto(r) Then
        Dim ind As Object
        Set ind = modJson.ObterObjeto(r, "indicadores")
        MsgBox "Motor respondendo." & vbCrLf & vbCrLf & _
               "Backend semantico: " & modJson.ObterTexto(r, "backend_semantico") & vbCrLf & _
               "Servicos da empresa: " & modJson.ObterNumero(ind, "servicos_empresa") & vbCrLf & _
               "Materiais: " & modJson.ObterNumero(ind, "materiais_base") & vbCrLf & _
               "Composicoes de referencia: " & modJson.ObterNumero(ind, "composicoes_referencia"), _
               vbInformation, "Conexao com o motor"
    Else
        MsgBox "Falha: " & MensagemErro(r), vbCritical, "Conexao com o motor"
    End If
End Sub
