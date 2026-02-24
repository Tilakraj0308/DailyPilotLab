from services.ideas_service import IdeaService
from services.topics_service import TopicsService
from models.ideas import IdeaCreateInput, IdeaUpdateInput, IdeaUpdateInput, IdeaDeleteInput
# from utils.openaiEmbeddings import get_embeddings
from utils.openAi import openai_client
from typing import List
from utils.helpers import classify_idea, update_personal_state, organize_ideas_into_topics
import os

def get_ideas():
    service = IdeaService()
    all_ideas = service.get_all_ideas()
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
        
        # topic_ids = insert_data.pop('topic_ids', [])
        
        service = IdeaService()
        new_idea_id = service.create_idea(insert_data)
        
        # if new_idea_id and topic_ids:
        #     for tid in topic_ids:
        #         service.add_idea_topic_relation(new_idea_id, tid)
                
        return {'status': 200, 'message': f'Added idea ID - {new_idea_id} successfully'}
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
    service = IdeaService()
    if idea.content and idea.content != "":
        service.clear_idea_topics(idea.id)
        embeddings = openai_client.get_embeddings(idea.content)
        idea.embeddings = embeddings[0].embedding
    update_data = idea.model_dump(exclude_unset=True)
    topic_ids = update_data.pop('topic_ids', None)
    service.update_idea(update_data)
    if topic_ids is not None:
        service.clear_idea_topics(idea.id)
        for tid in topic_ids:
            service.add_idea_topic_relation(idea.id, tid)

    return {'status': 200, 'message': 'Updated idea successfully'}

def update_ideas(ideas: List[IdeaUpdateInput]):
    if not ideas:
        return
    texts_to_embed = []
    idea_indices_to_embed = []
    
    # Map to store topic updates: idea_id -> list of topic_ids
    idea_topic_updates = {}

    for i, idea in enumerate(ideas):
        if idea.content and idea.content != "":
            service.clear_idea_topics(idea_id)
            texts_to_embed.append(idea.content)
            idea_indices_to_embed.append(i)
        
        if idea.topic_ids is not None:
            idea_topic_updates[idea.id] = idea.topic_ids

    if texts_to_embed:
        embeddings_data = openai_client.get_embeddings(texts_to_embed)
        for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
            ideas[idx].embeddings = embedding_obj.embedding
            
    data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
    service = IdeaService()
    service.bulk_update_ideas(data_list)
    
    # Process topic updates
    for idea_id, topic_ids in idea_topic_updates.items():
        service.clear_idea_topics(idea_id)
        for tid in topic_ids:
            service.add_idea_topic_relation(idea_id, tid)

    return {'status': 200, 'message': 'Updated ideas successfully'}

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

def assign_idea_to_topic():
    threshold = os.getenv("TOPIC_ASSIGNMENT_THRESHOLD", 0.9)
    idea_service = IdeaService()
    topic_service = TopicsService()
    assigned_ideas = idea_service.assign_idea_to_topic(threshold)
    print("************ assigned ideas to topics ***************")
    print(assigned_ideas)
    print("*****************************************************")
    unassigned_ideas = idea_service.get_unassigned_ideas()
    print("************ unassigned ideas ***************")
    print(unassigned_ideas)
    print("*****************************************************")
    existing_topics = topic_service.get_all_topics()
    print("************ existing topics ***************")
    print(existing_topics)
    print("*****************************************************")
    ideas = organize_ideas_into_topics(unassigned_ideas, existing_topics)
    print("************ organized ideas ***************")
    print(ideas)
    print("*****************************************************")
    new_topics, existing_topics = [], []
    for topic in ideas.topics:
        if topic.is_new:
            new_topics.append(topic)
        else:
            existing_topics.append(topic)
    # Updating the existing ideas
    idea_service.bulk_update_ideas()
    # Creating the new ideas
    idea_service.create_ideas(new_topics)
    return {'status': 200, 'message': 'Assigned ideas successfully'}

