# Update Claude Desktop Configuration
# This script updates the Claude Desktop configuration to include the Wikipedia MCP server

# Define paths
$ConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$RepoPath = "$PSScriptRoot"
$PythonPath = "$RepoPath\venv\Scripts\python.exe"
$ScriptPath = "$RepoPath\run.py"

# Ensure the configuration file exists
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Claude Desktop configuration file not found at: $ConfigPath" -ForegroundColor Red
    Write-Host "Make sure Claude Desktop is installed and has been run at least once." -ForegroundColor Yellow
    exit 1
}

# Read the current configuration
$ConfigContent = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json

# Check if mcpServers property exists and create it if not
if (-not (Get-Member -InputObject $ConfigContent -Name "mcpServers" -MemberType Properties)) {
    Write-Host "Creating mcpServers property" -ForegroundColor Yellow
    $ConfigContent | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{}
}

# Check if Wikipedia MCP is already configured
$WikiMcpExists = $false
if ($ConfigContent.mcpServers.PSObject.Properties.Name -contains "wikipedia-mcp") {
    $WikiMcpExists = $true
    # Update the existing configuration
    $ConfigContent.mcpServers."wikipedia-mcp".command = $PythonPath
    $ConfigContent.mcpServers."wikipedia-mcp".args = @($ScriptPath, "--host", "127.0.0.1", "--port", "8765", "--no-reload")
    Write-Host "Updated existing Wikipedia MCP configuration." -ForegroundColor Green
}

# Add new Wikipedia MCP configuration if it doesn't exist
if (-not $WikiMcpExists) {
    $WikiServer = [PSCustomObject]@{
        command = $PythonPath
        args = @($ScriptPath, "--host", "127.0.0.1", "--port", "8765", "--no-reload")
    }
    
    # Add the new server configuration
    $ConfigContent.mcpServers | Add-Member -NotePropertyName "wikipedia-mcp" -NotePropertyValue $WikiServer -Force
    Write-Host "Added new Wikipedia MCP server configuration." -ForegroundColor Green
}

# Save the updated configuration
$ConfigContent | ConvertTo-Json -Depth 10 | Set-Content -Path $ConfigPath
Write-Host "Claude Desktop configuration updated successfully." -ForegroundColor Green
Write-Host "Please restart Claude Desktop for changes to take effect." -ForegroundColor Cyan
