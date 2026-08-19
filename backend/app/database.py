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
