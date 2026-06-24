param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
python .\scripts\smoke_test_auth.py --base-url $BaseUrl
