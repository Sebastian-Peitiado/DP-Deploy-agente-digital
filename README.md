# 🏛️ Agente de FAQs y Enlaces Oficiales UBA

Sistema completo de inteligencia artificial en **Python (FastAPI + LangChain)** y **Supabase (`pgvector`)** diseñado para responder preguntas frecuentes y brindar hipervínculos oficiales a plataformas institucionales de la **Universidad de Buenos Aires (UBA)** (CBC, SIU Guaraní, TAD-UBA Legalizaciones, Facultades y Becas).

---

## 📐 Arquitectura del Sistema

- **Backend:** Python 3.11 + FastAPI + Uvicorn + LangChain Tool-Calling Agent.
- **Base de Datos & Vectors:** Supabase PostgreSQL con extensión `pgvector`.
- **Modelos IA:** OpenAI `gpt-4o-mini` (LLM) y `text-embedding-3-small` (Embeddings).
- **Carpeta de Conocimiento:** `backend/data/knowledge_base/` (contiene los archivos de FAQs y URLs).
- **Contenedor:** Dockerfile optimizado para despliegue serverless en **Google Cloud Run**.
- **Frontend:** SPA liviana en HTML5, CSS3 y JS Vanilla listos para subir a **Vercel**, **Netlify** o **GitHub Pages**.

---

## 🛠️ Configuración Inicial

### 1. Clonar el Repositorio y Configurar Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `backend/` basado en `backend/.env.example`:

```bash
cp backend/.env.example backend/.env
```

Llena las variables en `backend/.env`:
```env
OPENAI_API_KEY=sk-proj-tu-api-key-de-openai
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-o-service-role-key-de-supabase
PORT=8000
CORS_ORIGINS=*
```

### 2. Configurar la Base de Datos en Supabase
1. Ingresa a tu panel de control en [Supabase](https://supabase.com).
2. Ve a la sección **SQL Editor**.
3. Copia y ejecuta el contenido del archivo [`scripts/supabase_setup.sql`](file:///home/seba/Escritorio/Repo%20DataPath/scripts/supabase_setup.sql).
   *(Esto creará la extensión `pgvector`, la tabla `documents` y la función `match_documents`)*.

---

## 🚀 Carga de Datos (Ingesta desde Carpeta de Conocimiento)

Para cargar las FAQs y enlaces de la carpeta `backend/data/knowledge_base/` a Supabase:

1. Crea un entorno virtual e instala las dependencias en `backend/`:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # En Linux/macOS
   # venv\Scripts\activate  # En Windows
   pip install -r requirements.txt
   ```
2. Ejecuta el script de ingesta en Python:
   ```bash
   python ingest.py
   ```

---

## 🐳 Ejecución Local con Docker

Puedes probar todo el sistema localmente con un solo comando utilizando Docker Compose:

```bash
docker compose up --build
```

- **Backend FastAPI:** `http://localhost:8000` (Documentación Swagger en `http://localhost:8000/docs`).
- **Frontend Web:** `http://localhost:8080`.

---

## ☁️ Despliegue en la Nube

### 1. Despliegue del Backend en **Google Cloud Run**
El backend está preparado para desplegarse de manera serverless en Google Cloud Run utilizando contenedores:

#### Opción A: Despliegue Automatizado con Script
Ejecuta el script incluido que verifica credenciales, habilita APIs y despliega automáticamente:
```bash
./scripts/deploy_cloud_run.sh
```

#### Opción B: Despliegue Manual con gcloud CLI
1. Autentícate y selecciona tu proyecto en Google Cloud:
   ```bash
   gcloud auth login
   gcloud config set project TU_PROJECT_ID
   ```
2. Habilita los servicios necesarios:
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```
3. Despliega el backend en Cloud Run:
   ```bash
   gcloud run deploy uba-orienta-backend \
       --source ./backend \
       --platform managed \
       --region us-central1 \
       --allow-unauthenticated \
       --min-instances 0 \
       --max-instances 3 \
       --memory 512Mi \
       --set-env-vars "PORT=8080,CORS_ORIGINS=*"
   ```

### 2. Despliegue del Frontend
El frontend estático (ubicado en `backend/frontend/`) se sirve automáticamente desde la raíz del backend en Cloud Run (`/`), o bien puede desplegarse independientemente en:
- **Firebase Hosting** (Google Cloud)
- **Vercel** / **Netlify** / **GitHub Pages**

---

## 🧪 Pruebas de Funcionamiento

- **Healthcheck:** `GET /api/health` en tu servidor FastAPI.
- **Endpoint Chat:** `POST /api/chat` enviando un cuerpo JSON:
  ```json
  {
    "message": "¿Cómo me inscribo al CBC y cuál es la web?",
    "history": []
  }
  ```

---

## 💬 Gestión de Conversaciones y Soporte con Chatwoot

Para monitorear todas las conversaciones en tiempo real, auditar el desempeño de la IA y permitir la **intervención de operadores humanos (Handover)**, se integra **Chatwoot** (plataforma omnicanal Open Source).

### 🚀 Acceso y Configuración Inicial (Local)
1. **Acceder a la plataforma:**
   Ingresa desde tu navegador a: **[http://localhost:3000](http://localhost:3000)** (o `http://localhost:3000/installation/onboarding`).
2. **Onboarding Inicial (Super Admin):**
   * **Nombre de la Organización:** Ej. `UBA Digital` o `Soporte Estudiantil`.
   * **Nombre del Agente:** Tu nombre o el del operador.
   * **Email:** Puedes usar cualquier correo (incluyendo `@gmail.com`, sin restricciones corporativas).
   * **Contraseña:** Define tu clave de acceso.

### 🛠️ Comandos de Gestión (Docker Compose)
Los archivos de configuración y base de datos de Chatwoot residen en `~/chatwoot` (o `/home/seba/chatwoot`):

* **Iniciar Chatwoot:**
  ```bash
  cd ~/chatwoot && docker compose up -d
  ```
* **Ver el estado de los servicios:**
  ```bash
  cd ~/chatwoot && docker compose ps
  ```
* **Ver registros / logs en vivo:**
  ```bash
  cd ~/chatwoot && docker compose logs -f
  ```
* **Detener los servicios:**
  ```bash
  cd ~/chatwoot && docker compose stop
  ```

### ☁️ Consideración para Producción (24/7)
La instalación local permite desarrollar y probar la conexión con el bot. Para el entorno de producción final de la UBA:
* Se desplegará Chatwoot con Docker Compose en un servidor **VPS en la nube (ej. Hetzner o DigitalOcean)** para garantizar disponibilidad 24/7 y acceso a múltiples operadores simultáneos desde cualquier red.

