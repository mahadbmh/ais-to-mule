from __future__ import annotations as _annotations
import os
import time
import logging
import chainlit as cl

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
 
from openai import AsyncAzureOpenAI

from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

from agents import (
    set_tracing_disabled,
    set_default_openai_client,
    set_default_openai_api,
)
 

load_dotenv()
# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)
set_tracing_disabled(True)

AIPROJECT_CONNECTION_STRING = os.getenv("AIPROJECT_CONNECTION_STRING")

 
GPT4 = os.getenv("GPT4")
 
TRIAGE_AGENT_ID = os.getenv("TRIAGE_AGENT_ID")
ARCHITECT_AGENT_ID = os.getenv("ARCHITECT_AGENT_ID")
DEV_AGENT_ID = os.getenv("DEV_AGENT_ID")
REQ_AGENT_ID = os.getenv("REQ_AGENT_ID")
FAQ_AGENT_ID = os.getenv("FAQ_AGENT_ID")


AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=AzureKeyCredential(AZURE_SEARCH_KEY),
)


azure_client = AsyncAzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
)

set_default_openai_client(azure_client, use_for_tracing=False)
set_default_openai_api("chat_completions")

project_client = AIProjectClient.from_connection_string(
    conn_str=AIPROJECT_CONNECTION_STRING, credential=DefaultAzureCredential()
)


 # Step 2: Define Agent ID
agent_ids = [REQ_AGENT_ID, ARCHITECT_AGENT_ID, DEV_AGENT_ID]  # Replace with your actual agent ID
agents = []

# Step 3: Retrieve Agent
for agent_id in agent_ids:
    try:
        agent = project_client.agents.get_agent(agent_id)
        agents.append(agent)
        print(f"✅ Agent retrieved: {agent.name}")
    except Exception as e:
        print(f"❌ Error retrieving agent: {e}")

if not agents:
    print("❌ No agents retrieved. Exiting.")
    exit()

# Step 4: Create a Communication Thread
try:
    thread = project_client.agents.create_thread()
except Exception as e:
    print(f"❌ Error creating thread: {e}")
    exit()

# Step 5: Send a Message to the Thread
user_message = "Give requirements for implementation_chatter"

try:
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_message
    )
except Exception as e:
    print(f"❌ Error sending message to thread: {e}")
    exit()

# Step 6: Process Agent Runs
for agent in agents:
    try:
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=agent.id
)
        
    except Exception as e:
        print(f"❌ Error processing run for agent '{agent.name}': {e}")

# Step 7: Wait for the Agent to Process
time.sleep(10)  # Increase delay if needed

# Step 8: Retrieve and Display Messages in Correct Order
try:
    messages = project_client.agents.list_messages(thread_id=thread.id)

    if hasattr(messages, "data") and messages.data:
        # Sort messages by 'created_at' timestamp in ascending order
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)

        for msg in sorted_messages:
            if msg.content and isinstance(msg.content, list):
                for content_item in msg.content:
                    if content_item["type"] == "text":
                        print(f"🤖 {content_item['text']['value']}")
except Exception as e:
    print(f"❌ Error retrieving messages: {e}")