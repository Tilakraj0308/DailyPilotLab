
from fastapi import FastAPI

app = FastAPI()


@app.get("/ideas")
async def root():
    return {"message": "Hello World"}