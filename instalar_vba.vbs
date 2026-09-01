' ============================================================================
' instalar_vba.vbs - Monta Sistema_Composicoes.xlsm a partir do .xlsx
'                    gerado por build_xlsm.py mais os modulos de vba\.
'
' Uso:  cscript //nologo instalar_vba.vbs
'
' Exige a opcao "Confiar no acesso ao modelo de objeto do projeto do VBA"
' (Central de Confiabilidade -> Configuracoes de Macro). E uma caixa de
' selecao do Excel, marcavel por usuario comum, sem privilegio de
' administrador. Se preferir nao habilita-la, use a importacao manual
' descrita em docs/INSTALACAO.md, secao 3b.
' ============================================================================
Option Explicit

Const XL_ABERTA_COM_MACRO = 52      ' xlOpenXMLWorkbookMacroEnabled

Dim fso, raiz, origem, destino, pastaVba, excel, wb, arquivo, importados

Set fso = CreateObject("Scripting.FileSystemObject")
raiz = fso.GetParentFolderName(WScript.ScriptFullName)
origem = raiz & "\Sistema_Composicoes.xlsx"
destino = raiz & "\Sistema_Composicoes.xlsm"
pastaVba = raiz & "\vba"

If Not fso.FileExists(origem) Then
    WScript.Echo "Nao encontrei " & origem
    WScript.Echo "Rode antes:  python build_xlsm.py"
    WScript.Quit 1
End If
If Not fso.FolderExists(pastaVba) Then
    WScript.Echo "Nao encontrei a pasta " & pastaVba
    WScript.Quit 1
End If

On Error Resume Next
Set excel = CreateObject("Excel.Application")
If Err.Number <> 0 Then
    WScript.Echo "Nao foi possivel iniciar o Excel: " & Err.Description
    WScript.Quit 1
End If
On Error GoTo 0

excel.Visible = False
excel.DisplayAlerts = False

Set wb = excel.Workbooks.Open(origem)

' Remove modulos homonimos de uma execucao anterior, para a operacao ser
' repetivel sem duplicar codigo.
On Error Resume Next
Dim i, comp
For i = wb.VBProject.VBComponents.Count To 1 Step -1
    Set comp = wb.VBProject.VBComponents(i)
    If comp.Type = 1 Then wb.VBProject.VBComponents.Remove comp
Next
If Err.Number <> 0 Then
    WScript.Echo ""
    WScript.Echo "ERRO: sem acesso ao projeto VBA."
    WScript.Echo "Habilite em: Arquivo > Opcoes > Central de Confiabilidade >"
    WScript.Echo "Configuracoes da Central de Confiabilidade > Configuracoes de"
    WScript.Echo "Macro > 'Confiar no acesso ao modelo de objeto do projeto do VBA'."
    WScript.Echo ""
    WScript.Echo "Ou use a importacao manual (docs/INSTALACAO.md, secao 3b)."
    wb.Close False
    excel.Quit
    WScript.Quit 2
End If
On Error GoTo 0

importados = 0
For Each arquivo In fso.GetFolder(pastaVba).Files
    If LCase(fso.GetExtensionName(arquivo.Name)) = "bas" Then
        wb.VBProject.VBComponents.Import arquivo.Path
        WScript.Echo "  importado: " & arquivo.Name
        importados = importados + 1
    End If
Next

If importados = 0 Then
    WScript.Echo "Nenhum modulo .bas encontrado em " & pastaVba
    wb.Close False
    excel.Quit
    WScript.Quit 1
End If

' Cria os botoes de todas as abas.
On Error Resume Next
excel.Run "modUI.ReconstruirBotoes"
If Err.Number <> 0 Then
    WScript.Echo ""
    WScript.Echo "  AVISO: nao foi possivel criar os botoes automaticamente."
    WScript.Echo "  (" & Err.Description & ")"
    WScript.Echo "  Depois de abrir a planilha, pressione ALT+F11, depois"
    WScript.Echo "  CTRL+G, digite  modUI.ReconstruirBotoesComAviso  e ENTER."
    Err.Clear
End If
On Error GoTo 0

If fso.FileExists(destino) Then fso.DeleteFile destino, True
wb.SaveAs destino, XL_ABERTA_COM_MACRO
wb.Close False
excel.Quit

WScript.Echo ""
WScript.Echo importados & " modulo(s) importado(s)."
WScript.Echo "Gerado: " & destino
WScript.Echo "Abra o arquivo, habilite as macros e clique TESTAR MOTOR na aba INICIO."
