import os
import json
from glob import glob
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from supabase.client import create_client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def run_ingestion():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not supabase_url or not supabase_key or not openai_key:
        print("❌ Error: Asegúrate de tener SUPABASE_URL, SUPABASE_KEY y OPENAI_API_KEY en tu archivo .env")
        return

    print("🚀 Iniciando ingesta de archivos desde backend/data/knowledge_base/ ...")
    supabase_client = create_client(supabase_url, supabase_key)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=openai_key
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    kb_dir = os.path.join(base_dir, "data", "knowledge_base")

    docs = []

    # Process JSON files
    json_files = glob(os.path.join(kb_dir, "*.json"))
    for file_path in json_files:
        print(f"📄 Procesando archivo JSON: {os.path.basename(file_path)}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    content = (
                        f"Categoría: {item.get('category', 'General')}\n"
                        f"Título: {item.get('title', '')}\n"
                        f"Detalle: {item.get('content', '')}\n"
                        f"Enlace Oficial: [{item.get('url_label', 'Sitio Oficial UBA')}]({item.get('source_url', 'https://www.uba.ar')})"
                    )
                    metadata = {
                        "category": item.get("category", "General"),
                        "title": item.get("title", ""),
                        "source_url": item.get("source_url", "https://www.uba.ar"),
                        "url_label": item.get("url_label", "Sitio Oficial UBA")
                    }
                    docs.append(Document(page_content=content, metadata=metadata))
        except Exception as e:
            print(f"⚠️ Error al leer {file_path}: {e}")

    if not docs:
        print("⚠️ No se encontraron documentos para procesar en la carpeta knowledge_base.")
        return

    print(f"📦 Subiendo {len(docs)} fragmentos de conocimiento a Supabase (pgvector)...")
    
    SupabaseVectorStore.from_documents(
        docs,
        embeddings,
        client=supabase_client,
        table_name="documents",
        query_name="match_documents"
    )

    print("✅ ¡Ingesta completada con éxito! La base de datos de Supabase está lista.")

if __name__ == "__main__":
    run_ingestion()
