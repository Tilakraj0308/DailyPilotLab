
from fastapi import FastAPI
from managers.idea_manager import get_ideas, create_idea
from models.ideas import IdeaOut, IdeaCreate
from typing import List 

app = FastAPI()


# @app.get("/ideas", response_model=List[IdeaOut])
@app.get("/ideas")
def root():
    return get_ideas()

@app.post("/ideas")
def createIdea(idea: IdeaCreate):
    return create_idea(idea)