# Wikipedia MCP API Installation Checklist

This checklist guides you through the process of installing and configuring the Wikipedia MCP API for Claude Desktop.

## Prerequisites

- [ ] Python 3.8 or higher installed
- [ ] Git installed (for cloning the repository)
- [ ] Claude Desktop installed
- [ ] Internet connection for downloading dependencies

## Automatic Installation (Windows)

- [ ] Download the `install.ps1` script
- [ ] Open PowerShell as Administrator
- [ ] Navigate to the directory containing the script
- [ ] Run the script: `.\install.ps1`
- [ ] Follow the on-screen prompts
- [ ] Restart Claude Desktop after installation

## Manual Installation

### 1. Set Up the Repository

- [ ] Clone the repository: `git clone https://github.com/rayman546/WIKIMCP.git`
- [ ] Navigate to the repository directory: `cd WIKIMCP`

### 2. Set Up Python Environment

- [ ] Create a virtual environment: `python -m venv venv`
- [ ] Activate the virtual environment:
  - Windows: `.\venv\Scripts\activate`
  - macOS/Linux: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`

### 3. Configure Claude Desktop

- [ ] Locate the Claude Desktop configuration file:
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`
- [ ] Add the Wikipedia MCP API configuration to the file:
  ```json
  {
    "mcpServers": {
      "wikipedia-mcp": {
        "command": "python",
        "args": ["path/to/WIKIMCP/run.py"]
      }
    }
  }
  ```
- [ ] Save the configuration file
- [ ] Restart Claude Desktop

### 4. Run the Server

- [ ] Navigate to the repository directory
- [ ] Activate the virtual environment if not already activated
- [ ] Run the server: `python run.py`
- [ ] Keep the server running while using Claude Desktop

## Verification

- [ ] Open Claude Desktop
- [ ] Check that the Wikipedia MCP tools are available
- [ ] Test the functionality by asking Claude to search for a Wikipedia article

## Troubleshooting

- [ ] Check the server console for error messages
- [ ] Verify that the Claude Desktop configuration file is correctly formatted
- [ ] Ensure the server is running on the correct port (default: 8000)
- [ ] Check that the virtual environment is activated when running the server
- [ ] Restart Claude Desktop after making configuration changes

## Uninstallation

- [ ] Remove the Wikipedia MCP API configuration from the Claude Desktop configuration file
- [ ] Restart Claude Desktop
- [ ] Delete the repository directory 