from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
from typing import List, Union

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAPI"))


async def get_embeddings(content: Union[str, List[str]]):
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=content
    )

    return response.data

