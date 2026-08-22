# 🏛️ Agente de FAQs y Enlaces Oficiales UBA

Sistema completo de inteligencia artificial en **Python (FastAPI + LangChain)** y **Supabase (`pgvector`)** diseñado para responder preguntas frecuentes y brindar hipervínculos oficiales a plataformas institucionales de la **Universidad de Buenos Aires (UBA)** (CBC, SIU Guaraní, TAD-UBA Legalizaciones, Facultades y Becas).

---

## 📐 Arquitectura del Sistema

- **Backend:** Python 3.11 + FastAPI + Uvicorn + LangChain Tool-Calling Agent.
- **Base de Datos & Vectors:** Supabase PostgreSQL con extensión `pgvector`.
- **Modelos IA:** OpenAI `gpt-4o-mini` (LLM) y `text-embedding-3-small` (Embeddings).
- **Carpeta de Conocimiento:** `backend/data/knowledge_base/` (contiene los archivos de FAQs y URLs).
- **Contenedor:** Dockerfile multietapa optimizado para despliegue automático en **Render**.
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

### 1. Despliegue del Backend en **Render** (render.com)
1. Sube este repositorio a **GitHub**.
2. Ingresa a [Render Dashboard](https://dashboard.render.com/) y crea un nuevo **Web Service**.
3. Conecta tu repositorio de GitHub.
4. Render detectará automáticamente el archivo `backend/Dockerfile`.
5. Define la carpeta del código fuente (*Root Directory*) en `backend`.
6. En la sección **Environment Variables**, añade:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `CORS_ORIGINS` (URL donde alojes tu Frontend)
7. Haz clic en **Create Web Service**. ¡Render compilará el contenedor Docker y te dará una URL pública HTTPS!

### 2. Despliegue del Frontend
Sube el contenido de la carpeta `frontend/` a cualquier servicio de hosting estático:
- **Vercel:** Importa la carpeta `frontend/` o tu repo.
- **Netlify:** Arrastra la carpeta `frontend/` o vincula tu repo.
- **GitHub Pages:** Habilita GitHub Pages apuntando a la carpeta `frontend/`.

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

