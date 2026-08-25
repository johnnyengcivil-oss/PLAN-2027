Attribute VB_Name = "modJson"
'==============================================================================
' modJson - Leitor e escritor JSON para VBA
'
' O VBA nao tem JSON nativo. Este modulo implementa um parser recursivo
' descendente que devolve:
'     objeto {} -> Scripting.Dictionary  (late binding, sem referencia extra)
'     lista  [] -> Collection
'     texto     -> String
'     numero    -> Double
'     true/false-> Boolean
'     null      -> Empty
'
' Nao usa Eval, ScriptControl nem qualquer avaliacao de codigo: o payload
' vindo do Python nunca e executado, apenas lido caractere a caractere.
'==============================================================================
Option Explicit
Option Base 1

Private mTexto As String
Private mPos As Long
Private mTam As Long

'------------------------------------------------------------------ leitura

Public Function Parse(ByVal texto As String) As Variant
    mTexto = texto
    mPos = 1
    mTam = Len(texto)
    PularEspacos
    If mPos > mTam Then
        Set Parse = NovoDicionario
        Exit Function
    End If
    AtribuirValor Parse, LerValor()
End Function

Private Sub AtribuirValor(ByRef destino As Variant, ByRef origem As Variant)
    If IsObject(origem) Then
        Set destino = origem
    Else
        destino = origem
    End If
End Sub

Public Function NovoDicionario() As Object
    Set NovoDicionario = CreateObject("Scripting.Dictionary")
    NovoDicionario.CompareMode = 1          ' TextCompare
End Function

Private Function LerValor() As Variant
    Dim c As String
    PularEspacos
    If mPos > mTam Then Exit Function
    c = Mid$(mTexto, mPos, 1)
    Select Case c
        Case "{": Set LerValor = LerObjeto()
        Case "[": Set LerValor = LerLista()
        Case """": LerValor = LerTexto()
        Case "t"
            mPos = mPos + 4: LerValor = True
        Case "f"
            mPos = mPos + 5: LerValor = False
        Case "n"
            mPos = mPos + 4: LerValor = Empty
        Case Else
            LerValor = LerNumero()
    End Select
End Function

Private Function LerObjeto() As Object
    Dim dic As Object, chave As String
    Set dic = NovoDicionario
    mPos = mPos + 1                          ' consome "{"
    PularEspacos
    If Mid$(mTexto, mPos, 1) = "}" Then
        mPos = mPos + 1
        Set LerObjeto = dic
        Exit Function
    End If
    Do
        PularEspacos
        chave = LerTexto()
        PularEspacos
        mPos = mPos + 1                      ' consome ":"
        Dim v As Variant
        AtribuirValor v, LerValor()
        If IsObject(v) Then
            Set dic(chave) = v
        Else
            dic(chave) = v
        End If
        PularEspacos
        If Mid$(mTexto, mPos, 1) = "," Then
            mPos = mPos + 1
        Else
            Exit Do
        End If
    Loop
    PularEspacos
    If Mid$(mTexto, mPos, 1) = "}" Then mPos = mPos + 1
    Set LerObjeto = dic
End Function

Private Function LerLista() As Collection
    Dim col As New Collection
    mPos = mPos + 1                          ' consome "["
    PularEspacos
    If Mid$(mTexto, mPos, 1) = "]" Then
        mPos = mPos + 1
        Set LerLista = col
        Exit Function
    End If
    Do
        Dim v As Variant
        AtribuirValor v, LerValor()
        If IsObject(v) Then
            col.Add v
        Else
            col.Add v
        End If
        PularEspacos
        If Mid$(mTexto, mPos, 1) = "," Then
            mPos = mPos + 1
        Else
            Exit Do
        End If
    Loop
    PularEspacos
    If Mid$(mTexto, mPos, 1) = "]" Then mPos = mPos + 1
    Set LerLista = col
End Function

Private Function LerTexto() As String
    Dim sb As String, c As String, codigo As String
    mPos = mPos + 1                          ' consome aspas de abertura
    Do While mPos <= mTam
        c = Mid$(mTexto, mPos, 1)
        If c = """" Then
            mPos = mPos + 1
            Exit Do
        ElseIf c = "\" Then
            mPos = mPos + 1
            c = Mid$(mTexto, mPos, 1)
            Select Case c
                Case "n": sb = sb & vbLf
                Case "r": sb = sb & vbCr
                Case "t": sb = sb & vbTab
                Case "b": sb = sb & Chr$(8)
                Case "f": sb = sb & Chr$(12)
                Case "u"
                    codigo = Mid$(mTexto, mPos + 1, 4)
                    sb = sb & ChrW$(CLng("&H" & codigo))
                    mPos = mPos + 4
                Case Else: sb = sb & c
            End Select
            mPos = mPos + 1
        Else
            sb = sb & c
            mPos = mPos + 1
        End If
    Loop
    LerTexto = sb
