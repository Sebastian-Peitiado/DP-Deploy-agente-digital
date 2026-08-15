import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.agent import run_agent_query

app = FastAPI(
    title="UBA FAQ & Links AI Agent API",
    description="API para el Agente IA de Preguntas Frecuentes y Enlaces Oficiales de la UBA",
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str = Field(..., description="Rol del emisor: 'user' o 'assistant'")
    content: str = Field(..., description="Contenido del mensaje")

class ChatRequest(BaseModel):
    message: str = Field(..., description="Pregunta del usuario")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Historial previo de la conversación")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Respuesta generada por el agente con enlaces oficiales")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "UBA FAQ Agent Backend",
        "database": "Supabase pgvector"
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        history_dicts = [msg.model_dump() for msg in request.history] if request.history else []
        reply = run_agent_query(user_input=request.message, history=history_dicts)
        return ChatResponse(response=reply)
    except Exception as e:
        print(f"❌ Error procesando consulta: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ocurrió un error al procesar tu consulta: {str(e)}"
        )

# Servir archivos estáticos del frontend si se ejecuta el backend de forma local/monolítica
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def read_root():
        return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
