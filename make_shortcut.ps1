$dir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ico  = Join-Path $dir "tetris.ico"
$bat  = Join-Path $dir "tetris.bat"
$dest = [Environment]::GetFolderPath('Desktop') + "\Tetris.lnk"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($dest)
$sc.TargetPath        = $bat
$sc.WorkingDirectory  = $dir
$sc.IconLocation      = "$ico,0"
$sc.Description       = "Tetris"
$sc.Save()

Write-Host "デスクトップに Tetris.lnk を作成しました: $dest"