End Function

Private Function LerNumero() As Double
    Dim inicio As Long, c As String
    inicio = mPos
    Do While mPos <= mTam
        c = Mid$(mTexto, mPos, 1)
        If InStr("0123456789+-.eE", c) = 0 Then Exit Do
        mPos = mPos + 1
    Loop
    ' CDbl respeita a configuracao regional; o JSON usa sempre ponto.
    LerNumero = Val(Mid$(mTexto, inicio, mPos - inicio))
End Function

Private Sub PularEspacos()
    Do While mPos <= mTam
        Select Case Mid$(mTexto, mPos, 1)
            Case " ", vbTab, vbCr, vbLf
                mPos = mPos + 1
            Case Else
                Exit Do
        End Select
    Loop
End Sub

'------------------------------------------------------------------ escrita

Public Function Escapar(ByVal texto As String) As String
    Dim s As String
    s = Replace(texto, "\", "\\")
    s = Replace(s, """", "\""")
    s = Replace(s, vbCrLf, "\n")
    s = Replace(s, vbCr, "\n")
    s = Replace(s, vbLf, "\n")
    s = Replace(s, vbTab, "\t")
    Escapar = s
End Function

Public Function Texto(ByVal valor As String) As String
    Texto = """" & Escapar(valor) & """"
End Function

Public Function Numero(ByVal valor As Double) As String
    ' Forca o ponto decimal, independente da configuracao regional do Windows.
    Numero = Replace(CStr(valor), ",", ".")
End Function

Public Function Montar(ParamArray pares() As Variant) As String
    ' Montar("acao", modJson.Texto("status"), "top_n", "10")
    Dim i As Long, sb As String
    sb = "{"
    For i = LBound(pares) To UBound(pares) Step 2
        If i > LBound(pares) Then sb = sb & ","
        sb = sb & Texto(CStr(pares(i))) & ":" & CStr(pares(i + 1))
    Next i
    Montar = sb & "}"
End Function

'------------------------------------------------------- acesso seguro

Public Function Obter(ByVal dic As Object, ByVal chave As String, _
                      Optional ByVal padrao As Variant = "") As Variant
    If dic Is Nothing Then
        AtribuirValor Obter, padrao
    ElseIf dic.Exists(chave) Then
        AtribuirValor Obter, dic(chave)
    Else
        AtribuirValor Obter, padrao
    End If
End Function

Public Function ObterTexto(ByVal dic As Object, ByVal chave As String, _
                           Optional ByVal padrao As String = "") As String
    Dim v As Variant
    AtribuirValor v, Obter(dic, chave, padrao)
    If IsObject(v) Then
        ObterTexto = padrao
    ElseIf IsEmpty(v) Or IsNull(v) Then
        ObterTexto = padrao
    Else
        ObterTexto = CStr(v)
    End If
End Function

Public Function ObterNumero(ByVal dic As Object, ByVal chave As String, _
                            Optional ByVal padrao As Double = 0) As Double
    Dim v As Variant
    AtribuirValor v, Obter(dic, chave, padrao)
    If IsObject(v) Or IsEmpty(v) Or IsNull(v) Then
        ObterNumero = padrao
    ElseIf IsNumeric(v) Then
        ObterNumero = CDbl(v)
    Else
        ObterNumero = padrao
    End If
End Function

Public Function ObterObjeto(ByVal dic As Object, ByVal chave As String) As Object
    If dic Is Nothing Then Exit Function
    If Not dic.Exists(chave) Then Exit Function
    If IsObject(dic(chave)) Then Set ObterObjeto = dic(chave)
End Function

Public Function ObterLista(ByVal dic As Object, ByVal chave As String) As Collection
    Dim v As Object
    Set v = ObterObjeto(dic, chave)
    If v Is Nothing Then
        Set ObterLista = New Collection
    ElseIf TypeName(v) = "Collection" Then
        Set ObterLista = v
    Else
        Set ObterLista = New Collection
    End If
End Function
