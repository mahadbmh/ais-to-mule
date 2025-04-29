## Building a multimodal, multi-agent system using Azure AI Agent Service and OpenAI Agent SDK with streaming response

In the rapidly evolving landscape of artificial intelligence (AI), the development of systems that can autonomously interact, learn, and make decisions has become a focal point. A pivotal aspect of this advancement is the architecture of these systems, specifically the distinction between single-agent and multi-agent frameworks.

### **Single-Agent Systems**

A single-agent system consists of one autonomous entity operating within an environment to achieve specific goals. This agent perceives its surroundings, processes information, and acts accordingly, all in isolation. For example, a standalone chatbot designed to handle customer inquiries functions as a single-agent system, managing interactions without collaborating with other agents.

### **Multi-Agent Systems**

In contrast, a multi-agent system (MAS) comprises multiple autonomous agents that interact within a shared environment. These agents can collaborate, negotiate, or even compete to achieve individual or collective objectives. For instance, in a smart manufacturing setup, various robots (agents) might work together on an assembly line, each performing distinct tasks but coordinating to optimize the overall production process.

### **Distinctions Between Single-Agent and Multi-Agent Architectures**

- **Interaction Dynamics**: Single-agent systems operate independently without the need for communication protocols. In contrast, MAS require sophisticated mechanisms for agents to interact effectively, ensuring coordination and conflict resolution.

- **Complexity and Scalability**: While single-agent systems are generally simpler to design and implement, they may struggle with complex or large-scale problems. MAS offer scalability by distributing tasks among agents, enhancing the system's ability to handle intricate challenges.

- **Robustness and Fault Tolerance**: The decentralized nature of MAS contributes to greater resilience. If one agent fails, others can adapt or take over its functions, maintaining overall system performance. Single-agent systems lack this redundancy, making them more vulnerable to failures.

### **Context of This Guide**

This guide focuses on setting up an Customer Service use case using OpenAI's Agent SDK within a multi-agent architecture. By leveraging Microsoft's Azure AI Agent Service and integrating Azure AI Search, we aim to create a system where specialized agents collaborate to provide efficient and accurate responses to user inquiries. This approach not only showcases the practical application of MAS but also highlights the benefits of combining advanced AI tools to enhance user experience.

### **Prerequisites**

Before setting up your multi-agent system, ensure you have the following:

- **Azure Subscription**: An active Azure account is essential to access Azure AI services. If you don't have one, you can create a free account.

- **Azure AI Foundry Access**: Access to Azure AI Foundry is necessary for creating AI hubs and projects.

- **Azure AI Search Resource**: Set up an Azure AI Search resource to enable the agent to retrieve relevant information efficiently.

- **Development Environment**: Set up a suitable environment for development, which includes:

  - **Azure CLI**: Install the Azure Command-Line Interface to manage Azure resources from your terminal. Ensure it's updated to the latest version.

  - **Azure AI Foundry SDK**: For creating and managing AI agents.

  - **OpenAI Agent SDK**: Install the OpenAI Agent SDK to facilitate the development of agentic applications.

  - **Code Editor**: Such as Visual Studio Code, for writing and editing your deployment scripts.

---

### **Setting Up Azure AI Agent Service**

- Follow this blog for setting up an AI Hub in Azure AI Foundry, deploying a GPT-4o model, and creating your AI agent with specific instructions and tools.
- Add Azure AI Search tool by following this guide. You should have a sample knowledge reference PDF document uploaded in the blob storage for indexing.

---

### **Setting Up Multimodal, Multi-Agent System**

This code implements a conversational AI application using Azure OpenAI and Chainlit. It defines multiple specialized agents to handle user interactions, each with distinct responsibilities:

#### **Main Components:**
**Agents:**

- **Triage Agent:** Routes user requests to the appropriate specialized agent based on the user's query.

- **FAQ Agent:** Answers frequently asked questions by using an external FAQ lookup tool.

- **Account Management Agent:** Handles user account updates, such as changing usernames, uploading ID images, and updating birth dates.

- **Live Agent:** Simulates a human customer service representative named Sarah, handling complex issues or explicit requests for human assistance.

**Tools:**

- **faq_lookup_tool:** Queries an external FAQ system to answer user questions.
- update_user_name: Updates user account information based on provided details.

- **Session Management:** Uses Chainlit's user_session to store and manage session-specific data, such as the current agent, input history, context, and thread IDs.

- **Thread Management:** Creates and deletes conversation threads using Azure AI Project Client to manage isolated conversations for each agent interaction.

- **Streaming Responses:** Streams responses from Azure OpenAI models to the user interface in real-time, providing immediate feedback ("thinking...") and incremental updates.

- **Error Handling:** Implements robust error handling to gracefully inform users of issues during processing.

- **Chainlit Integration:** Uses Chainlit decorators (@cl.on_chat_start, @cl.on_message) to handle chat initialization and incoming messages.

**Workflow:**
When a user sends a message:
- The Triage Agent initially handles the request.

- Based on the user's input, the Triage Agent delegates the request to the appropriate specialized agent (FAQ, Account Management, or Live Agent).

- The selected agent processes the request using its defined tools and instructions.

- Responses are streamed back to the user interface.

- After processing, temporary conversation threads are cleaned up, and new threads are created for subsequent interactions.

**Technologies Used:**
- **Azure OpenAI:** For generating conversational responses.

- **Azure AI Project Client:** For managing agent threads and messages.

- **Chainlit:** For building interactive conversational UI.

- **Pydantic:** For structured data modeling.

- **Asyncio:** For asynchronous operations and streaming responses.

In summary, multi-agent system provides a structured, modular conversational AI system designed to handle customer interactions efficiently, delegate tasks to specialized agents, manage user sessions, and integrate seamlessly with Azure's AI services.
