from fastapi import FastAPI
from managers.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, update_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from typing import List 

app = FastAPI()


@app.get("/ideas", response_model=List[IdeaOut])
# @app.get("/ideas")
def root():
    return get_ideas()

@app.post("/ideas")
def createIdea(idea: IdeaCreateInput):
    return create_idea(idea)

@app.post("/ideas/bulk")
def createIdeas(ideas: List[IdeaCreateInput]):
    return create_ideas(ideas)

@app.post("/ideas/update")
def updateIdea(idea: IdeaUpdateInput):
    return update_idea(idea)

@app.post("/ideas/update/bulk")
def updateIdeas(ideas: List[IdeaUpdateInput]):
    return update_ideas(ideas)

@app.post("/ideas/delete")
def deleteIdea(idea: IdeaDeleteInput):
    return delete_idea(idea)

@app.post("/ideas/delete/bulk")
def deleteIdeas(idea_ids: List[int]):
    return delete_ideas(idea_ids)

@app.post("/ideas/delete/all")
def deleteAllIdeas():
    return delete_all_ideas()





