Option Explicit

Const BASE_URL = "https://dn.zaza.de5.net"
Const INPUT_DIR = ".\input"
Const OUTPUT_DIR = ".\output"
Const ARCHIVE_DIR = ".\archive"
Const LOG_FILE = ".\batch_upload_download.log"
Const HU_EXCEL_NAME = "EXPORT_hu-1471.xlsx"
Const HU_REFRESH_THRESHOLD_MINUTES = 30
Const DOWNLOAD_HU_SCRIPT = "download-hu-1471.vbs"
Const UPLOAD_EXCELS_SCRIPT = "upload_excels.vbs"
Const POLL_SECONDS = 3
Const MAX_WAIT_SECONDS = 1800

Dim fso
Dim shell
Dim quote
Dim logStream
Dim successCount
Dim failCount
Dim apiKey
Dim scriptFolder

quote = Chr(34)
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Set logStream = fso.OpenTextFile(LOG_FILE, 8, True)
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)
successCount = 0
failCount = 0
apiKey = GetEnv("DN_API_KEY")

If Not fso.FolderExists(INPUT_DIR) Then
    LogLine "Input folder not found: " & INPUT_DIR
    FinishAndExit 1, "Input folder not found: " & INPUT_DIR
End If

If Not fso.FolderExists(OUTPUT_DIR) Then
    fso.CreateFolder OUTPUT_DIR
End If
If Not fso.FolderExists(ARCHIVE_DIR) Then
    fso.CreateFolder ARCHIVE_DIR
End If

LogLine "Base URL: " & BASE_URL
LogLine "Input folder: " & fso.GetAbsolutePathName(INPUT_DIR)
LogLine "Output folder: " & fso.GetAbsolutePathName(OUTPUT_DIR)

EnsureHuExcelFreshness

Dim folder
Dim file
Set folder = fso.GetFolder(INPUT_DIR)

For Each file In folder.Files
    If LCase(fso.GetExtensionName(file.Name)) = "pdf" Then
        ProcessPdf file.Path
    End If
Next

FinishAndExit 0, BuildSummary()

Sub ProcessPdf(pdfPath)
    Dim jobId
    Dim status
    Dim outputPdf
    Dim errorMessage
    Dim startedAt

    LogLine ""
    LogLine "Processing: " & pdfPath

    jobId = UploadPdf(pdfPath)
    If jobId = "" Then
        LogLine "Upload failed."
        failCount = failCount + 1
        Exit Sub
    End If

    LogLine "Job ID: " & jobId
    startedAt = Now

    Do
        WScript.Sleep POLL_SECONDS * 1000
        status = GetJobStatus(jobId, outputPdf, errorMessage)

        If status = "done" Then
            Exit Do
        End If

        If status = "failed" Then
            If errorMessage = "" Then
                errorMessage = "Job failed but the API returned an empty error_message."
            End If
            LogLine "Job failed: " & errorMessage
            failCount = failCount + 1
            Exit Sub
        End If

        If DateDiff("s", startedAt, Now) > MAX_WAIT_SECONDS Then
            LogLine "Timed out waiting for job: " & jobId
            failCount = failCount + 1
            Exit Sub
        End If
    Loop

    DownloadOutput jobId, pdfPath, outputPdf
End Sub

Sub EnsureHuExcelFreshness()
    Dim excelPath
    Dim needsRefresh

    excelPath = fso.BuildPath(".", HU_EXCEL_NAME)
    needsRefresh = False

    If Not fso.FileExists(excelPath) Then
        needsRefresh = True
        LogLine HU_EXCEL_NAME & " is missing; refreshing it."
    ElseIf DateDiff("n", fso.GetFile(excelPath).DateLastModified, Now) > HU_REFRESH_THRESHOLD_MINUTES Then
        needsRefresh = True
        LogLine HU_EXCEL_NAME & " is older than " & HU_REFRESH_THRESHOLD_MINUTES & " minutes; refreshing it."
    End If

    If Not needsRefresh Then
        Exit Sub
    End If

    If Not RunScriptWithLog("refresh HU export", DOWNLOAD_HU_SCRIPT) Then
        FinishAndExit 1, "Failed to run " & DOWNLOAD_HU_SCRIPT
    End If

    If Not fso.FileExists(excelPath) Then
        FinishAndExit 1, HU_EXCEL_NAME & " was not created after refresh."
    End If

    If Not RunScriptWithArgsAndLog("upload refreshed HU export", UPLOAD_EXCELS_SCRIPT, excelPath) Then
        FinishAndExit 1, "Failed to run " & UPLOAD_EXCELS_SCRIPT
    End If

    If Not fso.FileExists(excelPath) Then
        FinishAndExit 1, HU_EXCEL_NAME & " was not created after refresh."
    End If

    LogLine HU_EXCEL_NAME & " is refreshed and ready."
