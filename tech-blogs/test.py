from __future__ import annotations
import os
import time
import chainlit as cl
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

# Azure Foundry setup
AIPROJECT_CONNECTION_STRING = os.getenv("AIPROJECT_CONNECTION_STRING")
project_client = AIProjectClient.from_connection_string(
    conn_str=AIPROJECT_CONNECTION_STRING,
    credential=DefaultAzureCredential()
)



# Agent names in Foundry 
AGENT_NAMES = ["AIS Requirements", "AIS Architect", "AIS Developer"]
AGENT_LOOKUP = {}

# Utility to retrieve agents by name
def get_agents_by_name(client, names: list[str]):
    found_agents = []
    try:
        agents = client.agents.list_agents()
        for name in names:
            match = next((a for a in agents.data if a.name == name), None)
            if match:
                found_agents.append(match)
            else:
                print(f"Agent named '{name}' not found.")
    except Exception as e:
        print(f"Error listing agents: {e}")
    return found_agents

# Routing logic: decide which agent to trigger based on user input
def detect_target_agent(message: str) -> str | None:
    message = message.lower()
    if "requirement" in message:
        return "AIS Requirements"
    elif "architecture" in message:
        return "AIS Architect"
    elif "project" in message:
        return "AIS Developer"
    return None

# Session start: load agents and create a shared thread
@cl.on_chat_start
async def setup():
    global AGENT_LOOKUP
    agents = get_agents_by_name(project_client, AGENT_NAMES)
    AGENT_LOOKUP = {a.name: a for a in agents}

    if not AGENT_LOOKUP:
        await cl.Message("No agents found. Please check your Foundry setup.").send()
        return

    thread = project_client.agents.create_thread()
    cl.user_session.set("thread", thread)

    await cl.Message("Multi-agent session started. Type a prompt to get started.").send()

# Main handler: user sends a message, we route to an agent
@cl.on_message
async def on_message(message: cl.Message):
    user_input = message.content
    thread = cl.user_session.get("thread")

    if not thread:
        await cl.Message("No active thread.").send()
        return

    # Determine which agent to use
    agent_name = detect_target_agent(user_input)
    agent = AGENT_LOOKUP.get(agent_name) if agent_name else None

    if not agent:
        await cl.Message(
            "Could not determine which agent to use. Try including keywords like "
            "`requirements`, `architecture`, or `project`."
        ).send()
        return

    # Append user's message to the thread
    try:
        project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
    except Exception as e:
        await cl.Message(f"Failed to send message to thread: {e}").send()
        return

    await cl.Message(f"`{agent.name}` is processing...").send()

    # Trigger agent run
    try:
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=agent.id
        )
        time.sleep(10)  # For now, fixed wait time (can be improved with polling)

        messages = project_client.agents.list_messages(thread_id=thread.id)
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)

        assistant_msg = next(
            (m for m in reversed(sorted_messages) if m.role == "assistant"), None
        )

        if assistant_msg:
            for item in assistant_msg.content:
                if item["type"] == "text":
                    await cl.Message(author=agent.name, content=item["text"]["value"]).send()
                    return

        await cl.Message("No reply found from the agent.").send()

    except Exception as e:
        await cl.Message(f"Error running `{agent.name}`: {e}").send()
