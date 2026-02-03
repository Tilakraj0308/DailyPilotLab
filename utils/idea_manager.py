from services.ideas_service import IdeaService
from models.ideas import IdeaCreateInput, IdeaUpdateInput, IdeaUpdateInput, IdeaDeleteInput
from utils.openaiEmbeddings import get_embeddings
from typing import List
import json

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
        # if type(idea.embeddings) == str:
        #     idea.embeddings = json.loads(idea.embeddings)
        # if not idea.embeddings or len(idea.embeddings) != 1536:
        embeddings = get_embeddings(idea.content)
        print("GOING TO CALL EMBEDDINGS FUNCTION")
        print("****************************")
        print(embeddings)
        print("****************************")
        # idea.embeddings = embeddings[0].embedding
        insert_data = idea.model_dump(exclude_unset=True)
        insert_data['embeddings'] = embeddings[0].embedding
        service = IdeaService()
        return service.create_idea(insert_data)
    return None

def create_ideas(ideas: List[IdeaCreateInput]):
    if not ideas:
        return
    texts_to_embed = []
    idea_indices_to_embed = []

    ideas = list(filter(lambda x: x.content!="", ideas))
    print("This is the filtered ideas")
    print(ideas)

    for i, idea in enumerate(ideas):
        # if idea.content != "":
            # if type(idea.embeddings) == str:
            #     idea.embeddings = json.loads(idea.embeddings)
            # if not idea.embeddings or len(idea.embeddings) != 1536:
                # embeddings = get_embeddings(idea.content)
                # idea.embeddings = embeddings[0].embedding
        texts_to_embed.append(idea.content)
        idea_indices_to_embed.append(i)

    if texts_to_embed:
        embeddings_data = get_embeddings(texts_to_embed)
        # for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
            # ideas[idx].embeddings = embedding_obj.embedding
    
    data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
    for i, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
        data_list[i]['embeddings'] = embedding_obj.embedding
        # if idea.content != "":
        #     idea_model = idea.model_dump(exclude_unset=True)
        #     if i in idea_indices_to_embed:
        #         idea_model['embeddings'] = embeddings_data[i].embedding
            
        #     data_list.append(ide)
    # data_list = [idea.model_dump(exclude_unset=True) for idea in ideas if idea.content != ""]
    service = IdeaService()
    return service.bulk_create_ideas(data_list)

def update_idea(idea: IdeaUpdateInput):
    if idea.content and idea.content != "":
        # if type(idea.embeddings) == str:
        #     idea.embeddings = json.loads(idea.embeddings)
        # if not idea.embeddings or len(idea.embeddings) != 1536:
        embeddings = get_embeddings(idea.content)
        print("GOING TO CALL EMBEDDINGS FUNCTION")
        print("****************************")
        print(embeddings)
        print("****************************")
        idea.embeddings = embeddings[0].embedding
    update_data = idea.model_dump(exclude_unset=True)
    # idea_id = update_data.pop('id') # Handled in service now
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
        embeddings_data = get_embeddings(texts_to_embed)
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