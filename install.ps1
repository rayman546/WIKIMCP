#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Installer script for the Wikipedia MCP API server with Claude Desktop integration.
.DESCRIPTION
    This script will:
    1. Clone the repository or use existing one
    2. Create a Python virtual environment
    3. Install dependencies
    4. Configure Claude Desktop to use the Wikipedia MCP API server
.PARAMETER RepoPath
    Path where to install the Wikipedia MCP API server.
    Default: C:\Claude\WIKIMCP
.PARAMETER Branch
    Branch to use when cloning the repository.
    Default: mcp-implementation
.PARAMETER Force
    Force reinstallation even if already installed.
.PARAMETER SkipClaudeConfig
    Skip configuring Claude Desktop.
.EXAMPLE
    .\install.ps1
    Install the Wikipedia MCP API server to C:\Claude\WIKIMCP
.EXAMPLE
    .\install.ps1 -RepoPath "D:\Projects\WIKIMCP" -Force
    Force reinstallation to a custom directory
#>
param (
    [string]$RepoPath = "C:\Claude\WIKIMCP",
    [string]$Branch = "mcp-implementation",
    [switch]$Force,
    [switch]$SkipClaudeConfig
)

# Configuration
$RepoUrl = "https://github.com/YOUR_USERNAME/WIKIMCP.git"  # Update this with your GitHub username
$ClaudeDesktopConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"

# Error handling
$ErrorActionPreference = "Stop"

# Helper Functions
function Write-Log {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet("Info", "Warning", "Error")]
        [string]$Level = "Info"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "Info" { "White" }
        "Warning" { "Yellow" }
        "Error" { "Red" }
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Test-Command {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Command
    )
    
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Check Prerequisites
Write-Log "Checking prerequisites..."

# Fix the command checking logic
if (-not ((Test-Command "python") -or (Test-Command "python3"))) {
    Write-Log "Python is not installed. Please install Python 3.8 or newer." -Level "Error"
    exit 1
}

if (-not (Test-Command "git")) {
    Write-Log "Git is not installed. Please install Git." -Level "Error"
    exit 1
}

# Create directory if it doesn't exist
if (-not (Test-Path $RepoPath)) {
    Write-Log "Creating directory $RepoPath"
    New-Item -ItemType Directory -Path $RepoPath -Force | Out-Null
}

# Clone or update repository
if (-not (Test-Path "$RepoPath\.git") -or $Force) {
    # Fresh clone if not exists or force flag is used
    if (Test-Path "$RepoPath\.git") {
        Write-Log "Force flag used, removing existing repository" -Level "Warning"
        
        try {
            # Try to deactivate virtual environment if it exists
            if (Test-Path "$RepoPath\venv\Scripts\deactivate.bat") {
                Write-Log "Deactivating virtual environment"
                & "$RepoPath\venv\Scripts\deactivate.bat"
            }
        }
        catch {
            # Ignore errors from deactivation attempt
            Write-Log "Could not deactivate virtual environment, continuing anyway" -Level "Warning"
        }
        
        # Move to a different directory before removing
        Set-Location $env:TEMP
        
        # Remove the directory with force
        Write-Log "Removing $RepoPath"
        Remove-Item -Path $RepoPath -Recurse -Force
        
        # Recreate the directory
        Write-Log "Recreating directory $RepoPath"
        New-Item -ItemType Directory -Path $RepoPath -Force | Out-Null
    }
    
    # Clone the repository
    Write-Log "Cloning repository from $RepoUrl"
    Set-Location $RepoPath
    git clone --branch $Branch $RepoUrl .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to clone repository" -Level "Error"
        exit 1
    }
}
else {
    # Update existing repository
    Write-Log "Updating existing repository"
    Set-Location $RepoPath
    git fetch
    git checkout $Branch
    git pull
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to update repository" -Level "Error"
        exit 1
    }
}

# Create virtual environment if it doesn't exist or force flag is used
if (-not (Test-Path "$RepoPath\venv") -or $Force) {
    if (Test-Path "$RepoPath\venv" -and $Force) {
        Write-Log "Removing existing virtual environment"
        Remove-Item -Path "$RepoPath\venv" -Recurse -Force
    }
    
    Write-Log "Creating Python virtual environment"
    python -m venv "$RepoPath\venv"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to create virtual environment" -Level "Error"
        exit 1
    }
}

# Install dependencies
Write-Log "Installing dependencies"
& "$RepoPath\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$RepoPath\venv\Scripts\python.exe" -m pip install -r "$RepoPath\requirements.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Log "Failed to install dependencies" -Level "Error"
    exit 1
}

# Configure Claude Desktop
if (-not $SkipClaudeConfig) {
    Write-Log "Configuring Claude Desktop"
    
    if (-not (Test-Path $ClaudeDesktopConfigPath)) {
        Write-Log "Claude Desktop config file not found at $ClaudeDesktopConfigPath" -Level "Warning"
        Write-Log "Is Claude Desktop installed? Skipping configuration."
    }
    else {
        # Backup config
        $backupPath = "$ClaudeDesktopConfigPath.bak"
        Write-Log "Backing up Claude Desktop config to $backupPath"
        Copy-Item -Path $ClaudeDesktopConfigPath -Destination $backupPath -Force
        
        # Read config
        $config = Get-Content -Path $ClaudeDesktopConfigPath -Raw | ConvertFrom-Json
        
        # Create mcpServers object if it doesn't exist
        if (-not $config.mcpServers) {
            $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{}
        }
        
        # Configure Wikipedia MCP
        $venvPythonPath = "$RepoPath\venv\Scripts\python.exe" -replace "\\", "\\"
        $mcpServerPath = "$RepoPath\mcp_server.py" -replace "\\", "\\"
        
        $config.mcpServers | Add-Member -NotePropertyName "wikipedia-mcp" -NotePropertyValue @{
            "command" = $venvPythonPath
            "args" = @($mcpServerPath)
        } -Force
        
        # Save config
        $config | ConvertTo-Json -Depth 10 | Set-Content -Path $ClaudeDesktopConfigPath
        
        Write-Log "Claude Desktop configured to use Wikipedia MCP API server"
    }
}

# Final message
Write-Log "Installation complete!"
Write-Log "To use the Wikipedia MCP API server with Claude Desktop:"
Write-Log "1. Restart Claude Desktop if it's running"
Write-Log "2. You should now see Wikipedia tools available in Claude Desktop"
Write-Log "   - wikipedia_search"
Write-Log "   - wikipedia_article"
Write-Log "   - wikipedia_summary"
Write-Log "   - wikipedia_citations"
Write-Log "   - wikipedia_structured"
Write-Log "   - wikipedia_sections"
Write-Log "For manual testing, run: $RepoPath\venv\Scripts\python.exe $RepoPath\mcp_server.py" 