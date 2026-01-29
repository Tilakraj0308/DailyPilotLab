from services.ideas_service import IdeaService
from models.ideas import IdeaCreate, IdeaUpdate
from utils.openaiEmbeddings import get_embeddings
from typing import List

def get_ideas():
    service = IdeaService()
    return service.get_all_ideas()

def get_idea(idea_id: int):
    service = IdeaService()
    return service.get_idea(idea_id)

def create_idea(idea: IdeaCreate):
    if not idea.embeddings and idea.content != "":
        embeddings = get_embeddings(idea.content)
        idea.embeddings = embeddings[0].embedding
    insert_data = idea.model_dump(exclude_unset=True)
    service = IdeaService()
    return service.create_idea(insert_data)

def create_ideas(ideas: List[IdeaCreate]):
    if not ideas:
        return
    texts_to_embed = []
    idea_indices_to_embed = []

    for i, idea in enumerate(ideas):
        if not idea.embeddings and idea.content != "":
            texts_to_embed.append(idea.content)
            idea_indices_to_embed.append(i)

    if texts_to_embed:
        embeddings_data = get_embeddings(texts_to_embed)
        for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
            ideas[idx].embeddings = embedding_obj.embedding
    data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
    service = IdeaService()
    return service.bulk_create_ideas(data_list)

def update_idea(idea_id: int, idea: IdeaUpdate):
    update_data = idea.model_dump(exclude_unset=True)
    service = IdeaService()
    return service.update_idea(idea_id, update_data)

def delete_idea(idea_id: int):
    service = IdeaService()
    return service.delete_idea(idea_id)

def delete_ideas(idea_ids: List[int]):
    if not idea_ids:
        return
    service = IdeaService()
    return service.bulk_delete_ideas(idea_ids)

def delete_all_ideas():
    service = IdeaService()
    return service.delete_all_ideas()