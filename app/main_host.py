from dotenv import load_dotenv
load_dotenv()
from src.servers.modules.config import Settings
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
import json, asyncio, logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f'Host.{__name__}')

class JSONFormatter(json.JSONEncoder):
    def default(self, o):
        if hasattr(o,"content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)
    
class LangAgent:
    _instance = None
    _initialized = False

    async def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LangAgent,cls).__new__(cls)
            await cls._instance._init()
        return cls._instance
    
    async def _init(self):
        if self._initialized:
            return
        self._settings = Settings("C:/Users/Cristopher Hdz/Desktop/Test/mcp_step/app/src/config/mcp.yaml")
        self._max_iterations = 6
        self.recursion_limit = 2 * self._max_iterations + 1
        self._checkpointer = InMemorySaver()
        self._build_llm()
        await self._build_lang_agent()
        self._initialized = True

    def _build_llm(self):
        self._llm = ChatOCIGenAI(
            model_id="cohere.command-a-03-2025",
            service_endpoint=self._settings.oci_client.endpoint,
            compartment_id=self._settings.oci_client.compartiment,
            model_kwargs={"temperature":0.7, "max_tokens":500},
            auth_profile=self._settings.oci_client.configProfile,
            auth_file_location=self._settings.oci_client.config_path
        )
    
    def _get_server_connection_data(self):
        with open(self._settings.client_settings.path,'r') as config:
            config_data = config.read()
            server_data = json.loads(config_data)
            return server_data
        
    async def _build_lang_agent(self):
        server_data = self._get_server_connection_data()
        self._client = MultiServerMCPClient(server_data)
        tools = await self._client.get_tools()
        self.agent = create_react_agent(
            self._llm, tools,
            checkpointer=self._checkpointer
        )
        logger.debug("Agent redy")
    
    async def process_query(self,query)->str:
        final_response = []
        try:
            async for chunk in self.agent.astream(
                {"messages":query},
                {"recursion_limit":self.recursion_limit,"configurable":{"thread_id":"1"}},
                subgraphs=False,
                stream_mode="updates"
            ):
                try:
                    formatted = json.dumps(chunk,indent=2,cls=JSONFormatter)
                except Exception:
                    formatted = str(chunk)
                final_response.append(formatted)
                logger.debug(formatted)
        except GraphRecursionError as g:
            final_response.append(f"Agent stopped for recursion error/limit: {g}")
            return final_response[-1]

        message = json.loads(final_response[-1])
        final_text = str(message.get('agent').get('messages')[0].get('content'))

        return final_text
    
    def thread_history(self):
        _config = {
            "configurable": {
                "thread_id": "1"
            }
        }
        history = list(self.agent.get_state_history(_config))
        logger.debug(history)

async def main():
    lang_agent = await LangAgent()
    while True:
        query = input("\nQuery: ").strip()
        if query.lower() == 'quit':
            break

        try:
            response = await lang_agent.process_query(query)
            print(f"\nModel response:\n{response}")
        except Exception as e:
            print(f"\nError in response:\n{e}")
    lang_agent.thread_history()

if __name__ == "__main__":
    asyncio.run(main())