End Sub

Function UploadPdf(pdfPath)
    Dim cmd
    Dim resp
    Dim apiUrl

    apiUrl = NormalizeUrl(BASE_URL) & "/api/process"
    cmd = "curl.exe -sS -X POST"
    If apiKey <> "" Then
        cmd = cmd & " -H " & quote & "X-API-Key: " & apiKey & quote
    End If
    cmd = cmd & " -F " & quote & "pdf=@" & pdfPath & quote
    cmd = cmd & " " & quote & apiUrl & quote

    resp = RunCommand(cmd)
    UploadPdf = ParseJsonValue(resp, "job_id")

    If UploadPdf = "" Then
        LogLine "Upload response:"
        LogLine resp
    End If
End Function

Function GetJobStatus(jobId, ByRef outputPdf, ByRef errorMessage)
    Dim cmd
    Dim resp
    Dim apiUrl

    outputPdf = ""
    errorMessage = ""
    apiUrl = NormalizeUrl(BASE_URL) & "/api/jobs/" & jobId

    cmd = "curl.exe -sS"
    If apiKey <> "" Then
        cmd = cmd & " -H " & quote & "X-API-Key: " & apiKey & quote
    End If
    cmd = cmd & " " & quote & apiUrl & quote

    resp = RunCommand(cmd)
    GetJobStatus = ParseJsonValue(resp, "status")
    outputPdf = ParseJsonValue(resp, "output_pdf")
    errorMessage = ParseJsonValue(resp, "error_message")
End Function

Sub DownloadOutput(jobId, pdfPath, outputPdf)
    Dim cmd
    Dim outName
    Dim outPath
    Dim apiUrl

    outName = fso.GetBaseName(pdfPath) & "_" & jobId & ".pdf"
    outPath = fso.BuildPath(OUTPUT_DIR, outName)
    apiUrl = NormalizeUrl(BASE_URL) & "/api/jobs/" & jobId & "/download"

    cmd = "curl.exe -sS -L"
    If apiKey <> "" Then
        cmd = cmd & " -H " & quote & "X-API-Key: " & apiKey & quote
    End If
    cmd = cmd & " -o " & quote & outPath & quote
    cmd = cmd & " " & quote & apiUrl & quote

    LogLine "Downloading to: " & outPath
    LogLine RunCommand(cmd)

    If fso.FileExists(outPath) Then
        LogLine "Saved: " & outPath
        If MoveOriginalPdfToArchive(pdfPath) Then
            successCount = successCount + 1
        Else
            failCount = failCount + 1
        End If
    Else
        LogLine "Download did not create a file."
        failCount = failCount + 1
    End If
End Sub

Function MoveOriginalPdfToArchive(pdfPath)
    Dim sourcePath
    Dim archivePath
    Dim baseName
    Dim attempt
    Dim maxRetries

    sourcePath = fso.GetAbsolutePathName(pdfPath)
    baseName = fso.GetFileName(sourcePath)
    archivePath = fso.BuildPath(ARCHIVE_DIR, baseName)
    maxRetries = 3

    For attempt = 1 To maxRetries
        On Error Resume Next
        If fso.FileExists(archivePath) Then
            fso.DeleteFile archivePath, True
        End If
        fso.MoveFile sourcePath, archivePath
        If Err.Number = 0 Then
            On Error GoTo 0
            LogLine "Moved original PDF to: " & archivePath
            MoveOriginalPdfToArchive = True
            Exit Function
        End If

        LogLine "Failed to move original PDF (attempt " & attempt & "): " & Err.Description
        Err.Clear
        On Error GoTo 0

        If attempt < maxRetries Then
            WScript.Sleep 1000
        End If
    Next

    MoveOriginalPdfToArchive = False
