#!/usr/bin/env bash
# ==============================================================================
# Script de Despliegue en Google Cloud Run - UBA Orienta Agent
# ==============================================================================

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SERVICE_NAME="${SERVICE_NAME:-uba-orienta-backend}"
REGION="${REGION:-us-central1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
ENV_FILE="${BACKEND_DIR}/.env"

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}   Despliegue de UBA Orienta en Google Cloud Run    ${NC}"
echo -e "${GREEN}====================================================${NC}"

# 1. Verificar instalación de gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: 'gcloud' no está instalado en el sistema.${NC}"
    echo "Instálalo desde: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 2. Verificar autenticación
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [ -z "$ACTIVE_ACCOUNT" ]; then
    echo -e "${YELLOW}⚠️ No se detectó una cuenta activa en Google Cloud.${NC}"
    echo "Iniciando autenticación interactiva con 'gcloud auth login'..."
    gcloud auth login
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
fi
echo -e "👤 Cuenta activa: ${GREEN}${ACTIVE_ACCOUNT}${NC}"

# 3. Verificar o solicitar Project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo -e "${YELLOW}⚠️ No hay un proyecto seleccionado en la configuración actual de gcloud.${NC}"
    read -p "Ingresa tu Google Cloud Project ID: " INPUT_PROJECT
    if [ -z "$INPUT_PROJECT" ]; then
        echo -e "${RED}❌ Error: Debes especificar un Project ID válido.${NC}"
        exit 1
    fi
    gcloud config set project "$INPUT_PROJECT"
    PROJECT_ID="$INPUT_PROJECT"
fi
echo -e "📦 Proyecto GCP: ${GREEN}${PROJECT_ID}${NC}"
echo -e "🌎 Región: ${GREEN}${REGION}${NC}"

# 4. Habilitar APIs necesarias en GCP
echo -e "\n${YELLOW}⚙️ Habilitando APIs requeridas (Cloud Run, Cloud Build, Artifact Registry)...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${PROJECT_ID}"

# 5. Cargar variables de entorno desde backend/.env
ENV_VARS_LIST=()
if [ -f "$ENV_FILE" ]; then
    echo -e "\n${GREEN}📄 Leyendo variables desde backend/.env...${NC}"
    while IFS= read -r line || [ -n "$line" ]; do
        # Omitir comentarios y líneas vacías
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Extraer clave y valor
        KEY=$(echo "$line" | cut -d '=' -f 1 | xargs)
        VAL=$(echo "$line" | cut -d '=' -f 2- | xargs)
        
        # Excluir PORT local
        if [ "$KEY" != "PORT" ] && [ -n "$KEY" ]; then
            ENV_VARS_LIST+=("${KEY}=${VAL}")
        fi
    done < "$ENV_FILE"
fi

# Agregar defaults para Cloud Run
ENV_VARS_LIST+=("PORT=8080")
ENV_VARS_LIST+=("CORS_ORIGINS=*")

# Construir cadena de variables de entorno para gcloud
ENV_STRING=$(IFS=, ; echo "${ENV_VARS_LIST[*]}")

# 6. Desplegar en Google Cloud Run usando Cloud Build
echo -e "\n${YELLOW}🚀 Compilando contenedor y desplegando en Cloud Run...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
    --source "${BACKEND_DIR}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 3 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars "${ENV_STRING}" \
    --project "${PROJECT_ID}"

# 7. Obtener URL del servicio y verificar salud
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format="value(status.url)" --project "${PROJECT_ID}")

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}🎉 ¡Despliegue completado con éxito!${NC}"
echo -e "URL del Servicio: ${GREEN}${SERVICE_URL}${NC}"
echo -e "Documentación API: ${GREEN}${SERVICE_URL}/docs${NC}"
echo -e "Healthcheck: ${GREEN}${SERVICE_URL}/api/health${NC}"
echo -e "${GREEN}====================================================${NC}"
