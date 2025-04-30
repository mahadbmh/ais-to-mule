from __future__ import annotations as _annotations
import os
import time
import logging
import asyncio
import chainlit as cl

from pydantic import BaseModel
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from openai.types.responses import ResponseTextDeltaEvent
from openai import AsyncAzureOpenAI

from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

from agents import (
    Agent,
    Runner,
    TResponseInputItem,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
    set_default_openai_client,
    set_default_openai_api,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

load_dotenv()
# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)
set_tracing_disabled(True)

AIPROJECT_CONNECTION_STRING = os.getenv("AIPROJECT_CONNECTION_STRING")
AZURE_OPENAI_GPT4 = os.getenv("AZURE_OPENAI_GPT4")
AZURE_OPENAI_GPT35 = os.getenv("AZURE_OPENAI_GPT35")

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
    api_key=os.getenv("MY_OPENAI_API_KEY"),
)

set_default_openai_client(azure_client, use_for_tracing=False)
set_default_openai_api("chat_completions")

project_client = AIProjectClient.from_connection_string(
    conn_str=AIPROJECT_CONNECTION_STRING, credential=DefaultAzureCredential()
)


class TelcoAgentContext(BaseModel):
    user_name: str | None = None
    image_path: str | None = None
    birth_date: str | None = None
    user_id: str | None = None


### AGENTS

creativity_agent = Agent[TelcoAgentContext](
    name="AIS CreativityAgent",
    handoff_description="An agent for generating AIS architecture for a MuleSoft integration.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}

     # Routine
    1. Receive structured integration requirements from the Requirements Agent.
    2. Generate the AIS-compatible output.
    3. Return the translated format to the user.
    4. If the request seems incomplete, transfer back to the Requirements Agent.

     🔹 Objective
Convert each MuleSoft integration flow into a modular Azure Integration Services (AIS) design by:
 
- Mapping incoming triggers and payloads
 
- Identifying transformation logic and endpoints
 
- Breaking steps into reusable Azure Functions or Logic App actions
 
- Adding observability design
 
The expected input represents the functional behavior of a MuleSoft flow. The expected output is a breakdown of the Azure architecture. Use the yaml files in Creativity Agent Input_Output Template.docx cls
as a reference for the translation.
 
🔹 Processing Rules  
1. Trigger Mapping
If incoming_payload.type is:
 
query_parameter or json_body: → use HTTP Trigger
 
mule_properties with credential flow: → use Timer Trigger or subflow call
 
Else: pick the appropriate AIS trigger (e.g., Blob, Queue)
 
2. Transformation Handling
Use an Azure Function for:
 
Field mapping
 
Conditional logic
 
Format conversion
 
If only reformatting (no logic), use Logic App mappers or Liquid templates
 
3. Destination Handling
Map destination_endpoint.type to AIS connectors:
 
Salesforce API → HTTP Action
 
OAuth → HTTP with credentials
 
Database → SQL connector or Azure Function
 
4. Function Decomposition
Any transformations.description involving condition checks, lookups, or error handling → make them separate Azure Functions
 
Name each function clearly using business context (e.g., TransformToChatterFormat, QuerySalesforceGroupId)
 
5. Observability Inclusion
Default to Application Insights and Run History
 
If sensitive, specify if monitoring or alerting should be added (e.g., email alert, Teams webhook)

Additionally, follow these guidelines:

- Commands are intended to be something that WILL be executed. Is an action. Name is always in the imperative. Ex. CreateUser or UserCreate.

- Events are a representation of something that has already happened and are always named in the past. Ex. UserCreated.

- Commands does not return values.

- Queries are intended to format the input values to retrieve data.


""",
    model=OpenAIChatCompletionsModel(
        model=AZURE_OPENAI_GPT4,
        openai_client=azure_client,
    ),
)


req_agent = Agent[TelcoAgentContext](
    name="AIS RequirementsAgent",
    handoff_description="An agent for caputring the reuqirements from a MuleSoft integration, and delegate to the creativity agent.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
   You are given MuleSoft implementation xml file(s). Given files, generate a table summary for each one using the format from Integration Summary.docx  as a reference and give the following details for each flow:

- Incoming payload
- Transformation/mappings (if any)
- Destination endpoint
- Destination payload

 # Routine
    1. If the user asks unrelated questions, transfer back to the Triage Agent.
    2. DO NOT HANDLE AIS TRANSLATION YOURSELF. ALWAYS TRANSFER TO THE CREATIVITY AGENT.
    Your only task is to generate summaries of the integrations.

 """,
    model=OpenAIChatCompletionsModel(
        model=AZURE_OPENAI_GPT4,
        openai_client=azure_client,
    ),
    handoffs=[creativity_agent],
)

