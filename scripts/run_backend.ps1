# 백엔드 개발 서버 — data/ CSV·DB 변경으로 reload 루프 나는 것 방지
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".\.venv\Scripts\uvicorn.exe")) {
    Write-Error ".venv 가 없습니다. 가상환경을 먼저 활성화하거나 생성하세요."
}

Write-Host "Starting Silmari API on http://127.0.0.1:8000"
.\.venv\Scripts\uvicorn.exe backend.main:app `
    --reload `
    --reload-dir backend `
    --host 127.0.0.1 `
    --port 8000
