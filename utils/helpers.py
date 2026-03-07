from typing import Tuple
import os
import yaml
from models.output_schemas import ClassificationResultList, PersonalState, TopicsList
from utils.openAi import openai_client
import json
from collections import defaultdict
from models.topics import TopicCreateInput, TopicUpdateInput
from services.ideas_service import IdeaService
from utils.topic_manager import get_all_topics, update_topics, create_topics
from collections import defaultdict

def classify_ideas(user_input_text: list[Tuple[str, str]]):
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    personal_state_path = os.path.join(ROOT_DIR, "config", "memory", "personal_state.json")

    if os.path.exists(personal_state_path):
        with open(personal_state_path, "r") as f:
            personal_state_data = f.read().strip()
        
        if not personal_state_data:
            personal_state_data = "{}"
    else:
        personal_state_data = "{}"

    idea_filter_prompt_path = os.path.join(ROOT_DIR, "config", "prompts", "ideaFiltering.yaml")
    with open(idea_filter_prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_msg = template["system"].format(personal_state=personal_state_data)
    user_msg = template["user"].format(user_input=user_input_text)

    completion = openai_client.get_chat_completion(system_prompt=system_msg, user_prompt=user_msg, response_format=ClassificationResultList)

    return completion

def update_personal_state(user_input_text: list[str]):
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    personal_state_path = os.path.join(ROOT_DIR, "config", "memory", "personal_state.json")

    if os.path.exists(personal_state_path):
        with open(personal_state_path, "r") as f:
            personal_state_data = f.read().strip()
        
        if not personal_state_data:
            personal_state_data = "{}"
    else:
        personal_state_data = "{}"

    personal_info_updater_prompt_path = os.path.join(ROOT_DIR, "config", "prompts", "personal_info_updater.yaml")
    with open(personal_info_updater_prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_msg = template["system"].format(personal_state=personal_state_data)
    user_msg = template["user"].format(user_input=user_input_text)

    completion = openai_client.get_chat_completion(system_prompt=system_msg, user_prompt=user_msg, response_format=PersonalState)


    data_store = defaultdict(list)
    for item in completion.personal_info:
        data_store[item.key].append(item.value)
    
    final_dict = {k: (v[0] if len(v) == 1 else v) for k, v in data_store.items()}

    with open(personal_state_path, "w") as f:
        json.dump(final_dict, f, indent=2)

# assign input parameters type
def organize_ideas_into_topics(ideas: any, existing_topics: any) -> TopicsList:
    """
    Organizes ideas into topics using LLM.
    
    Args:
        ideas: List of Idea objects to organize
        existing_topics: List of existing Topic objects to potentially add ideas to
        
    Returns:
        TopicOrganization with organized topics and unassigned ideas
    """
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load the prompt
    prompt_path = os.path.join(ROOT_DIR, "config", "prompts", "topic_organization.yaml")
    with open(prompt_path, "r") as f:
        template = yaml.safe_load(f)
    
    # Prepare ideas data for LLM
    ideas_data = []
    for idea in ideas:
        ideas_data.append({
            "id": idea['id'],
            "content": idea['content'],
        })
    
    existing_topics_data = []
    for topic in existing_topics:
        existing_topics_data.append({
            "id": topic["id"],
            "title": topic["title"],
            "summary": topic["summary"],
        })
    
    # Prepare existing topics data for LLM
    # existing_topics_data = []
    # for topic in existing_topics:
    #     existing_topics_data.append({
    #         "id": topic.id,
    #         "title": topic.title,
    #         "summary": topic.summary,
    #         "idea_ids": topic.idea_ids
    #     })
    
    # Format prompts
    system_prompt = template["system_prompt"]
    
    user_prompt = template["user_prompt_template"].format(
        existing_topics=json.dumps(existing_topics_data, indent=2),
        ideas=json.dumps(ideas_data, indent=2)
    )
    
    # Get LLM completion
    completion = openai_client.get_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=TopicsList
    )
    return completion

def assign_idea_to_topic():
    '''Assign unassigned ideas to existing topics using a threshold and create a new topic if needed'''
    threshold = float(os.getenv("TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY", 0.9))
    threshold = 1-threshold
    idea_service = IdeaService()
    assigned_ideas = idea_service.assign_idea_to_topic(threshold)
    unassigned_ideas = idea_service.get_unassigned_ideas()
    existing_topics = get_all_topics()
    if len(unassigned_ideas) == 0:
        return {'status': 200, 'message': 'Assigned ideas successfully'}
    ideas = organize_ideas_into_topics(unassigned_ideas, existing_topics)
    new_topics, existing_topics = [], []
    for topic in ideas.topics:
        if topic.is_new:
            new_topics.append(TopicCreateInput.model_validate(topic.model_dump(exclude={"is_new", "id"})))
        else:
            existing_topics.append(TopicUpdateInput.model_validate(topic.model_dump(exclude={"is_new"})))
    if len(existing_topics) > 0:
        update_topics(existing_topics, append_idea_ids=True)
    if len(new_topics) > 0:
        create_topics(new_topics)
    return {'status': 200, 'message': 'Assigned ideas successfully'}

def semantic_search_memories(query: str, n_topics: int = 5, k_ideas: int = 3):
    idea_service = IdeaService()
    query_embedding = openai_client.get_embeddings(query)[0].embedding
    topic_similarity_threshold = float(os.getenv("TOPIC_SIMILARITY_THRESHOLD", 0.7))
    idea_similarity_threshold = float(os.getenv("IDEA_SIMILARITY_THRESHOLD", 0.8))
    rows = idea_service.search_topics_and_ideas(query_embedding, n_topics, k_ideas, topic_similarity_threshold, idea_similarity_threshold)
    topics = defaultdict(lambda: {"title": "", "summary": "", "ideas": []})
    # for topic_id, title, summary, idea_id, content, dist in rows:
    #     topics[topic_id]["title"] = title
    #     topics[topic_id]["summary"] = summary
    #     topics[topic_id]["ideas"].append({
    #         "id": idea_id, 
    #         "content": content, 
    #         "distance": dist # You can optionally include the distance in your final JSON now!
    #     })

    for row in rows:
        topic_id = row['topic_id'] # Use your actual column names here
        
        topics[topic_id]["title"] = row['title']
        topics[topic_id]["summary"] = row['summary']
        topics[topic_id]["similarity"] = row['topic_similarity']
        topics[topic_id]["ideas"].append({
            "id": row['idea_id'], 
            "content": row['idea_content'], 
            "similarity": row['idea_similarity'] 
        })

    return [{"topic_id": tid, **data} for tid, data in topics.items()]
