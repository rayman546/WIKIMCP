$config = Get-Content "C:\Users\Topher\AppData\Roaming\Claude\claude_desktop_config.json" -Raw | ConvertFrom-Json
$config.mcpServers."wikipedia-mcp".command = "C:\Claude\WIKIMCP\venv\Scripts\python.exe"
$config | ConvertTo-Json -Depth 10 | Set-Content "C:\Users\Topher\AppData\Roaming\Claude\claude_desktop_config.json"
Write-Output "Update complete!"
