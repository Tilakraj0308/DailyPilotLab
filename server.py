from fastapi import FastAPI, Response
from utils.idea_manager import get_ideas, create_idea, update_idea, delete_idea, delete_ideas, delete_all_ideas, assign_idea_to_topic
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from typing import List 
from dotenv import load_dotenv
from utils.openAi import OpenAI

load_dotenv()
app = FastAPI()
    
@app.get("/ideas", response_model=List[IdeaOut])
# @app.get("/ideas")
def root():
    return get_ideas()

@app.post("/ideas")
def createIdea(idea: IdeaCreateInput, response: Response):
    creation_response = create_idea(idea)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

# @app.post("/ideas/bulk")
# def createIdeas(ideas: List[IdeaCreateInput]):
#     return create_ideas(ideas)

@app.post("/ideas/update")
def updateIdea(idea: IdeaUpdateInput):
    return update_idea(idea)

# @app.post("/ideas/update/bulk")
# def updateIdeas(ideas: List[IdeaUpdateInput]):
#     return update_ideas(ideas)

@app.post("/ideas/delete")
def deleteIdea(idea: IdeaDeleteInput):
    return delete_idea(idea)

@app.post("/ideas/delete/bulk")
def deleteIdeas(idea_ids: List[int]):
    return delete_ideas(idea_ids)

@app.post("/ideas/delete/all")
def deleteAllIdeas():
    return delete_all_ideas()

@app.get("/topics/assign")
def assignTopics(response: Response):
    creation_response = assign_idea_to_topic()
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}





