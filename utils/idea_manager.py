from services.ideas_service import IdeaService
from models.ideas import IdeaCreateInput, IdeaUpdateInput, IdeaUpdateInput, IdeaDeleteInput
# from utils.openaiEmbeddings import get_embeddings
from utils.openAi import openai_client
from typing import List
import json
from utils.helpers import classify_idea, update_personal_state

def get_ideas():
    service = IdeaService()
    print("**********************************************************")
    all_ideas = service.get_all_ideas()
    print(all_ideas)
    return all_ideas

def get_idea(idea_id: int): 
    service = IdeaService()
    return service.get_idea(idea_id)

def create_idea(idea: IdeaCreateInput):
    if idea.content != "":
        classification = classify_idea(idea.content)
        category = classification.category
        if category == 'idea':
            pass
        elif category == 'gibberish':
            return {'status': 200, 'message': 'Gibberish text'}
        elif category == 'secrets':
            return {'status': 200, 'message': 'Can\'t save sensitive data'}
        elif category == 'personal_information':
            update_personal_state(idea.content)
            return {'status': 200, 'message': 'Updated personal state successfully'}
        embeddings = openai_client.get_embeddings(idea.content)
        insert_data = idea.model_dump(exclude_unset=True)
        insert_data['embeddings'] = embeddings[0].embedding
        service = IdeaService()
        service.create_idea(insert_data)
        return {'status': 200, 'message': 'Added idea successfully'}
    return {'status': 200, 'message': 'No text to add'}

def create_ideas(ideas: List[IdeaCreateInput]):
    if not ideas:
        return
    texts_to_embed = []
    idea_indices_to_embed = []

    ideas = list(filter(lambda x: x.content!="", ideas))

    for i, idea in enumerate(ideas):
        texts_to_embed.append(idea.content)
        idea_indices_to_embed.append(i)

    if texts_to_embed:
        embeddings_data = openai_client.get_embeddings(texts_to_embed)

    
    data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
    for i, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
        data_list[i]['embeddings'] = embedding_obj.embedding
    service = IdeaService()
    return service.bulk_create_ideas(data_list)

def update_idea(idea: IdeaUpdateInput):
    if idea.content and idea.content != "":
        embeddings = openai_client.get_embeddings(idea.content)
        idea.embeddings = embeddings[0].embedding
    update_data = idea.model_dump(exclude_unset=True)
    service = IdeaService()
    return service.update_idea(update_data)

def update_ideas(ideas: List[IdeaUpdateInput]):
    if not ideas:
        return
    texts_to_embed = []
    idea_indices_to_embed = []
    for i, idea in enumerate(ideas):
        if idea.content and idea.content != "":
            texts_to_embed.append(idea.content)
            idea_indices_to_embed.append(i)
    if texts_to_embed:
        embeddings_data = openai_client.get_embeddings(texts_to_embed)
        for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
            ideas[idx].embeddings = embedding_obj.embedding
    data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
    service = IdeaService()
    return service.bulk_update_ideas(data_list)

def delete_idea(idea: IdeaDeleteInput):
    service = IdeaService()
    return service.delete_idea(idea.id)

def delete_ideas(idea_ids: List[int]):
    if not idea_ids:
        return
    service = IdeaService()
    return service.bulk_delete_ideas(idea_ids)

def delete_all_ideas():
    service = IdeaService()
    return service.delete_all_ideas()