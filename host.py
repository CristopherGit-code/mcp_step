from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from typing import Dict,Any
import asyncio, json, logging
from dotenv import load_dotenv
from servers.modules.config import Settings
from servers.modules.oci_client import Client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f'HOST.{__name__}')

class MCP_ConnectionManager:
    _instance = None
    _initializaed = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCP_ConnectionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not MCP_ConnectionManager._initializaed:
            self.connections: Dict[str,ClientSession] = {}
            self.async_stacks: Dict[str,AsyncExitStack] = {}
            self.exit_stack = AsyncExitStack()
            MCP_ConnectionManager._initializaed = True

    async def connectToServer(self, id:str, command:str, server_args:list[str]) -> ClientSession:
        server_params = StdioServerParameters(
            command=command,
            args=server_args,
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await session.initialize()

        self.connections[id] = session
        self.async_stacks[id] = self.exit_stack

        logger.info(f"connected to server: {id}")
    
    def get_client(self, id:str) -> ClientSession | None:
        return self.connections[id]
    
    def get_all_clients(self) -> list[ClientSession]:
        keys = self.connections.keys()
        clients = []
        for key in keys:
            clients.append(self.connections[key])
        return clients

    async def get_all_tools(self) -> list[Any]:
        keys = self.connections.keys()
        all_tools = []
        for key in keys:
            try:
                tool_list = await self.connections[key].list_tools()
                server_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }for tool in tool_list.tools]
                all_tools.append({"server":key,"tools":server_tools})
            except Exception as e:
                all_tools.append({"server":key,"tools":[e]})
        return all_tools
    
    async def disconnect_all_clients(self):
        keys = self.connections.keys()
        for key in keys:
            client = self.async_stacks[key]
            try:
                await client.aclose()
                logger.info(f'Disconnected from client: {key}')
            except Exception as e:
                logger.info(f'Failed to disconnect from {key} due to error: {e}')

class MCP_HostManager:
    def __init__(self):
        load_dotenv()
        self.settings = Settings("mcp.yaml")
        self.oci_llm = Client(self.settings)
        self.servers = MCP_ConnectionManager()

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        response = await self.servers.get_all_tools()
        #logger.debug(response)
        final_text = []
        return_format = """{"server": "name of the server the tool is from","tool_name": "selected toolname","arguments":{"name arg1":value,"name arg2":value}} """
        tool_prompt = self.settings.decision_prompt + f' User prompt: {query}; tool list: {response}; return JSON format template: {return_format}'
        initial_response = self.oci_llm.answer_prompt(tool_prompt)

        try:
            temp_llm = Client(self.settings)
            prompt = f'Analyse the following text: {initial_response}. If the text is similar to a JSON format but incomplete or with errors, fix the sintax from the format accoring to the template: {return_format}. Do not add extra fields or information. If the format is correct, do not modify and return the same format just as given. If the text is not similar to a JSON format, rather a natural response, just return the same text.'
            temp_json = temp_llm.answer_prompt(prompt)
            logger.debug(temp_json)
            metadata = json.loads(temp_json)
        except Exception as e:
            metadata = None
        
        if not metadata:
            final_text.append(initial_response)
            return "\n".join(final_text)
        
        final_text.append(f"[Try calling tool {metadata}]")

        tool_server = metadata['server']
        tool_name = metadata['tool_name']
        tool_args = metadata['arguments']
        current_server = self.servers.get_client(tool_server)

        try:
            response = await current_server.call_tool(tool_name,tool_args)
        except Exception as e:
            response = f'Failed to use tool: {e}'
            final_text.append(response)

        logger.debug(f'tool response: {response}')

        tool_response = []
        for content in response.content:
            tool_response.append(content.text)

        final_response = self.oci_llm.answer_prompt(f'{query}. Answer the query. Here is some context information: {tool_response}',"Answer in less than 300 words. Address as much as possible the best answer for the user in the given context")
        final_text.append(final_response)

        return "\n".join(final_text)
    
    ### Chat interface --------------------------------------------------------
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nUSER: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\nMODEL RESPONSE: " + response)

            except Exception as e:
                print(f"\nError: {str(e)}")
    
async def main():
    mcp_client_manger = MCP_ConnectionManager()
    host = MCP_HostManager()
    try:
        await mcp_client_manger.connectToServer("slack","python",["servers/slack_server.py"])
        await mcp_client_manger.connectToServer("wl_db","python",["servers/wl_server.py"])
        await mcp_client_manger.connectToServer("file_system","python",["servers/filesys_server.py"])
        await mcp_client_manger.connectToServer("weather","python",["servers/weather.py"])
        await host.chat_loop()
    finally:
        await mcp_client_manger.disconnect_all_clients()
    print('\n-----------Closed host-----------\n')

if __name__ == "__main__":
    asyncio.run(main())