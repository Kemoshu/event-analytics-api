$API = "http://localhost:8000"

function Post-Event($json) {
  Invoke-RestMethod `
    -Uri "$API/events" `
    -Method POST `
    -ContentType "application/json" `
    -Body $json | Out-Null
}

Post-Event '{"event_type":"robot.menu.updated","source":"admin-panel","user_id":"kevin","payload":{"menuId":"coffee-01","changes":2}}'
Post-Event '{"event_type":"robot.menu.updated","source":"admin-panel","user_id":"kevin","payload":{"menuId":"coffee-02","changes":5}}'
Post-Event '{"event_type":"robot.calibration.ran","source":"field-tech","user_id":"alex","payload":{"result":"pass"}}'
Post-Event '{"event_type":"robot.calibration.ran","source":"field-tech","user_id":"alex","payload":{"result":"fail","error":"camera"}}'
Post-Event '{"event_type":"robot.health.ping","source":"robot","user_id":null,"payload":{"cpu":32,"temp":61}}'

Write-Host "Seeded events."
