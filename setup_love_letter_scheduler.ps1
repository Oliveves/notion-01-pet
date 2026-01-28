
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFilePath = Join-Path $ScriptDir "run_love_letter.bat"

if (-not (Test-Path $BatchFilePath)) {
    Write-Error "run_love_letter.bat 파일을 찾을 수 없습니다: $BatchFilePath"
    exit
}

# 작업 스케줄러 등록
$TaskName = "NotionLoveLetterUpdate"

# 트리거: 지금부터 시작해서 1시간마다 무기한 반복
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)

$Action = New-ScheduledTaskAction -Execute $BatchFilePath -WorkingDirectory $ScriptDir
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 기존 작업 삭제
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 새 작업 등록
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "매시간 정각에 Notion Love Letter를 업데이트합니다."

Write-Host "=========================================="
Write-Host "Love Letter 스케줄러 등록 완료!"
Write-Host "매 1시간마다 실행됩니다."
Write-Host "=========================================="
