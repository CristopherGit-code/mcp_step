import asyncio, json
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from servers.modules.oci_client import Client
from servers.modules.config import Settings

settings = Settings("mcp.yaml")
oci_llm = Client(settings)

class MCPClient:
    def __init__(self, id:int):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.id = id

    ### Connect to the server -----------------------------------------------------------------
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        # List available resources
        response = await self.session.list_resources()
        resources = response.resources
        print("\nConnected to server with resources:", [resource.name for resource in resources])

        response = await self.session.list_resource_templates()
        templates = response.resourceTemplates
        print(templates)
        #print("\nConnected to server with templates:", [template.name for template in templates])

        response = await self.session.list_prompts()
        prompts = response.prompts
        print("\nConnected to server with prompts:", [prompt.name for prompt in prompts])
    
    ### Answer the user query -------------------------------------------------------------------------------
    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        final_text = []
        return_format = """{"tool_name": "selected toolname","arguments":{"name arg1":value,"name arg2":value}} """
        tool_prompt = settings.decision_prompt + f' User prompt: {query}; tool list: {available_tools}; return JSON format template: {return_format}'
        initial_response = oci_llm.answer_prompt(tool_prompt)

        try:
            metadata = json.loads(initial_response)
        except Exception as e:
            metadata = None
        
        if not metadata:
            final_text.append(initial_response)
            return "\n".join(final_text)
        
        final_text.append(f"[Try calling tool {metadata}]")

        tool_name = metadata['tool_name']
        tool_args = metadata['arguments']

        try:
            #result = await self.session.get_prompt('debug_error',{'error':'Example code error'})
            #result = await self.session.read_resource("file://claude")
            #result = await self.session.read_resource("file://claude_files") TODO: fix
            result = await self.session.call_tool(tool_name,tool_args)
        except Exception as e:
            result = f'Failed to use tool: {e}'
            final_text.append(result)

        tool_response = []
        for content in result.content:
            tool_response.append(content.text)

        final_response = oci_llm.answer_prompt(f'{query}. Answer using the information from: {tool_response}')
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

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client_list = []
    idx = 0
    for client in sys.argv[1:]:
        mcp_client = MCPClient(idx)
        try:
            await mcp_client.connect_to_server(client)
        finally:
            client_list.append(mcp_client)
            idx +=1
        print(idx)
    
    try:
        await client_list[1].chat_loop()
    finally:
        await client_list[1].cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())

"""
// Use a resource template
  const templates = resourcesResult.resourceTemplates;
  if (templates.length > 0) {
    const template = templates[0];
    console.log(`Using template: ${template.name} (${template.uriTemplate})`);
    
    // Example: if template is "file:///{path}"
    const uri = template.uriTemplate.replace('{path}', 'example.txt');
    
    try {
      const contentResult = await client.readResource(uri);
      console.log('Template resource content:', contentResult.contents[0].text);
    } catch (error) {
      console.error('Error accessing template resource:', error);
    }
  }
}


import { Client } from '@modelcontextprotocol/sdk/client/index.js';

async function discoverAndUsePrompts(client: Client) {
  // Discover available prompts
  const promptsResult = await client.listPrompts();
  console.log('Available prompts:', promptsResult.prompts);
  
  // Find a specific prompt
  const codeReviewPrompt = promptsResult.prompts.find(prompt => prompt.name === 'code-review');
  
  if (codeReviewPrompt) {
    console.log('Found code review prompt:', codeReviewPrompt);
    console.log('Arguments:', codeReviewPrompt.arguments);
    
    // Use the prompt with arguments
    try {
      const promptArgs = {
        code: 'function hello() { return "world"; }',
        language: 'javascript'
      };
      
      const result = await client.getPrompt('code-review', promptArgs);
      
      console.log('Prompt result:', result);
      console.log('Messages to send to LLM:', result.messages);
      
      // Now you can send these messages to your LLM
      // const llmResponse = await sendToLLM(result.messages);
    } catch (error) {
      console.error('Error using prompt:', error);
    }
  } else {
    console.log('Code review prompt not found');
  }
}

"""