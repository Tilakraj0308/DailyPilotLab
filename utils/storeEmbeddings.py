import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAPI"))


def get_embeddings(file_path):
    # 1. Read Excel
    df = pd.read_excel(file_path)

    # 2. Filter rows ONCE (keep alignment)
    df = df[["text", "category"]].dropna().reset_index(drop=True)

    # Ensure text is string
    df["text"] = df["text"].astype(str)

    # 3. Generate embeddings (order preserved)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=df["text"].tolist()
    )

    # 4. Attach embeddings by index
    df["embeddings"] = [item.embedding for item in response.data]

    return df


df = get_embeddings('text_category_sentences.xlsx')

df.to_json(
    "text_category_sentences_with_embeddings.json",
    orient="records",
    indent=2
)

