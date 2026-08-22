import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import create_retriever_tool
try:
    from langchain.agents import create_tool_calling_agent, AgentExecutor
except ImportError:
    from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.config import settings
from app.database import get_vector_store

def load_default_system_prompt() -> str:
    """Carga el system prompt base desde el archivo markdown."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "prompts", "system_prompt.md")
    
    if not os.path.exists(prompt_path):
        # Fallback a directorio alternativo si existiese
        prompt_path = os.path.join(os.path.dirname(base_dir), "data", "prompts", "system_prompt.md")
    
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
            
    return "Eres UBA Orienta, un asistente servicial para responder preguntas de la Universidad de Buenos Aires."

def get_agent_executor(system_prompt: Optional[str] = None) -> AgentExecutor:
    """Crea y devuelve el ejecutor del agente con el prompt provisto o por defecto."""
    if not system_prompt:
        system_prompt = load_default_system_prompt()

    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    # Tool nativa de búsqueda en la base de conocimiento UBA
    uba_retriever_tool = create_retriever_tool(
        retriever=retriever,
        name="search_uba_knowledge",
        description=(
            "Útil para buscar información oficial sobre la Universidad de Buenos Aires (UBA), "
            "incluyendo CBC, UBA XXI, fechas de inscripción, facultades, trámites de legalización de títulos, "
            "acceso al SIU Guaraní y becas. Devuelve fragmentos con sus enlaces oficiales."
        )
    )

    tools = [uba_retriever_tool]

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

def run_agent_query(
    user_input: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None
) -> str:
    """Ejecuta una consulta contra el agente, permitiendo pasar un system prompt opcional."""
    agent_executor = get_agent_executor(system_prompt=system_prompt)
    
    formatted_history = []
    if history:
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_history.append(AIMessage(content=content))

    result = agent_executor.invoke({
        "input": user_input,
        "chat_history": formatted_history
    })

    return result.get("output", "")
