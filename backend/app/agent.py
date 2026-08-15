from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.tools import create_retriever_tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.config import settings
from app.database import get_vector_store

def get_agent_executor() -> AgentExecutor:
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

    system_prompt = """Eres el asistente virtual oficial de FAQs y Trámites de la Universidad de Buenos Aires (UBA).
Tu función principal es responder preguntas frecuentes sobre el CBC, facultades, trámites, inscripciones y legalizaciones de la UBA.

REGLAS ESTRICTAS QUE DEBES SEGUIR:
1. Para responder a cualquier consulta sobre la UBA, utiliza SIEMPRE la herramienta `search_uba_knowledge` para recuperar la información veridica y actualizada.
2. Cada vez que respondas sobre un trámite, facultad o inscripción, DEBES INCLUIR SIEMPRE el enlace web oficial en formato Markdown cliqueable: [Nombre de la Plataforma o Trámite](https://url-oficial.uba.ar).
3. Responde de forma cordial, concisa y estructurada usando viñetas o pasos si la respuesta es extensa.
4. Si el usuario te saluda o pregunta algo genérico, responde amablemente indicando en qué áreas de la UBA puedes ayudarle (CBC, legalizaciones, facultades, SIU Guaraní).
5. Si la pregunta no está relacionada con la UBA o no encuentras información relevante en la herramienta, aclara educadamente que solo respondes consultas de la UBA y comparte la web principal: [Portal Web UBA](https://www.uba.ar).
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

def run_agent_query(user_input: str, history: List[Dict[str, str]] = None) -> str:
    agent_executor = get_agent_executor()
    
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
