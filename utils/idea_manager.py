from tracemalloc import start
from services.ideas_service import IdeaService
from models.ideas import IdeaCreateInput, IdeaUpdateInput, IdeaUpdateInput, IdeaDeleteInput
from utils.openAi import openai_client
from typing import List
from utils.helpers import classify_ideas, update_personal_state

def get_ideas():
    service = IdeaService()
    all_ideas = service.get_all_ideas()
    return all_ideas

def get_idea(idea_id: int): 
    service = IdeaService()
    return service.get_idea(idea_id)

def create_idea(idea: IdeaCreateInput):
    if idea.content != "":
        classification = classify_ideas([("1", idea.content)])
        classification = classification.classification_results[0]
        category = classification.category
        if category == 'idea':
            pass
        elif category == 'gibberish':
            return {'status': 200, 'message': 'Gibberish text'}
        elif category == 'secrets':
            return {'status': 200, 'message': 'Can\'t save sensitive data'}
        elif category == 'personal_information':
            update_personal_state([idea.content])
            return {'status': 200, 'message': 'Updated personal state successfully'}
        embeddings = openai_client.get_embeddings(idea.content)
        insert_data = idea.model_dump(exclude_unset=True)
        insert_data['embeddings'] = embeddings[0].embedding
        
        # topic_ids = insert_data.pop('topic_ids', [])
        
        service = IdeaService()
        new_idea_id = service.create_idea(insert_data)
        
        # if new_idea_id and topic_ids:
        #     for tid in topic_ids:
        #         service.add_idea_topic_relation(new_idea_id, tid)
                
        return {'status': 200, 'message': f'Added idea ID - {new_idea_id} successfully'}
    return {'status': 200, 'message': 'No text to add'}


def create_ideas(ideas_input: List[IdeaCreateInput]):
    if not ideas_input:
        return
    ideas_len_limit = 10

    if len(ideas_input) > ideas_len_limit:
        return {'status': 200, 'message': f'Too many ideas to add !! only upto {ideas_len_limit} ideas can be added at a time'}

    ideas_filtered = list(filter(lambda x: x.content!="", ideas_input))
    
    if len(ideas_filtered) == 0:
        return {'status': 200, 'message': 'No Valid text to add'}
    
    if len(ideas_filtered) == 1:
        extra_mess = 'Only one idea with content found!! \n'
        create_res = create_idea(ideas_filtered[0])
        return {'status': 200, 'message': extra_mess + create_res['message']}

    
    ideas_with_id = [(str(i), idea) for i, idea in enumerate(ideas_filtered, start=1)]
    classification_data = classify_ideas([(idea[0], idea[1].content) for idea in ideas_with_id])
    classification_data = classification_data.classification_results
    ideas, personal_info = [], []
    texts_to_embed = []
    # idea_indices_to_embed = []
    for classification in classification_data:
        # corresponding_idea = filter(lambda x: x[0] == classification.id, ideas_with_id)[1]
        corresponding_idea = next((item[1] for item in ideas_with_id if item[0] == classification.id), None)
        if classification.category == 'idea':
            if corresponding_idea:
                ideas.append(corresponding_idea.model_dump(exclude_unset=True))
                texts_to_embed.append(corresponding_idea.content)
                # idea_indices_to_embed.append(idea_count)
                # idea_count += 1
        elif classification.category == 'personal_information':
            if corresponding_idea:
                personal_info.append(corresponding_idea.content)
    
    
    if texts_to_embed:
        embeddings_data = openai_client.get_embeddings(texts_to_embed)
        for idx, embedding_obj in enumerate(embeddings_data):
            ideas[idx]["embeddings"] = embedding_obj.embedding

    if len(personal_info) > 0:
        update_personal_state(personal_info)
    if len(ideas) > 0:
        service = IdeaService()
        service.bulk_create_ideas(ideas)
    
    return {'status': 200, 'message': f'Added {len(ideas)} ideas and updated {len(personal_info)} personal information'}
    
# def create_ideas(ideas: List[IdeaCreateInput]):
#     if not ideas:
#         return
#     texts_to_embed = []
#     idea_indices_to_embed = []

#     ideas = list(filter(lambda x: x.content!="", ideas))

#     for i, idea in enumerate(ideas):
#         texts_to_embed.append(idea.content)
#         idea_indices_to_embed.append(i)

#     if texts_to_embed:
#         embeddings_data = openai_client.get_embeddings(texts_to_embed)

    
#     data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
#     for i, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
#         data_list[i]['embeddings'] = embedding_obj.embedding
#     service = IdeaService()
#     return service.bulk_create_ideas(data_list)

def update_idea(idea: IdeaUpdateInput, override_topic_ids: bool = False):
    service = IdeaService()
    if idea.content and idea.content != "":
        embeddings = openai_client.get_embeddings(idea.content)
        idea.embeddings = embeddings[0].embedding
    update_data = idea.model_dump(exclude_unset=True)
    topic_ids = update_data.pop('topic_ids', None)
    service.update_idea(update_data)
    if topic_ids is not None:
        if override_topic_ids:
            # service.clear_idea_topics(idea.id)
            service.remove_idea_topic_relation(idea_id=idea.id)
        for tid in topic_ids:
            service.add_idea_topic_relation(idea.id, tid)

    return {'status': 200, 'message': 'Updated idea successfully'}

# def update_ideas(ideas: List[IdeaUpdateInput]):
#     if not ideas:
#         return
#     texts_to_embed = []
#     idea_indices_to_embed = []
    
#     # Map to store topic updates: idea_id -> list of topic_ids
#     idea_topic_updates = {}

#     for i, idea in enumerate(ideas):
#         if idea.content and idea.content != "":
#             service.clear_idea_topics(idea_id)
#             texts_to_embed.append(idea.content)
#             idea_indices_to_embed.append(i)
        
#         if idea.topic_ids is not None:
#             idea_topic_updates[idea.id] = idea.topic_ids

#     if texts_to_embed:
#         embeddings_data = openai_client.get_embeddings(texts_to_embed)
#         for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
#             ideas[idx].embeddings = embedding_obj.embedding
            
#     data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
#     service = IdeaService()
#     service.bulk_update_ideas(data_list)
    
#     # Process topic updates
#     for idea_id, topic_ids in idea_topic_updates.items():
#         service.clear_idea_topics(idea_id)
#         for tid in topic_ids:
#             service.add_idea_topic_relation(idea_id, tid)

#     return {'status': 200, 'message': 'Updated ideas successfully'}

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