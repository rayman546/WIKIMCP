<#
.SYNOPSIS
    Installer script for Wikipedia MCP API for Claude Desktop.

.DESCRIPTION
    This script automates the installation and configuration of the Wikipedia MCP API
    for use with Claude Desktop. It performs the following actions:
    - Checks for prerequisites (Python, Git)
    - Clones the repository (if needed)
    - Sets up a virtual environment
    - Installs dependencies
    - Configures Claude Desktop to use the Wikipedia MCP API
    - Optionally starts the server

.PARAMETER RepoPath
    Path where the Wikipedia MCP API will be installed. Defaults to "C:\Claude\WIKIMCP".

.PARAMETER CloneRepo
    Whether to clone the repository or use an existing one. Defaults to $true.

.PARAMETER StartServer
    Whether to start the server after installation. Defaults to $true.

.PARAMETER ModifyConfig
    Whether to modify the Claude Desktop configuration. Defaults to $true.

.EXAMPLE
    .\install.ps1

.EXAMPLE
    .\install.ps1 -RepoPath "D:\Projects\WIKIMCP" -CloneRepo $false -StartServer $false

.NOTES
    Author: Wikipedia MCP API Team
    Version: 1.0
#>

param (
    [string]$RepoPath = "C:\Claude\WIKIMCP",
    [bool]$CloneRepo = $true,
    [bool]$StartServer = $true,
    [bool]$ModifyConfig = $true
)

# Global variables
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/rayman546/WIKIMCP.git"
$ClaudeConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$BackupSuffix = ".backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
$MinPythonVersion = [Version]"3.8.0"
$VenvPath = Join-Path $RepoPath "venv"
$InstallLogPath = Join-Path $RepoPath "install_log.txt"

# Helper functions
function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Output to console
    if ($Level -eq "ERROR") {
        Write-Host $logMessage -ForegroundColor Red
    } elseif ($Level -eq "WARNING") {
        Write-Host $logMessage -ForegroundColor Yellow
    } elseif ($Level -eq "SUCCESS") {
        Write-Host $logMessage -ForegroundColor Green
    } else {
        Write-Host $logMessage
    }
    
    # Write to log file if path exists
    if (Test-Path (Split-Path $InstallLogPath -Parent)) {
        Add-Content -Path $InstallLogPath -Value $logMessage
    }
}

