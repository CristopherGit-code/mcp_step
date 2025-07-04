# MCP host connection

### last update: 07-04-2015

MCP host connected to MCP servers to implement real-time information with LLM

## Features

- 4 available servers (Slack, Oracle DB, File system manager, weather)
- Terminal based UI
- Connection to all servers in the same session
- Tool selection by the LLM regarding the servers available
- Differenciation between needed tool calls or not

## Setup

1. Get the necessary dependencies (use python venv / toml):
    - envyaml
    - httpx
    - mcp
    - oci
    - oracledb
    - python-box
    - python-dotenv
    - slack-bolt
2. Create .env file to set the environment variables for Oracle DB and OCI client
    - For DB ensure a Cloud Wallet connection type
3. Modify ```mcp.yaml``` to call the env variables and set the parameters
4. Ensure the file paths in the ```main()``` function from ```host.py```
4. Run ```uv run host.py```

## Basic walkthrough

- [Demo video](walkthrough/MCP_Host_Demo.mp4)
- [Example](example/loss_causes.txt) example documents created by the file system server using DB and Slack data
    - Does not include files with information from win/loss application
- [servers](servers) folder containing the server setup to connect over the different applications
- Add more servers in the ```main()``` function from ```host.py```