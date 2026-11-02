$py = "python"
if (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe") {
    $py = "$PSScriptRoot\.venv\Scripts\python.exe"
}
& $py "$PSScriptRoot\bot.py"