function Test-Command {
    param (
        [string]$Command
    )
    
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Test-PythonVersion {
    param (
        [Version]$MinVersion
    )
    
    try {
        $versionString = python --version 2>&1
        if ($versionString -match 'Python (\d+\.\d+\.\d+)') {
            $version = [Version]$Matches[1]
            return $version -ge $MinVersion
        }
        return $false
    } catch {
        return $false
    }
}

function Backup-ConfigFile {
    param (
        [string]$ConfigPath
    )
    
    try {
        if (Test-Path $ConfigPath) {
            $backupPath = "$ConfigPath$BackupSuffix"
            Copy-Item -Path $ConfigPath -Destination $backupPath -Force
            Write-Log "Backed up Claude Desktop config to $backupPath" -Level "INFO"
            return $backupPath
        } else {
            Write-Log "Claude Desktop config file does not exist at $ConfigPath" -Level "WARNING"
            return $null
        }
    } catch {
        Write-Log "Failed to backup config file: $_" -Level "ERROR"
        throw
    }
}

function Update-ClaudeConfig {
    param (
        [string]$ConfigPath,
        [string]$ServerPath
    )
    
    try {
        # Create default config if it doesn't exist
        if (-not (Test-Path $ConfigPath)) {
            Write-Log "Creating new Claude Desktop config file" -Level "INFO"
            $defaultConfig = @{
                mcpServers = @{}
            } | ConvertTo-Json -Depth 10
            New-Item -Path (Split-Path $ConfigPath -Parent) -ItemType Directory -Force | Out-Null
            Set-Content -Path $ConfigPath -Value $defaultConfig
        }
        
        # Backup existing config
        $backupPath = Backup-ConfigFile -ConfigPath $ConfigPath
        
        # Read the current config
        $config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        
        # Initialize mcpServers if it doesn't exist
        if (-not $config.mcpServers) {
            $config | Add-Member -NotePropertyName mcpServers -NotePropertyValue @{}
        }
        
        # Add or update the wikipedia-mcp server
        $scriptPath = Join-Path $ServerPath "run.py"
        $config.mcpServers | Add-Member -NotePropertyName "wikipedia-mcp" -NotePropertyValue @{
            command = "python"
            args = @($scriptPath)
        } -Force
        
        # Save the updated config
        $config | ConvertTo-Json -Depth 10 | Set-Content -Path $ConfigPath
        Write-Log "Updated Claude Desktop config to include Wikipedia MCP API" -Level "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to update Claude Desktop config: $_" -Level "ERROR"
        
        # Restore backup if it exists
        if ($backupPath -and (Test-Path $backupPath)) {
            Copy-Item -Path $backupPath -Destination $ConfigPath -Force
            Write-Log "Restored config from backup" -Level "INFO"
        }
        
        return $false
    }
}

function Start-WikiMCP {
    param (
        [string]$RepoPath,
        [string]$VenvPath
    )
    
    try {
        $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
        $scriptPath = Join-Path $RepoPath "run.py"
        
        if (-not (Test-Path $pythonExe)) {
            Write-Log "Virtual environment Python not found at $pythonExe" -Level "ERROR"
            return $false
        }
        
        if (-not (Test-Path $scriptPath)) {
            Write-Log "Server script not found at $scriptPath" -Level "ERROR"
            return $false
        }
        
        # Start the server in a new PowerShell window
        $command = "& '$pythonExe' '$scriptPath'"
        Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $command
        
        Write-Log "Started Wikipedia MCP API server in a new window" -Level "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to start Wikipedia MCP API server: $_" -Level "ERROR"
        return $false
    }
}

# Main installation logic
function Install-WikiMCP {
    # Display welcome banner
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Cyan
    Write-Host "   Wikipedia MCP API Installer for Claude Desktop" -ForegroundColor Cyan
    Write-Host "=========================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check prerequisites
    Write-Log "Checking prerequisites..." -Level "INFO"
    
    # Check Python
    if (-not (Test-Command "python")) {
        Write-Log "Python is not installed or not in PATH. Please install Python 3.8 or higher." -Level "ERROR"
        return $false
    }
    
    if (-not (Test-PythonVersion -MinVersion $MinPythonVersion)) {
        Write-Log "Python 3.8 or higher is required. Please update Python." -Level "ERROR"
        return $false
    }
    
    Write-Log "Python check passed" -Level "SUCCESS"
    
    # Check Git if we need to clone
    if ($CloneRepo -and -not (Test-Command "git")) {
        Write-Log "Git is not installed or not in PATH. Please install Git or use existing repository." -Level "ERROR"
        Write-Log 'You can install without cloning by using the -CloneRepo $false parameter.' -Level "INFO"
        return $false
    }
    
    # Create or verify repository directory
    if (-not (Test-Path $RepoPath)) {
        try {
            New-Item -Path $RepoPath -ItemType Directory -Force | Out-Null
            Write-Log "Created directory: $RepoPath" -Level "SUCCESS"
        } catch {
            Write-Log "Failed to create directory $RepoPath: $_" -Level "ERROR"
            return $false
        }
    } else {
        Write-Log "Using existing directory: $RepoPath" -Level "INFO"
    }
    
    # Clone repository if needed
    if ($CloneRepo) {
        Write-Log "Cloning repository from $RepoUrl..." -Level "INFO"
        
        # Check if directory is empty
        if ((Get-ChildItem -Path $RepoPath | Measure-Object).Count -gt 0) {
            Write-Log "Directory is not empty. Do you want to proceed and potentially overwrite files? (y/n)" -Level "WARNING"
            $response = Read-Host
            if ($response -ne "y") {
                Write-Log "Installation cancelled by user" -Level "INFO"
                return $false
            }
        }
        
        try {
            Push-Location $RepoPath
            git clone $RepoUrl .
            $cloneSuccess = $?
            Pop-Location
            
            if (-not $cloneSuccess) {
                Write-Log "Failed to clone repository" -Level "ERROR"
                return $false
            }
            
            Write-Log "Repository cloned successfully" -Level "SUCCESS"
        } catch {
            Write-Log "Failed to clone repository: $_" -Level "ERROR"
            return $false
        }
    } else {
        Write-Log "Skipping repository clone as requested" -Level "INFO"
        
        # Check if this is a valid WIKIMCP repository
        if (-not (Test-Path (Join-Path $RepoPath "run.py")) -or 
            -not (Test-Path (Join-Path $RepoPath "requirements.txt"))) {
            Write-Log "The specified directory does not appear to contain the Wikipedia MCP API repository" -Level "ERROR"
            Write-Log "Please check the path or use -CloneRepo `$true to clone a fresh copy" -Level "INFO"
            return $false
        }
    }
    
    # Create virtual environment
    Write-Log "Creating Python virtual environment..." -Level "INFO"
    try {
        Push-Location $RepoPath
        python -m venv $VenvPath
        $venvSuccess = $?
        Pop-Location
        
        if (-not $venvSuccess) {
            Write-Log "Failed to create virtual environment" -Level "ERROR"
            return $false
        }
        
        Write-Log "Virtual environment created successfully" -Level "SUCCESS"
    } catch {
        Write-Log "Failed to create virtual environment: $_" -Level "ERROR"
        return $false
    }
    
    # Install dependencies
    Write-Log "Installing dependencies..." -Level "INFO"
    try {
        $pipExe = Join-Path $VenvPath "Scripts\pip.exe"
        $requirementsPath = Join-Path $RepoPath "requirements.txt"
        
        & $pipExe install -r $requirementsPath
        $installSuccess = $?
        
        if (-not $installSuccess) {
            Write-Log "Failed to install dependencies" -Level "ERROR"
            return $false
        }
        
        Write-Log "Dependencies installed successfully" -Level "SUCCESS"
    } catch {
        Write-Log "Failed to install dependencies: $_" -Level "ERROR"
        return $false
    }
    
    # Update Claude Desktop configuration
    if ($ModifyConfig) {
        Write-Log "Updating Claude Desktop configuration..." -Level "INFO"
        $configSuccess = Update-ClaudeConfig -ConfigPath $ClaudeConfigPath -ServerPath $RepoPath
        
        if (-not $configSuccess) {
            Write-Log "Failed to update Claude Desktop configuration" -Level "ERROR"
            Write-Log "You may need to configure it manually" -Level "INFO"
        } else {
            Write-Log "Claude Desktop configuration updated successfully" -Level "SUCCESS"
        }
    } else {
        Write-Log "Skipping Claude Desktop configuration as requested" -Level "INFO"
        Write-Log "You will need to configure Claude Desktop manually" -Level "INFO"
    }
    
    # Start the server if requested
    if ($StartServer) {
        Write-Log "Starting Wikipedia MCP API server..." -Level "INFO"
        $startSuccess = Start-WikiMCP -RepoPath $RepoPath -VenvPath $VenvPath
        
        if (-not $startSuccess) {
            Write-Log "Failed to start Wikipedia MCP API server" -Level "ERROR"
            Write-Log "You may need to start it manually" -Level "INFO"
        }
    } else {
        Write-Log "Skipping server start as requested" -Level "INFO"
    }
    
    # Display success message and usage instructions
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Green
    Write-Host "   Wikipedia MCP API Installation Complete!" -ForegroundColor Green
    Write-Host "=========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation Details:" -ForegroundColor Cyan
    Write-Host "  - Repository: $RepoPath" -ForegroundColor White
    Write-Host "  - Virtual Environment: $VenvPath" -ForegroundColor White
    Write-Host "  - Claude Config: $ClaudeConfigPath" -ForegroundColor White
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Restart Claude Desktop to load the new configuration" -ForegroundColor White
    
    if (-not $StartServer) {
        Write-Host "  2. Start the server manually with:" -ForegroundColor White
        Write-Host "     cd $RepoPath" -ForegroundColor White
        Write-Host "     $VenvPath\Scripts\python.exe run.py" -ForegroundColor White
    } else {
        Write-Host "  2. Server is running in a separate window" -ForegroundColor White
    }
    
    Write-Host "  3. In Claude Desktop, you should now see Wikipedia MCP tools available" -ForegroundColor White
    Write-Host ""
    Write-Host "For troubleshooting, see: $InstallLogPath" -ForegroundColor White
    Write-Host ""
    
    return $true
}

# Run the installation
$installationResult = Install-WikiMCP

# Return exit code based on installation result
if ($installationResult) {
    exit 0
} else {
    exit 1
} 