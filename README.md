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
    - Call ```get_all_tools``` from ```host.py``` to know all the available tool options

## Basic walkthrough

- [Demo video](walkthrough/MCP_Host_Demo.mp4)
- [Architecture](walkthrough/MCP_architecture.png)
- [servers](servers) folder containing the server setup to connect over the different applications
- Add more servers in the ```main()``` function from ```host.py```
- [Example](example) example documents created by the file system server using DB and Slack data
    - Does not include files with information from win/loss application

# Important

Update to ```venv/lib/python3.13/site-packages/langgraph/checkpoint/serde/jsonplus.py```

more details could be found at: [langchain_forum](https://github.com/langchain-ai/langgraph/issues/4956)
Fix issue for: ```Type is not msgpack serializable: AIMessage```
Add return type for function ```def message_to_dict(msg)-> Dict[Any]:``` to avoid warning error