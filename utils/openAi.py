from openai import OpenAI
import os
from typing import List, Union
import os
from pydantic import BaseModel

class OpenAIWrapper:

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAPI"))

    def get_embeddings(self, content: Union[str, List[str]]):
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )
        return response.data

    def get_chat_completion(self, system_prompt: str, user_prompt: str, response_format: BaseModel = None, model: str = "gpt-3.5-turbo"):
        response = self.client.responses.parse(
            model="gpt-5-nano",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            text_format=response_format
        )
        structured_output = response.output_parsed

        return structured_output

openai_client = OpenAIWrapper()