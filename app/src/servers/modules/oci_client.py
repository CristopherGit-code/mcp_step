import oci,logging, ast
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference import models
from .config import Settings

logger = logging.getLogger(name=f'File.{__name__}----------->')

# General variables --------------------------
PREAMBLE = 'Answer in maximum, 200 words'
MESSAGE = ''

class Client:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config = oci.config.from_file(
            self.settings.oci_client.config_path, 
            self.settings.oci_client.configProfile)
        self.endpoint = self.settings.oci_client.endpoint
        self.client = GenerativeAiInferenceClient(
            config=self.config, 
            service_endpoint=self.endpoint, 
            retry_strategy=oci.retry.NoneRetryStrategy(), 
            timeout=(10,240))
        
        self.chat_detail = models.ChatDetails()
        self.chat_detail.serving_mode = models.OnDemandServingMode(
            model_id=self.settings.oci_client.model_id)
        self.chat_detail.compartment_id = self.settings.oci_client.compartiment

        self.message_db = {}
        self.message_history = [] # user

        self.chat_request = models.CohereChatRequest()
        self.chat_request.preamble_override = PREAMBLE # user
        self.chat_request.message = MESSAGE #user
        self.chat_request.max_tokens = self.settings.oci_client.max_tokens
        self.chat_request.temperature = self.settings.oci_client.temperature
        self.chat_request.frequency_penalty = self.settings.oci_client.freq_penalty
        self.chat_request.top_p = self.settings.oci_client.top_p
        self.chat_request.top_k = self.settings.oci_client.top_k
        self.chat_request.chat_history = self.message_history #user
        
    def _get_chat_details(self):
        self.chat_detail.chat_request = self._get_chat_request()

        return self.chat_detail
    
    # Chat parameters
    def _get_chat_request(self):
        return self.chat_request
    
    def _set_chat_request(self, prompt, instructions):
        self.chat_request.preamble_override = PREAMBLE + instructions # user (keep 200 word limit)
        self.chat_request.message = prompt #user
    
    def _call_client(self,u_prompt, sys_instructions=''):
        self.message_history.append(models.CohereUserMessage(message=u_prompt))
        try:
            self._set_chat_request(u_prompt, sys_instructions)
            client_config = self._get_chat_details()
            chat_response = self.client.chat(client_config)
            generated_response = chat_response.data.chat_response.text
            ## Use tokens from the model call
            tokens = chat_response.data.chat_response.usage.total_tokens
        except oci.exceptions.ServiceError as s:
            logger.debug(s)
            generated_response = f'Error in fetching the message: {s.message}'
        except Exception as e:
            logger.debug(e)
            generated_response = 'General internal error'
        self.message_history.append(models.CohereChatBotMessage(message=generated_response))
        return generated_response
    
    def provide_analysis(self, query:str, u_instructions:str = '') -> str:
        prompt = self.settings.analysis_prompt + query
        instructions = self.settings.analysis_instructions + u_instructions
        response = self._call_client(prompt,instructions)
        return response

    def filter_files(self, query:str) -> list:
        prompt = self.settings.filter_prompt + query
        instructions = self.settings.filter_instructions
        response = self._call_client(prompt, instructions)
        try:
            r_dict = ast.literal_eval(response)
        except Exception as e:
            r_dict = [2010,None,None,None]
        return r_dict
    
    def summarize(self,query:str) -> str:
        prompt = query
        response = self._call_client(prompt,'answer in at least 6 bullet points and use just the information provided')
        return response
    
    def answer_prompt(self, prompt, instructions='')->str:
        response = self._call_client(prompt,instructions)
        return response
    
    def reset_chat(self):
        self.message_history = []

def main():
    settings = Settings("mcp.yaml")
    llm = Client(settings)
    while True:
        question = input('user: ')
        if question.lower() == "quit":
            break
        ans = llm._call_client(question)
        print('model:',ans)
    """
    {
  "api_format": "COHERE",
  "chat_history": [
    {
      "message": "what is the capital of congo?",
      "role": "USER"
    },
    {
      "message": "what is the capital of congo?",
      "role": "USER"
    },
    {
      "message": "The capital of the Republic of the Congo is Brazzaville.",
      "role": "CHATBOT",
      "tool_calls": null
    }
  ],
  "citations": null,
  "documents": null,
  "error_message": null,
  "finish_reason": "COMPLETE",
  "is_search_required": null,
  "prompt": null,
  "search_queries": null,
  "text": "The capital of the Republic of the Congo is Brazzaville.",
  "tool_calls": null,
  "usage": {
    "completion_tokens": 11,
    "completion_tokens_details": null,
    "prompt_tokens": 25,
    "prompt_tokens_details": null,
    "total_tokens": 36
  }
}
    """
    
if __name__ == "__main__":
    main()