triage_agent = Agent[TelcoAgentContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
        "Use the response from other agents to answer the question. Do not rely on your own knowledge."
        "Other than greetings, do not answer any questions yourself."
        "If the user requires MuleSoft requirements generated, delegate to the Requirements agent."
        "If the user requires AIS architecture generated, delegate to the Creativity agent."
    ),
    handoffs=[
        req_agent,
        creativity_agent,
    ],
    model=OpenAIChatCompletionsModel(
        model=AZURE_OPENAI_GPT35,
        openai_client=azure_client,
    ),
)


async def retrieve_documents(query: str, top_k: int = 5) -> list[str]:
    results = []
    search_results = await search_client.search(search_text=query, top=top_k)
    async for result in search_results:
        content = result.get("content") or result.get("text") or str(result)
        results.append(content)
    return results


async def main(user_input: str) -> None:
    current_agent = cl.user_session.get("current_agent")
    input_items = cl.user_session.get("input_items")
    context = cl.user_session.get("context")
    print(f"Received message: {user_input}")

    # Show thinking message to user
    msg = await cl.Message(f"thinking...", author="agent").send()
    msg_final = cl.Message("", author="agent")

    # Set an empty list for delete_threads in the user session
    cl.user_session.set("delete_threads", [])
    is_thinking = True

    retrieved_docs = await retrieve_documents(user_input)
    print("Retrieved documents for grounding:")
    for i, doc in enumerate(retrieved_docs):
        print(f"Doc {i + 1}: {doc[:200]}...")  # Log usage of documents

    # Combine retrieved content with user input for context
    context_text = "\n\n".join(
        f"[Doc {i + 1}]: {doc}" for i, doc in enumerate(retrieved_docs)
    )
    augmented_input = f"{context_text}\n\nUser Query: {user_input}"

    input_items.append({"content": augmented_input, "role": "user"})

    try:
        input_items.append({"content": user_input, "role": "user"})
        # Run the agent with streaming
        result = Runner.run_streamed(current_agent, input_items, context=context)
        last_agent = ""

        # Stream the response
        async for event in result.stream_events():
            # Get the last agent name
            if event.type == "agent_updated_stream_event":
                if is_thinking:
                    last_agent = event.new_agent.name
                    msg.content = f"[{last_agent}] thinking..."
                    await msg.send()
            # Get the message delta chunk
            elif event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                if is_thinking:
                    is_thinking = False
                    await msg.remove()
                    msg_final.content = f"[{last_agent}] "
                    await msg_final.send()

                await msg_final.stream_token(event.data.delta)

        # Update the current agent and input items in the user session
        cl.user_session.set("current_agent", result.last_agent)
        cl.user_session.set("input_items", result.to_input_list())

    except Exception as e:
        logger.error(f"Error: {e}")
        msg_final.content = "I'm sorry, I encountered an error while processing your request. Please try again."

    # show the last response in the UI
    await msg_final.update()

    # Delete threads after processing
    delete_threads = cl.user_session.get("delete_threads") or []
    for thread_id in delete_threads:
        try:
            project_client.agents.delete_thread(thread_id)
            print(f"Deleted thread: {thread_id}")
        except Exception as e:
            print(f"Error deleting thread {thread_id}: {e}")

    # Create new thread for the next message
    new_threads = cl.user_session.get("new_threads") or {}

    for key in new_threads:
        if new_threads[key] in delete_threads:
            thread = project_client.agents.create_thread()
            new_threads[key] = thread.id
            print(f"Created new thread: {thread.id}")

    # Update new threads in the user session
    cl.user_session.set("new_threads", new_threads)


# Chainlit setup
@cl.on_chat_start
async def on_chat_start():
    # Initialize user session
    current_agent: Agent[TelcoAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []

    cl.user_session.set("current_agent", current_agent)
    cl.user_session.set("input_items", input_items)
    cl.user_session.set("context", TelcoAgentContext())

    # Create a thread for the agent
    thread = project_client.agents.create_thread()
    cl.user_session.set(
        "new_threads",
        {
            FAQ_AGENT_ID: thread.id,
        },
    )


@cl.on_message
async def on_message(message: cl.Message):
    cl.user_session.set("start_time", time.time())
    user_input = message.content

    for element in message.elements:
        # check if the element is an image
        if element.mime.startswith("image/"):
            user_input += f"\n[uploaded image] {element.path}"
            print(f"Received file: {element.path}")

    asyncio.run(main(user_input))


if __name__ == "__main__":
    # Chainlit will automatically run the application
    pass
