import os
import json
from glob import glob
from typing import List, Optional
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from langchain_core.tools import tool

from app.config import settings

# Variable global para cachear el índice
_index: Optional[VectorStoreIndex] = None

def load_kb_documents() -> List[Document]:
    """Carga los documentos de la base de conocimiento JSON en formato LlamaIndex Document."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    kb_dir = os.path.join(os.path.dirname(base_dir), "data", "knowledge_base")
    
    if not os.path.exists(kb_dir):
        kb_dir = os.path.join(base_dir, "data", "knowledge_base")

    documents: List[Document] = []
    json_files = glob(os.path.join(kb_dir, "*.json"))
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    text_content = (
                        f"Categoría: {item.get('category', 'General')}\n"
                        f"Título: {item.get('title', '')}\n"
                        f"Detalle: {item.get('content', '')}\n"
                        f"Enlace Oficial: [{item.get('url_label', 'Sitio Oficial UBA')}]({item.get('source_url', 'https://www.uba.ar')})"
                    )
                    doc = Document(
                        text=text_content,
                        metadata={
                            "category": item.get("category", "General"),
                            "title": item.get("title", ""),
                            "source_url": item.get("source_url", "https://www.uba.ar"),
                            "url_label": item.get("url_label", "Sitio Oficial UBA"),
                            "file_name": os.path.basename(file_path)
                        }
                    )
                    documents.append(doc)
        except Exception as e:
            print(f"⚠️ Error al leer {file_path} en LlamaIndex: {e}")

    return documents

def get_llamaindex_index() -> VectorStoreIndex:
    """Inicializa y cachea el VectorStoreIndex de LlamaIndex."""
    global _index
    if _index is not None:
        return _index

    # Configuración del modelo de embedding y LLM en LlamaIndex
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    Settings.embed_model = OpenAIEmbedding(
        model_name="text-embedding-3-small",
        api_key=api_key
    )
    Settings.llm = OpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=api_key
    )

    docs = load_kb_documents()
    if not docs:
        print("⚠️ No se encontraron documentos en knowledge_base, creando índice vacío.")
        docs = [Document(text="UBA - Universidad de Buenos Aires. Sitio web oficial: https://www.uba.ar")]

    print(f"📚 Indexando {len(docs)} fragmentos institucionales con LlamaIndex...")
    _index = VectorStoreIndex.from_documents(docs)
    print("✅ Índice de LlamaIndex generado exitosamente.")
    return _index

def query_uba_knowledge(query: str) -> str:
    """Ejecuta una consulta sobre la base de conocimiento utilizando el QueryEngine de LlamaIndex."""
    index = get_llamaindex_index()
    query_engine = index.as_query_engine(similarity_top_k=4)
    response = query_engine.query(query)
    return str(response)

def get_llamaindex_tool():
    """Genera la herramienta de LangChain/LangGraph conectada al Query Engine de LlamaIndex."""
    @tool("search_uba_knowledge")
    def search_uba_knowledge(query: str) -> str:
        """Útil para buscar información oficial sobre la Universidad de Buenos Aires (UBA),
        incluyendo CBC, UBA XXI, fechas de inscripción, facultades, trámites de legalización de títulos,
        acceso al SIU Guaraní y becas. Devuelve fragmentos institucionales con sus enlaces oficiales."""
        try:
            return query_uba_knowledge(query)
        except Exception as e:
            print(f"❌ Error en búsqueda con LlamaIndex: {e}")
            return f"Hubo un inconveniente al consultar la base de conocimiento: {str(e)}"

    return search_uba_knowledge
