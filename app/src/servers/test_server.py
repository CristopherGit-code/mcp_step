from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

# Create an MCP server
mcp = FastMCP("Demo")

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# Add a dynamic greeting resource TEMPLATE
@mcp.resource("resource://greeting//example//{name}")
def get_greeting(name: str='') -> str:
    return f"Hello, {name}!"

@mcp.resource("resource://my-resource")
def get_name() -> str:
    return "Hello world"

@mcp.resource('file://text//{file_name}')
def get_file(file_name:str) -> str:
    name = f'File found: {file_name}'
    return name

@mcp.resource("config://app", title="Application Configuration")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"

@mcp.prompt(title="Code Review")
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"

@mcp.prompt(title="Debug Assistant")
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    mcp.run(transport='stdio')