
$ErrorActionPreference = "Stop"

# 현재 스크립트가 있는 디렉토리 확인
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScriptPath = Join-Path $ScriptDir "update_age.py"
$PythonPath = (Get-Command python).Source

if (-not (Test-Path $PythonScriptPath)) {
    Write-Error "update_age.py 파일을 찾을 수 없습니다: $PythonScriptPath"
    exit
}

# 사용자 입력 받기 (이미 환경변수에 있으면 그것을 사용, 없으면 에러)
$NotionToken = $env:NOTION_TOKEN
$PageId = $env:NOTION_PAGE_ID

Write-Host "Debug: Token Length: $($NotionToken.Length)"
Write-Host "Debug: PageID: $PageId"

if ([string]::IsNullOrWhiteSpace($NotionToken) -or [string]::IsNullOrWhiteSpace($PageId)) {
    Write-Error "Token과 Page ID는 필수입니다. 환경 변수가 설정되지 않았습니다."
    exit 1
}

# 배치 파일 생성 (환경변수 설정을 위해)
$BatchFilePath = Join-Path $ScriptDir "run_update.bat"
$BatchContent = @"
@echo off
set NOTION_TOKEN=$NotionToken
set NOTION_PAGE_ID=$PageId
"$PythonPath" "$PythonScriptPath" >> "$ScriptDir\update.log" 2>&1
"@

Set-Content -Path $BatchFilePath -Value $BatchContent
Write-Host "실행 스크립트 생성됨: $BatchFilePath"

# 작업 스케줄러 등록
$TaskName = "NotionPetAgeUpdate"
$Trigger = New-ScheduledTaskTrigger -Daily -At 9am
$Action = New-ScheduledTaskAction -Execute $BatchFilePath -WorkingDirectory $ScriptDir
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 기존 작업이 있다면 삭제
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 새 작업 등록
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "매일 우유의 나이를 노션에 업데이트합니다."

Write-Host "=========================================="
Write-Host "작업 스케줄러 등록 완료!"
Write-Host "매일 오전 9시에 자동으로 실행됩니다."
Write-Host "테스트를 위해 지금 한번 실행해볼 수 있습니다."
Write-Host "로그 확인: $ScriptDir\update.log"
Write-Host "=========================================="
