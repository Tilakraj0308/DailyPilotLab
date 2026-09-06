from openai import OpenAI
from typing import List, Union
from pydantic import BaseModel
from services.ai_factory import AIFactory
import os

class OpenAIWrapper:

    def _get_client(self, user_id: str = None) -> OpenAI:
        if user_id:
            return AIFactory.get_openai_client(user_id)
        # Fallback to env var if no user_id (e.g. for global scripts/testing)
        return OpenAI(api_key=os.getenv("OPENAPI"))

    def _get_model(self, user_id: str = None, default_model: str = "gpt-4o-mini") -> str:
        if user_id:
            settings = AIFactory.get_user_ai_settings(user_id)
            return settings.get("model", default_model)
        return default_model

    def get_embeddings(self, content: Union[str, List[str]], user_id: str = None):
        client = self._get_client(user_id)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )
        return response.data

    def get_chat_completion(self, system_prompt: str, user_prompt: str, response_format: BaseModel = None, model: str = None, user_id: str = None):
        client = self._get_client(user_id)
        actual_model = model or self._get_model(user_id, "gpt-4o-mini")
        response = client.responses.parse(
            model=actual_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            text_format=response_format
        )
        structured_output = response.output_parsed

        return structured_output
    
    @property
    def client(self):
        return self._get_client(None)

openai_client = OpenAIWrapper()