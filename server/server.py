from fastapi import FastAPI, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from utils.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, raw_to_refined_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from models.users import UserOut
from utils.helpers import assign_idea_to_topic, semantic_search_memories, update_traits
from utils.auth_middleware import get_current_user
from services.auth_service import get_or_create_user
from db.dbConnection import get_dict_cursor
from typing import List 
from dotenv import load_dotenv
from utils.topic_manager import update_topic_recency

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Authentication ─────────────────────────────────────────────────────────

@app.get("/auth/profile", response_model=UserOut)
def get_profile(user_id: int = Depends(get_current_user)):
    """
    Return the current user's profile.
    The user is auto-created on first call (handled inside get_current_user).
    """
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT id, email, display_name, avatar_url FROM public.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    return UserOut(**dict(user))


# ─── Ideas ───────────────────────────────────────────────────────────────────
    
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

@app.get("/update-topic-recency")
def updateTopicRecency(response: Response):
    update_response = update_topic_recency()
    response.status_code = update_response['status']
    return {'message': update_response['message']}

@app.get("/update-traits")  
def updateTraits(response: Response):
    update_response = update_traits()
    response.status_code = update_response['status']
    return {'message': update_response['message']}
