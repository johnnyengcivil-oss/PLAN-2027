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
    ' Monta o comando que executa o motor. Procura, nesta ordem:
    '   1. motor.exe empacotado (item 61)
    '   2. python\main.py, a partir da pasta do .xlsm
    '
    ' A busca do main.py nao se limita a pasta do .xlsm: o arquivo pode ter
    ' sido movido para fora, ou o ZIP ter sido extraido criando uma
    ' subpasta. Por isso tambem olha um nivel acima e as subpastas.
    Dim fso As Object, base As String, script As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    base = RaizSistema()

    If fso.FileExists(base & "\motor.exe") Then
        CaminhoMotor = """" & base & "\motor.exe"""
        Exit Function
    End If
    If fso.FileExists(base & "\motor\motor.exe") Then
        CaminhoMotor = """" & base & "\motor\motor.exe"""
        Exit Function
    End If

    script = LocalizarScript()
    If Len(script) > 0 Then
        CaminhoMotor = ExecutavelPython() & " """ & script & """"
    Else
        CaminhoMotor = ""
    End If
End Function

Public Function LocalizarScript() As String
    ' Caminho completo de python\main.py, ou vazio.
    '
    ' Procura em varios lugares de proposito: o .xlsm pode ter sido movido,
    ' ou o ZIP extraido criando uma pasta a mais. Ordem: a pasta do
    ' arquivo, dois niveis acima e dois niveis de subpastas.
    Dim base As String
    base = RaizSistema()

    LocalizarScript = ProcurarEm(base)
    If Len(LocalizarScript) > 0 Then Exit Function

    Dim fso As Object, pai As String, avo As String
    Set fso = CreateObject("Scripting.FileSystemObject")

    pai = PastaPai(base)
    If Len(pai) > 0 Then
        LocalizarScript = ProcurarEm(pai)
        If Len(LocalizarScript) > 0 Then Exit Function
        avo = PastaPai(pai)
        If Len(avo) > 0 Then
            LocalizarScript = ProcurarEm(avo)
            If Len(LocalizarScript) > 0 Then Exit Function
        End If
    End If

    LocalizarScript = ProcurarNasSubpastas(base, 2)
End Function

Private Function ProcurarEm(ByVal pasta As String) As String
    Dim fso As Object
    If Len(pasta) = 0 Then Exit Function
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FileExists(pasta & "\python\main.py") Then
        ProcurarEm = pasta & "\python\main.py"
    End If
End Function

Private Function ProcurarNasSubpastas(ByVal pasta As String, _
                                      ByVal profundidade As Long) As String
    Dim fso As Object, subPasta As Object, achado As String
    If profundidade <= 0 Or Len(pasta) = 0 Then Exit Function
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FolderExists(pasta) Then Exit Function

    On Error Resume Next
    For Each subPasta In fso.GetFolder(pasta).SubFolders
        achado = ProcurarEm(subPasta.Path)
        If Len(achado) > 0 Then
            ProcurarNasSubpastas = achado
            Exit Function
        End If
    Next subPasta
    For Each subPasta In fso.GetFolder(pasta).SubFolders
        achado = ProcurarNasSubpastas(subPasta.Path, profundidade - 1)
        If Len(achado) > 0 Then
            ProcurarNasSubpastas = achado
            Exit Function
        End If
    Next subPasta
    On Error GoTo 0
End Function

Private Function PastaPai(ByVal pasta As String) As String
    Dim fso As Object
    If Len(pasta) = 0 Then Exit Function
    Set fso = CreateObject("Scripting.FileSystemObject")
    On Error Resume Next
    PastaPai = fso.GetParentFolderName(pasta)
    On Error GoTo 0
End Function

Public Function ExecutavelPython() As String
    ' Descobre o interpretador, na mesma ordem do _localizar_python.bat:
    '   1. python-portatil\python.exe    (vem dentro do pacote)
    '   2. python-portatil\<subpasta>\python.exe
    '   3. .venv\Scripts\python.exe
    '   4. python do PATH
    Dim fso As Object, base As String, pasta As Object, subPasta As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    base = PastaDoSistema()

    If fso.FileExists(base & "\python-portatil\python.exe") Then
        ExecutavelPython = """" & base & "\python-portatil\python.exe"""
        Exit Function
    End If

    If fso.FolderExists(base & "\python-portatil") Then
        Set pasta = fso.GetFolder(base & "\python-portatil")
        For Each subPasta In pasta.SubFolders
            If fso.FileExists(subPasta.Path & "\python.exe") Then
                ExecutavelPython = """" & subPasta.Path & "\python.exe"""
                Exit Function
            End If
        Next subPasta
    End If

    If fso.FileExists(base & "\.venv\Scripts\python.exe") Then
        ExecutavelPython = """" & base & "\.venv\Scripts\python.exe"""
        Exit Function
    End If

    ExecutavelPython = "python"
End Function

Public Function PastaDoSistema() As String
    ' Pasta que realmente contem o sistema: a do main.py localizado, que
    ' pode nao ser a do .xlsm.
    Dim fso As Object, script As String
    script = LocalizarScript()
    If Len(script) = 0 Then
        PastaDoSistema = RaizSistema()
        Exit Function
    End If
    Set fso = CreateObject("Scripting.FileSystemObject")
    PastaDoSistema = fso.GetParentFolderName(fso.GetParentFolderName(script))
End Function

Private Function PastaTemp() As String
    Dim fso As Object, caminho As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    caminho = PastaDoSistema() & "\" & PASTA_TEMP
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
        Set Chamar = RespostaErro(DiagnosticoMotor())
        Exit Function
    End If

    arqPedido = PastaTemp() & "\pedido.json"
    arqResposta = PastaTemp() & "\resposta.json"
    GravarUtf8 arqPedido, pedidoJson
    If fso.FileExists(arqResposta) Then fso.DeleteFile arqResposta, True

    comando = motor & " --pedido """ & arqPedido & """" & _
              " --resposta """ & arqResposta & """" & _
              " --raiz """ & PastaDoSistema() & """"

    ' Executa o interpretador DIRETAMENTE, sem "cmd /c". O cmd, ao receber
    ' um comando que comeca com aspas, remove o primeiro e o ultimo
    ' caractere de aspas da linha inteira, o que corrompia o ultimo
    ' argumento. WScript.Shell.Run trata caminhos entre aspas sozinho.
    Application.StatusBar = "Processando no motor Python..."
    codigo = wsh.Run(comando, 0, True)               ' 0 = oculto, True = aguarda
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

Public Function DiagnosticoMotor() As String
    ' Texto que diz exatamente ONDE o motor foi procurado. Sem isso,
    ' "motor nao encontrado" nao da nenhuma pista de como resolver.
    Dim fso As Object, base As String, sb As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    base = RaizSistema()

    sb = "Motor nao encontrado." & vbCrLf & vbCrLf & _
         "Pasta do arquivo Excel:" & vbCrLf & "  " & base & vbCrLf & vbCrLf & _
         "Procurei por:" & vbCrLf
    sb = sb & "  " & Marca(fso, base & "\motor.exe") & vbCrLf
    sb = sb & "  " & Marca(fso, base & "\motor\motor.exe") & vbCrLf
    sb = sb & "  " & Marca(fso, base & "\python\main.py") & vbCrLf
    If Len(fso.GetParentFolderName(base)) > 0 Then
        sb = sb & "  " & Marca(fso, fso.GetParentFolderName(base) & "\python\main.py") & vbCrLf
    End If
    sb = sb & vbCrLf & "Interpretador Python:" & vbCrLf
    sb = sb & "  " & Marca(fso, base & "\python-portatil\python.exe") & vbCrLf
    sb = sb & "  " & Marca(fso, base & "\.venv\Scripts\python.exe") & vbCrLf
    sb = sb & vbCrLf & "Conteudo da pasta do Excel:" & vbCrLf
    sb = sb & ListarPasta(fso, base)
    sb = sb & vbCrLf & _
         "O arquivo Sistema_Composicoes.xlsm precisa ficar na MESMA pasta" & vbCrLf & _
         "que as pastas python, vba e BASES. Se ele foi movido, devolva-o" & vbCrLf & _
         "para junto delas e reabra."
    DiagnosticoMotor = sb
End Function

Private Function ListarPasta(ByVal fso As Object, ByVal pasta As String) As String
    ' Mostrar o que HA na pasta costuma revelar o problema mais depressa
    ' do que a lista do que falta.
    Dim item As Object, sb As String, n As Long
    On Error Resume Next
    If Not fso.FolderExists(pasta) Then
        ListarPasta = "  (a pasta nao existe)" & vbCrLf
        Exit Function
    End If
    For Each item In fso.GetFolder(pasta).SubFolders
        sb = sb & "  [pasta] " & item.Name & vbCrLf
        n = n + 1
        If n > 12 Then Exit For
    Next item
    n = 0
    For Each item In fso.GetFolder(pasta).Files
        sb = sb & "  " & item.Name & vbCrLf
        n = n + 1
        If n > 12 Then
            sb = sb & "  ..." & vbCrLf
            Exit For
        End If
    Next item
    On Error GoTo 0
    ListarPasta = sb
End Function

Private Function Marca(ByVal fso As Object, ByVal caminho As String) As String
    If fso.FileExists(caminho) Then
        Marca = "[existe]     " & caminho
    Else
        Marca = "[nao existe] " & caminho
    End If
End Function

Public Sub MostrarDiagnostico()
    ' Chamavel pela janela Verificacao Imediata (Ctrl+G) para depurar.
    Dim motor As String
    motor = CaminhoMotor()
    If Len(motor) = 0 Then
        MsgBox DiagnosticoMotor(), vbExclamation, "Diagnostico do motor"
    Else
        MsgBox "Comando que sera executado:" & vbCrLf & vbCrLf & motor & vbCrLf & vbCrLf & _
               "Pasta do sistema:" & vbCrLf & PastaDoSistema(), _
               vbInformation, "Diagnostico do motor"
    End If
End Sub
