import os
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Sequence, Tuple, Union
from langchain_openai import ChatOpenAI
from langchain_core.tools import create_retriever_tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.database import get_vector_store

# Intentamos importar Langfuse para observabilidad
try:
    from langfuse.langchain import CallbackHandler
    from langfuse import get_client, Langfuse
    HAS_LANGFUSE = True
    
    if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        langfuse_client = get_client()
    else:
        langfuse_client = None
except ImportError:
    HAS_LANGFUSE = False
    langfuse_client = None

def load_default_system_prompt() -> str:
    """Carga el system prompt base desde Langfuse (fallback a archivo markdown)."""
    if langfuse_client:
        try:
            # Obtenemos el prompt con el nombre "uba_orienta_system_prompt"
            return langfuse_client.get_prompt("uba_orienta_system_prompt").prompt
        except Exception as e:
            print(f"No se pudo cargar system_prompt desde Langfuse, usando local: {e}")

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
    """Carga el prompt del guardarriel desde Langfuse (fallback a archivo markdown)."""
    if langfuse_client:
        try:
            return langfuse_client.get_prompt("guardrail_prompt").prompt
        except Exception as e:
            print(f"No se pudo cargar guardrail_prompt desde Langfuse, usando local: {e}")

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

    from app.llamaindex_rag import get_llamaindex_tool

    # Herramienta de RAG impulsada por LlamaIndex
    uba_retriever_tool = get_llamaindex_tool()
    tools = [uba_retriever_tool]
    # Parámetros por defecto para el LLM principal
    llm_model = "gpt-4o-mini"
    llm_temperature = 0.1

    if langfuse_client:
        try:
            # Obtenemos el config desde el prompt de Langfuse
            lf_sys = langfuse_client.get_prompt("uba_orienta_system_prompt")
            config = lf_sys.config or {}
            llm_model = config.get("model", llm_model)
            llm_temperature = config.get("temperature", llm_temperature)
        except Exception as e:
            print(f"No se pudo obtener config de Langfuse para el sistema, usando defaults: {e}")

    # LLM principal
    llm = ChatOpenAI(
        model=llm_model,
        temperature=llm_temperature,
        openai_api_key=settings.OPENAI_API_KEY
    )

    # Creamos el Agente Interno usando prebuilt react agent de LangGraph
    uba_agent = create_react_agent(llm, tools, prompt=system_prompt)

    # NODO 1: Guardarriel
    def guardrail_node(state: AgentState, config: Optional[RunnableConfig] = None):
        messages = state["messages"]
        last_message = messages[-1]
        
        guardrail_prompt = None
        guardrail_model = "gpt-4o-mini"
        guardrail_temp = 0.0
        
        if langfuse_client:
            try:
                lf_prompt = langfuse_client.get_prompt("guardrail_prompt")
                guardrail_prompt = lf_prompt.compile(message=last_message.content)
                prompt_config = lf_prompt.config or {}
                guardrail_model = prompt_config.get("model", guardrail_model)
                guardrail_temp = prompt_config.get("temperature", guardrail_temp)
            except Exception as e:
                print(f"No se pudo compilar guardrail_prompt desde Langfuse: {e}")
                
        if not guardrail_prompt:
            guardrail_template = load_guardrail_prompt()
            # En caso de que el template venga de Langfuse con {{message}}, lo reemplazamos
            guardrail_template = guardrail_template.replace("{{message}}", "{message}")
            guardrail_prompt = guardrail_template.format(message=last_message.content)
        
        guardrail_llm = ChatOpenAI(
            model=guardrail_model, 
            temperature=guardrail_temp,
            openai_api_key=settings.OPENAI_API_KEY
        )
        res = guardrail_llm.invoke(guardrail_prompt, config=config)
        
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
    def uba_node(state: AgentState, config: Optional[RunnableConfig] = None):
        # Delegamos la ejecución al agente react pasando el config (callbacks, metadata, etc.)
        response = uba_agent.invoke({"messages": state["messages"]}, config=config)
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
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    return_trace_id: bool = False
) -> Union[str, Tuple[str, Optional[str]]]:
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
    config: Dict[str, Any] = {}
    langfuse_handler = None
    trace_id = None
    if HAS_LANGFUSE and os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        # Inicializamos el Callback de Langfuse
        langfuse_handler = CallbackHandler()
        metadata: Dict[str, Any] = {}
        if session_id:
            metadata["langfuse_session_id"] = session_id
            metadata["session_id"] = session_id
        config = {
            "callbacks": [langfuse_handler],
            "metadata": metadata
        }

    # Invocamos el grafo
    result = graph.invoke({"messages": formatted_history}, config=config)

    if langfuse_handler:
        trace_id = getattr(langfuse_handler, "last_trace_id", None)

    # Vaciamos la cola para asegurar el envío inmediato a Langfuse Cloud
    if HAS_LANGFUSE:
        try:
            client = langfuse_client or get_client()
            client.flush()
        except Exception as e:
            print(f"Error al vaciar trazas de Langfuse: {e}")

    # Obtenemos la última respuesta del asistente
    final_message = result["messages"][-1]
    if return_trace_id:
        return final_message.content, trace_id
    return final_message.content