End Function

Function RunScriptWithLog(label, scriptName)
    Dim scriptPath
    Dim cmd
    Dim output
    Dim exitCode

    scriptPath = fso.BuildPath(scriptFolder, scriptName)
    If Not fso.FileExists(scriptPath) Then
        LogLine "Missing helper script: " & scriptPath
        RunScriptWithLog = False
        Exit Function
    End If

    cmd = "cscript.exe //nologo " & quote & scriptPath & quote
    LogLine "Running " & label & ": " & cmd
    output = RunCommandWithExit(cmd, exitCode)
    If Len(output) > 0 Then
        LogLine label & " output:"
        LogLine output
    End If
    LogLine label & " finished with exit code " & exitCode
    RunScriptWithLog = (exitCode = 0)
End Function

Function RunScriptWithArgsAndLog(label, scriptName, arg1)
    Dim scriptPath
    Dim cmd
    Dim output
    Dim exitCode

    scriptPath = fso.BuildPath(scriptFolder, scriptName)
    If Not fso.FileExists(scriptPath) Then
        LogLine "Missing helper script: " & scriptPath
        RunScriptWithArgsAndLog = False
        Exit Function
    End If

    cmd = "cscript.exe //nologo " & quote & scriptPath & quote & " " & quote & arg1 & quote
    LogLine "Running " & label & ": " & cmd
    output = RunCommandWithExit(cmd, exitCode)
    If Len(output) > 0 Then
        LogLine label & " output:"
        LogLine output
    End If
    LogLine label & " finished with exit code " & exitCode
    RunScriptWithArgsAndLog = (exitCode = 0)
End Function

Function RunCommand(cmd)
    Dim exec
    Dim output

    Set exec = shell.Exec(cmd)
    Do While exec.Status = 0
        WScript.Sleep 100
    Loop

    output = ""
    On Error Resume Next
    output = exec.StdOut.ReadAll & exec.StdErr.ReadAll
    On Error GoTo 0

    RunCommand = output
End Function

Function RunCommandWithExit(cmd, ByRef exitCode)
    Dim exec
    Dim output

    Set exec = shell.Exec(cmd)
    Do While exec.Status = 0
        WScript.Sleep 100
    Loop

    output = ""
    On Error Resume Next
    output = exec.StdOut.ReadAll & exec.StdErr.ReadAll
    On Error GoTo 0

    exitCode = exec.ExitCode
    RunCommandWithExit = output
End Function

Function ParseJsonValue(jsonText, key)
    Dim re
    Dim matches

    Set re = New RegExp
    re.Global = False
    re.IgnoreCase = True
    re.Pattern = """" & key & """\s*:\s*""([^""]*)"""

    If re.Test(jsonText) Then
        Set matches = re.Execute(jsonText)
        ParseJsonValue = matches(0).SubMatches(0)
    Else
        ParseJsonValue = ""
    End If
End Function

Function NormalizeUrl(url)
    If Right(url, 1) = "/" Then
        NormalizeUrl = Left(url, Len(url) - 1)
    Else
        NormalizeUrl = url
    End If
End Function

Function GetEnv(name)
    On Error Resume Next
    GetEnv = shell.Environment("PROCESS")(name)
    If Err.Number <> 0 Then
        Err.Clear
        GetEnv = ""
    End If
    On Error GoTo 0
End Function

Sub LogLine(text)
    logStream.WriteLine NowIso() & " " & text
End Sub

Function NowIso()
    NowIso = Year(Now) & "-" & Right("0" & Month(Now), 2) & "-" & Right("0" & Day(Now), 2) & " " & _
             Right("0" & Hour(Now), 2) & ":" & Right("0" & Minute(Now), 2) & ":" & Right("0" & Second(Now), 2)
End Function

Function BuildSummary()
    BuildSummary = "Finished." & vbCrLf & _
                   "Success: " & successCount & vbCrLf & _
                   "Failed: " & failCount & vbCrLf & _
                   "Log file: " & fso.GetAbsolutePathName(LOG_FILE)
End Function

Sub FinishAndExit(exitCode, message)
    On Error Resume Next
    logStream.Close
    On Error GoTo 0
    MsgBox message, vbInformation, "Batch Upload Result"
    WScript.Quit exitCode
End Sub
