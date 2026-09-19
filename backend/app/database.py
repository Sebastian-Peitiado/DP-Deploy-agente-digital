from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from supabase.client import create_client, Client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from app.config import settings

def get_supabase_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL y SUPABASE_KEY deben estar configuradas en el entorno.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_vector_store() -> SupabaseVectorStore:
    client = get_supabase_client()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY
    )
    return SupabaseVectorStore(
        client=client,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents"
    )

def save_chat_log(user_message: str, bot_response: str, session_id: str = None):
    try:
        client = get_supabase_client()
        client.table("chat_logs").insert({
            "user_message": user_message,
            "bot_response": bot_response,
            "session_id": session_id
        }).execute()
    except Exception as e:
        print(f"⚠️ Error al guardar log de chat en Supabase: {e}")

def get_recent_chat_logs(limit: int = 50):
    try:
        client = get_supabase_client()
        res = client.table("chat_logs").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data
    except Exception as e:
        print(f"⚠️ Error al consultar logs de chat: {e}")
        return []

def get_session_history(session_id: str):
    """Obtiene el historial ordenado de mensajes para un session_id dado."""
    try:
        client = get_supabase_client()
        res = client.table("chat_logs").select("user_message, bot_response, created_at").eq("session_id", session_id).order("created_at", desc=False).execute()
        history = []
        for row in res.data:
            history.append({"role": "user", "content": row["user_message"]})
            history.append({"role": "assistant", "content": row["bot_response"]})
        return history
    except Exception as e:
        print(f"⚠️ Error al obtener historial de la sesión {session_id}: {e}")
        return []

# Buffer en memoria de respaldo para auditorías en caso de indisponibilidad temporal de BD
_memory_audits: List[Dict[str, Any]] = []

def save_chat_audit(session_id: Optional[str], user_message: str, bot_response: str, audit_data: Dict[str, Any]):
    """Guarda el resultado de la auditoría de CrewAI en Supabase (con fallback en memoria)."""
    record = {
        "session_id": session_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "score": audit_data.get("score", 1.0),
        "passed": audit_data.get("passed", True),
        "hallucination_detected": audit_data.get("hallucination_detected", False),
        "official_links_valid": audit_data.get("official_links_valid", True),
        "critique": audit_data.get("critique", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    _memory_audits.insert(0, record)
    if len(_memory_audits) > 100:
        _memory_audits.pop()

    try:
        client = get_supabase_client()
        client.table("chat_audits").insert(record).execute()
    except Exception as e:
        print(f"ℹ️ Auditoría persistida en buffer local (Supabase opcional): {e}")

def get_recent_audits(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene las auditorías recientes del supervisor desde Supabase o desde memoria."""
    try:
        client = get_supabase_client()
        res = client.table("chat_audits").select("*").order("created_at", desc=True).limit(limit).execute()
        if res.data:
            return res.data
    except Exception:
        pass
    return _memory_audits[:limit]

