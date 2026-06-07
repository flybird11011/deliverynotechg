Option Explicit

Const API_URL = "https://dn.zaza.de5.net/api/excels"
Const CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
Const BOUNDARY = "----CodexExcelUploadBoundary7d3f2b5f"
Const STATE_FILE_NAME = "upload_excels.state.txt"
Const LOG_FILE_NAME = "upload_excels.log.txt"

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

Dim scriptFolder
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)

Dim stateFilePath
stateFilePath = fso.BuildPath(scriptFolder, STATE_FILE_NAME)

Dim logFilePath
logFilePath = fso.BuildPath(scriptFolder, LOG_FILE_NAME)

Dim apiKey
apiKey = GetEnv("DN_API_KEY")

Dim state
Set state = LoadState(stateFilePath)

Dim files
Set files = CreateObject("Scripting.Dictionary")

If WScript.Arguments.Count > 0 Then
    Dim i
    For i = 0 To WScript.Arguments.Count - 1
        AddFileIfExists files, WScript.Arguments(i), state, False
    Next
Else
    Dim folder, file
    Set folder = fso.GetFolder(scriptFolder)
    For Each file In folder.Files
        If LCase(fso.GetExtensionName(file.Name)) = "xlsx" Then
            AddFileIfExists files, file.Path, state, True
        End If
    Next
End If

If files.Count = 0 Then
    LogLine "No new .xlsx files to upload."
    WScript.Quit 0
End If

Dim bodyStream
Set bodyStream = CreateObject("ADODB.Stream")
bodyStream.Type = 1
bodyStream.Open

Dim key
For Each key In files.Keys
    AppendText bodyStream, "--" & BOUNDARY & vbCrLf
    AppendText bodyStream, "Content-Disposition: form-data; name=""excels""; filename=""" & GetFileName(key) & """" & vbCrLf
    AppendText bodyStream, "Content-Type: " & CONTENT_TYPE & vbCrLf & vbCrLf
    AppendFileBytes bodyStream, key
    AppendText bodyStream, vbCrLf
Next

AppendText bodyStream, "--" & BOUNDARY & "--" & vbCrLf
bodyStream.Position = 0

Dim request
Set request = CreateObject("WinHttp.WinHttpRequest.5.1")
request.Open "POST", API_URL, False
request.SetRequestHeader "Content-Type", "multipart/form-data; boundary=" & BOUNDARY
If Len(apiKey) > 0 Then
    request.SetRequestHeader "X-API-Key", apiKey
End If
request.Send bodyStream.Read

LogLine "HTTP " & request.Status & " " & request.StatusText
LogLine request.ResponseText

If request.Status >= 200 And request.Status < 300 Then
    UpdateState state, files
    SaveState stateFilePath, state
End If

bodyStream.Close

Sub AddFileIfExists(dict, path, stateDict, skipAlreadyUploaded)
    Dim absPath, modified
    absPath = fso.GetAbsolutePathName(path)
    If Not fso.FileExists(absPath) Then
        LogLine "Skip missing file: " & path
        Exit Sub
    End If

    modified = CStr(fso.GetFile(absPath).DateLastModified)

    If skipAlreadyUploaded Then
        If stateDict.Exists(absPath) Then
            If stateDict(absPath) = modified Then
                Exit Sub
            End If
        End If
    End If

    If Not dict.Exists(absPath) Then
        dict.Add absPath, modified
    End If
End Sub

Sub AppendText(binStream, text)
    Dim textStream
    Set textStream = CreateObject("ADODB.Stream")
    textStream.Type = 2
    textStream.Charset = "us-ascii"
    textStream.Open
    textStream.WriteText text
    textStream.Position = 0
    textStream.Type = 1
    binStream.Write textStream.Read
    textStream.Close
End Sub

Sub AppendFileBytes(binStream, path)
    Dim fileStream
    Set fileStream = CreateObject("ADODB.Stream")
    fileStream.Type = 1
    fileStream.Open
    fileStream.LoadFromFile path
    binStream.Write fileStream.Read
    fileStream.Close
End Sub

Function GetFileName(path)
    Dim localFso
    Set localFso = CreateObject("Scripting.FileSystemObject")
    GetFileName = localFso.GetFileName(path)
End Function

Function GetEnv(name)
    On Error Resume Next
    Dim shell
    Set shell = CreateObject("WScript.Shell")
    GetEnv = shell.Environment("Process")(name)
    If Err.Number <> 0 Then
        Err.Clear
        GetEnv = ""
    End If
    On Error GoTo 0
End Function

Function LoadState(path)
    Dim dict
    Set dict = CreateObject("Scripting.Dictionary")
    If Not fso.FileExists(path) Then
        Set LoadState = dict
        Exit Function
    End If

    Dim ts, line, parts
    Set ts = fso.OpenTextFile(path, 1, False)
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If Len(line) > 0 Then
            parts = Split(line, "|", 2)
            If UBound(parts) = 1 Then
                dict(parts(0)) = parts(1)
            End If
        End If
    Loop
    ts.Close
    Set LoadState = dict
End Function

Sub SaveState(path, stateDict)
    Dim ts, key
    Set ts = fso.CreateTextFile(path, True)
    For Each key In stateDict.Keys
        ts.WriteLine key & "|" & stateDict(key)
    Next
    ts.Close
End Sub

Sub UpdateState(stateDict, filesDict)
    Dim key
    For Each key In filesDict.Keys
        stateDict(key) = filesDict(key)
    Next
End Sub

Sub LogLine(text)
    Dim ts
    Set ts = fso.OpenTextFile(logFilePath, 8, True)
    ts.WriteLine Now & " " & text
    ts.Close

    If InStr(LCase(WScript.FullName), "cscript.exe") > 0 Then
        WScript.Echo text
    End If
End Sub
