from mcp.server.fastmcp import FastMCP
from typing import Any
import os

mcp = FastMCP("file system")

@mcp.resource("file://claude")
def find_file()->list[Any]:
    path = r"C:\Users\Cristopher Hdz\Desktop\claude_files"
    return os.listdir(path)

@mcp.resource("file://{name}")
def find_file(name:str)->list[Any]:
    path = rf"C:\Users\Cristopher Hdz\Desktop\{name}"
    return os.listdir(path)

@mcp.tool()
def open_file(path:str)->str:
    """Reads the content of a file given a path by the user"""
    with open(path,'r') as file:
        content = file.read()
        return f'File content:\n{content}'
    
@mcp.tool()
def write_file(path:str, content:str)->str:
    """Writes content into a file path, could be provided or default, current directory"""
    llm_data = str(content)
    with open(path,'w') as file:
        data = "\n"+llm_data
        file.write(data)
    return "File written successfully"

@mcp.tool()
def delete_file(path:str)->str:
    """Deletes a file given a path from the user"""
    os.remove(path)
    return f"File deleted at {path}"

@mcp.tool()
def rename_file(path:str,new_name:str)->str:
    """Renames a file from a specific directory and a given name"""
    os.rename(path,new_name)
    return f"File renamed as {new_name}"

@mcp.tool()
def create_dir(path:str)->str:
    """Creates a directory in the specified path"""
    os.mkdir(path)
    return "Dir created"

if __name__ == "__main__":
    mcp.run(transport='stdio')