from dotenv import load_dotenv
load_dotenv()
from src.servers.modules.config import Settings
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from langgraph.prebuilt import create_react_agent
from mcp.client.stdio import stdio_client
import json, asyncio, logging
from langgraph.errors import GraphRecursionError

settings = Settings("C:/Users/Cristopher Hdz/Desktop/Test/mcp_step/app/src/config/mcp.yaml")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f'Host.{__name__}')

llm = ChatOCIGenAI(
    model_id="cohere.command-a-03-2025",
    service_endpoint=settings.oci_client.endpoint,
    compartment_id=settings.oci_client.compartiment,
    model_kwargs={"temperature":0.7, "max_tokens":500},
    auth_profile=settings.oci_client.configProfile,
    auth_file_location=settings.oci_client.config_path
)

class JSONFormatter(json.JSONEncoder):
    def default(self, o):
        if hasattr(o,"content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

server_params = StdioServerParameters(
    command="python",
    args=["servers/weather.py"]
)

with open("C:/Users/Cristopher Hdz/Desktop/Test/mcp_step/app/src/config/server.json",'r') as config:
    data = config.read()
    metadata = json.loads(data)

client = MultiServerMCPClient(metadata)

""" 
for online server connection
{
    "name":{
        "url": "server-url",
        "transport": "streamable_http",
    }
} """

async def lang_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(llm,[tools])
            logger.debug("Connected to server")
            while True:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await agent.ainvoke({"messages":query})
                try:
                    formatted = json.dumps(response,indent=2,cls=JSONFormatter)
                except Exception:
                    formatted = str(response)
                print(f"Response:\n{formatted}")

async def lang_multiclient():
    max_iterations = 5
    recursion_limit = 2*max_iterations + 1
    tools = await client.get_tools()
    agent = create_react_agent(llm,tools)
    logger.debug("Connected to server")
    while True:
        query = input("\nQuery: ").strip()

        if query.lower() == 'quit':
            break

        final_response = []
        
        try:
            async for chunk in agent.astream(
                {"messages":query},
                {"recursion_limit":recursion_limit},
                stream_mode="updates"
            ):
                # logger.debug(chunk)
                try:
                    formatted = json.dumps(chunk,indent=2,cls=JSONFormatter)
                except Exception:
                    formatted = str(chunk)
                final_response.append(formatted)
                print(formatted)
        except GraphRecursionError:
            logger.debug("Agent stopped for recursion error/limit")
        print("MODEL response:\n",final_response[-1])


if __name__ == "__main__":
    # asyncio.run(lang_agent())
    asyncio.run(lang_multiclient())
