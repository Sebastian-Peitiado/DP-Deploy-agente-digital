import os
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.tools import create_retriever_tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.database import get_vector_store

# Intentamos importar Langfuse para observabilidad
try:
    from langfuse.callback import CallbackHandler
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False

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

def load_guardrail_prompt() -> str:
    """Carga el prompt del guardarriel desde el archivo markdown."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "prompts", "guardrail_prompt.md")
    
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(os.path.dirname(base_dir), "data", "prompts", "guardrail_prompt.md")
        
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
            
    return """Evalúa si el siguiente mensaje es seguro y respetuoso. 
Si contiene groserías, odio, violencia o promueve algo ilegal, responde únicamente con la palabra BLOQUEAR. 
De lo contrario, responde PERMITIR.

Mensaje: {message}"""

# Definimos el Estado de nuestro Grafo
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def get_agent_graph(system_prompt: Optional[str] = None):
    """Crea y devuelve el grafo compilado de LangGraph."""
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

    # LLM principal
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY
    )

    # Creamos el Agente Interno usando prebuilt react agent de LangGraph
    uba_agent = create_react_agent(llm, tools, state_modifier=system_prompt)

    # NODO 1: Guardarriel
    def guardrail_node(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        
        guardrail_template = load_guardrail_prompt()
        guardrail_prompt = guardrail_template.format(message=last_message.content)
        
        # Usamos temperature 0 para que sea determinista
        guardrail_llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY
        )
        res = guardrail_llm.invoke(guardrail_prompt)
        
        if "BLOQUEAR" in res.content.upper():
            return {"messages": [AIMessage(content="Lo siento, tu consulta infringe nuestras políticas de respeto y seguridad y no puede ser procesada.")]}
        
        # Si es seguro, no agregamos mensajes nuevos, simplemente dejamos continuar el flujo
        return {"messages": []}

    # Lógica de ruteo post-guardarriel
    def route_guardrail(state: AgentState):
        last_message = state["messages"][-1]
        # Si el último mensaje es del asistente y fue un bloqueo, terminamos.
        if isinstance(last_message, AIMessage) and "infringe nuestras políticas" in last_message.content:
            return END
        return "uba_orienta"

    # NODO 2: UBA Orienta
    def uba_node(state: AgentState):
        # Delegamos la ejecución al agente react
        response = uba_agent.invoke({"messages": state["messages"]})
        # add_messages de LangGraph se encarga de deduplicar por ID de mensaje automáticamente
        return {"messages": response["messages"]}

    # Construimos el grafo (StateGraph)
    builder = StateGraph(AgentState)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("uba_orienta", uba_node)

    # Definimos el flujo
    builder.add_edge(START, "guardrail")
    builder.add_conditional_edges("guardrail", route_guardrail)
    builder.add_edge("uba_orienta", END)

    return builder.compile()

def run_agent_query(
    user_input: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None
) -> str:
    """Ejecuta una consulta contra el grafo, integrando Langfuse si está configurado."""
    graph = get_agent_graph(system_prompt=system_prompt)
    
    formatted_history = []
    if history:
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_history.append(AIMessage(content=content))

    # Agregamos la entrada actual del usuario
    formatted_history.append(HumanMessage(content=user_input))

    # Configuración de Observabilidad con Langfuse
    config = {}
    if HAS_LANGFUSE and os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        # Inicializamos el Callback de Langfuse
        langfuse_handler = CallbackHandler()
        config = {"callbacks": [langfuse_handler]}

    # Invocamos el grafo
    result = graph.invoke({"messages": formatted_history}, config=config)

    # Obtenemos la última respuesta del asistente
    final_message = result["messages"][-1]
    return final_message.content
