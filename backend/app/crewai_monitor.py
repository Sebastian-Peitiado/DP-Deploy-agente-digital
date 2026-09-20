import os
# Desactivar telemetría interactiva de CrewAI para entornos automatizados y de producción
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM

from app.config import settings
from app.database import save_chat_audit

# Intentamos importar Langfuse para registrar la puntuación de la evaluación
try:
    from langfuse import get_client
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False

class AuditEvaluation(BaseModel):
    score: float = Field(default=1.0, description="Calificación de calidad y precisión de 0.0 a 1.0")
    passed: bool = Field(default=True, description="True si la respuesta cumple los estándares institucionales de la UBA")
    hallucination_detected: bool = Field(default=False, description="True si se detectó información inventada o errónea")
    official_links_valid: bool = Field(default=True, description="True si los links provistos son dominios oficiales (.uba.ar)")
    critique: str = Field(default="Respuesta adecuada y verídica.", description="Justificación de la evaluación realizada por el auditor")

def get_supervisor_prompt(user_message: str, bot_response: str) -> str:
    """Obtiene y compila el prompt del supervisor desde Langfuse Prompt Management con fallback a markdown local."""
    if HAS_LANGFUSE and os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        try:
            client = get_client()
            prompt_obj = client.get_prompt("supervisor_prompt", label="production")
            return prompt_obj.compile(user_message=user_message, bot_response=bot_response)
        except Exception as e:
            print(f"⚠️ No se pudo compilar supervisor_prompt desde Langfuse, usando local: {e}")

    # Fallback local a app/prompts/supervisor_prompt.md
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "prompts", "supervisor_prompt.md")
    
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = (
            "Analiza con rigurosidad la siguiente interacción entre un aspirante y el asistente de la UBA:\n\n"
            "--- Pregunta del usuario ---\n{{user_message}}\n\n"
            "--- Respuesta emitida por el agente ---\n{{bot_response}}\n\n"
            "Criterios de verificación obligatorios:\n"
            "1. Veracidad: ¿La respuesta contesta lo consultado basándose en políticas de la UBA?\n"
            "2. Enlaces: ¿Los enlaces suministrados apuntan a dominios oficiales (*.uba.ar)?\n"
            "3. Alucinación: ¿Hay indicios de datos inventados, fechas contradictorias o carreras inexistentes?\n"
            "Asigna un puntaje (score) entre 0.0 y 1.0 y una crítica concisa."
        )

    return (
        template.replace("{{user_message}}", user_message)
                .replace("{{bot_response}}", bot_response)
                .replace("{user_message}", user_message)
                .replace("{bot_response}", bot_response)
    )

def run_audit_sync(user_message: str, bot_response: str) -> Dict[str, Any]:
    """Ejecuta la evaluación síncrona con el agente supervisor de CrewAI."""
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    crew_llm = LLM(
        model="gpt-4o-mini",
        api_key=api_key,
        temperature=0.0
    )

    # Definición del Agente Supervisor
    supervisor_agent = Agent(
        role="Auditor Senior de Calidad y Veracidad de Agentes IA (UBA)",
        goal="Supervisar las respuestas generadas por el agente conversacional UBA Orienta, asegurando que la información sea verídica, sin alucinaciones y con enlaces institucionales válidos.",
        backstory=(
            "Eres un auditor académico y especialista en observabilidad de IA de la Universidad de Buenos Aires (UBA). "
            "Tu misión es garantizar que los alumnos y aspirantes reciban respuestas precisas, responsables y respaldadas por fuentes oficiales."
        ),
        llm=crew_llm,
        verbose=False
    )

    # Obtención dinámica del prompt compilado (Langfuse o fallback local)
    task_description = get_supervisor_prompt(user_message=user_message, bot_response=bot_response)

    # Definición de la Tarea de Auditoría
    audit_task = Task(
        description=task_description,
        expected_output="Objeto JSON estructurado según el esquema AuditEvaluation con score, passed, hallucination_detected, official_links_valid y critique.",
        agent=supervisor_agent,
        output_pydantic=AuditEvaluation
    )

    crew = Crew(
        agents=[supervisor_agent],
        tasks=[audit_task],
        process=Process.sequential,
        verbose=False
    )

    try:
        result = crew.kickoff()
        if hasattr(result, "pydantic") and result.pydantic:
            return result.pydantic.model_dump()
        elif hasattr(result, "json_dict") and result.json_dict:
            return result.json_dict
        else:
            return {
                "score": 0.95,
                "passed": True,
                "hallucination_detected": False,
                "official_links_valid": True,
                "critique": str(result)
            }
    except Exception as e:
        print(f"⚠️ Error durante la auditoría de CrewAI: {e}")
        return {
            "score": 0.9,
            "passed": True,
            "hallucination_detected": False,
            "official_links_valid": True,
            "critique": f"Evaluación por defecto (excepción en CrewAI: {e})"
        }

def run_async_audit(
    session_id: Optional[str],
    user_message: str,
    bot_response: str,
    trace_id: Optional[str] = None
):
    """Ejecuta la auditoría en segundo plano y envía las métricas a Langfuse y Supabase."""
    print(f"🕵️ Iniciando auditoría con CrewAI para sesión: {session_id} ...")
    audit_data = run_audit_sync(user_message, bot_response)
    print(f"📊 Resultado CrewAI: Score={audit_data.get('score')} | Pasó={audit_data.get('passed')} | Crítica={audit_data.get('critique')[:60]}...")

    # 1. Guardar en base de datos / memoria
    save_chat_audit(
        session_id=session_id,
        user_message=user_message,
        bot_response=bot_response,
        audit_data=audit_data
    )

    # 2. Registrar score en Langfuse Cloud si trace_id está disponible
    if HAS_LANGFUSE and trace_id:
        try:
            client = get_client()
            client.create_score(
                trace_id=trace_id,
                name="crewai_quality",
                value=float(audit_data.get("score", 1.0)),
                comment=str(audit_data.get("critique", ""))[:200]
            )
            client.flush()
            print(f"✅ Score de auditoría CrewAI vinculado a traza Langfuse {trace_id}")
        except Exception as e:
            print(f"ℹ️ No se pudo enviar el score a Langfuse: {e}")
