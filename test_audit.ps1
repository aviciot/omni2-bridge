# Test Audit Logging

$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    user_id = "avi.cohen@shift4.com"
    message = "What databases are available?"
} | ConvertTo-Json

Write-Host "`n🧪 Testing chat request with audit logging..." -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "http://localhost:8000/chat/ask" -Method POST -Headers $headers -Body $body
Write-Host "✅ Chat Response:" -ForegroundColor Green
$response | ConvertTo-Json -Depth 5

Write-Host "`n📊 Querying my audit logs..." -ForegroundColor Cyan
$auditUrl = "http://localhost:8000/audit/my-logs?user_id=avi.cohen@shift4.com&limit=5"
$auditResponse = Invoke-RestMethod -Uri $auditUrl -Method GET
Write-Host "✅ Audit Logs:" -ForegroundColor Green
$auditResponse | ConvertTo-Json -Depth 5

Write-Host "`n📈 Checking my stats..." -ForegroundColor Cyan
$statsUrl = "http://localhost:8000/audit/my-stats?user_id=avi.cohen@shift4.com&days=1"
$statsResponse = Invoke-RestMethod -Uri $statsUrl -Method GET
Write-Host "✅ Audit Stats:" -ForegroundColor Green
$statsResponse | ConvertTo-Json -Depth 5
