from models.topics import TopicCreateInput, TopicUpdateInput
from services.topics_service import TopicsService
from services.ideas_service import IdeaService
from typing import List
from utils.openAi import openai_client
import os


def get_all_topics():
    topic_service = TopicsService()
    return topic_service.get_all_topics()

def create_topic(topic: TopicCreateInput):
    if topic.summary != "":
        embeddings = openai_client.get_embeddings(topic.summary)
        insert_data = topic.model_dump(exclude_unset=True)
        insert_data['embeddings'] = embeddings[0].embedding
        
        idea_ids = insert_data.pop('idea_ids', [])
        
        topic_service = TopicsService()
        idea_service = IdeaService()
        
        new_topic_id = topic_service.create_topic(insert_data)
        
        if new_topic_id and idea_ids:
            idea_service.remove_idea_topic_relation(topic_id=new_topic_id)
            for idea_id in idea_ids:
                idea_service.add_idea_topic_relation(idea_id=idea_id, topic_id=new_topic_id)
        return {'status': 200, 'message': f'Added topic ID - {new_topic_id} successfully'}
    return {'status': 200, 'message': 'No text to add'}

def create_topics(topics: List[TopicCreateInput]):
    if not topics:
        return
    texts_to_embed = []
    topic_indices_to_embed = []

    # Collect idea_ids per topic (by index), since new topics have no id yet
    idea_ids_per_index = []
    data_list = []
    for i, topic in enumerate(topics):
        if topic.summary and topic.summary != "":
            texts_to_embed.append(topic.summary)
            topic_indices_to_embed.append(i)

        topic_data = topic.model_dump(exclude_unset=True)
        idea_ids_per_index.append(topic_data.pop('idea_ids', []))
        data_list.append(topic_data)

    if texts_to_embed:
        embeddings_data = openai_client.get_embeddings(texts_to_embed)
        for idx, embedding_obj in zip(topic_indices_to_embed, embeddings_data):
            data_list[idx]["summary_embedding"] = embedding_obj.embedding

    topic_service = TopicsService()
    idea_service = IdeaService()
    new_topic_ids = topic_service.bulk_create_topics(data_list)

    # Use the returned IDs to update the idea_topic relation table
    if new_topic_ids:
        for topic_id, idea_ids in zip(new_topic_ids, idea_ids_per_index):
            if not idea_ids:
                continue
            idea_service.remove_idea_topic_relation(topic_id=topic_id)
            for idea_id in idea_ids:
                idea_service.add_idea_topic_relation(idea_id=idea_id, topic_id=topic_id)

    return {'status': 200, 'message': 'Created topics successfully'}

def update_topic(topic: TopicUpdateInput, append_idea_ids: bool = False):
    topic_service = TopicsService()
    idea_service = IdeaService()
    update_data = topic.model_dump(exclude_unset=True)
    idea_ids = update_data.pop('idea_ids', [])
    topic_service.update_topic(update_data)
    if not append_idea_ids:
        idea_service.remove_idea_topic_relation(update_data["id"])
    for idea_id in idea_ids:
        idea_service.add_idea_topic_relation(idea_id=idea_id, topic_id=update_data["id"])
    return {'status': 200, 'message': 'Updated topic successfully'}

def update_topics(topics: List[TopicUpdateInput], append_idea_ids: bool = False):
    topic_service = TopicsService()
    idea_service = IdeaService()
    topics_to_add = []
    for topic in topics:
        update_data = topic.model_dump(exclude_unset=True)
        idea_ids = update_data.pop('idea_ids', [])
        topics_to_add.append(update_data)
        if not append_idea_ids:
            idea_service.remove_idea_topic_relation(update_data["id"])
        for idea_id in idea_ids:
            idea_service.add_idea_topic_relation(idea_id=idea_id, topic_id=update_data["id"])
    topic_service.bulk_update_topics(topics_to_add)
    return {'status': 200, 'message': 'Updated topics successfully'}

def update_topic_recency():
    topic_service = TopicsService()
    topic_service.refresh_topic_recency()
    return {'status': 200, 'message': 'Updated topic recency successfully'}

def get_high_signal_topics():
    dominance_threshold = os.getenv("DOMINANCE_THRESHOLD")
    recency_threshold = os.getenv("RECENCY_THRESHOLD")
    topic_service = TopicsService()
    return topic_service._get_high_signal_topics(recency_threshold, dominance_threshold)       

