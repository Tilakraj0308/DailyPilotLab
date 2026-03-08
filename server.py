from fastapi import FastAPI, Response
from utils.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, raw_to_refined_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from utils.helpers import assign_idea_to_topic, semantic_search_memories
from typing import List 
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
    
@app.get("/ideas", response_model=List[IdeaOut])
# @app.get("/ideas")
def getIdeas():
    return get_ideas()

@app.post("/ideas")
def createIdea(idea: IdeaCreateInput, response: Response):
    creation_response = create_idea(idea)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.post("/ideas/bulk")
def createIdeas(ideas: List[IdeaCreateInput], response: Response):
    creation_response = create_ideas(ideas)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

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

@app.get("/semantic-search")
def semanticSearch(query: str):
    return semantic_search_memories(query)

@app.get("/refine-ideas")
def refineIdeas(response: Response):
    refine_response = raw_to_refined_ideas()
    response.status_code = refine_response['status']
    return {'message': refine_response['message']}





