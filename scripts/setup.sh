#!/bin/bash

# Script de configuración para TecnoJuy Backend
set -e

echo "🚀 Configurando TecnoJuy Backend..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes coloreados
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    print_error "No se encontró requirements.txt. Asegúrate de estar en el directorio backend/"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    print_info "Creando entorno virtual..."
    python3 -m venv venv
    print_status "Entorno virtual creado"
fi

# Activar entorno virtual
print_info "Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
print_info "Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Dependencias instaladas"

# Verificar archivo .env
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        print_warning "Archivo .env no encontrado. Copiando desde env.example..."
        cp env.example .env
        print_info "Archivo .env creado. Por favor, completa las variables de entorno necesarias."
    else
        print_error "No se encontró archivo env.example"
        exit 1
    fi
else
    print_status "Archivo .env encontrado"
fi

# Ejecutar script de inicialización
print_info "Inicializando proyecto..."
python init_project.py

if [ $? -eq 0 ]; then
    print_status "¡Configuración completada exitosamente!"
    echo ""
    print_info "Para ejecutar el servidor de desarrollo:"
    echo "  uvicorn app.main:app --reload"
    echo ""
    print_info "Para ver la documentación de la API:"
    echo "  http://localhost:8000/docs"
else
    print_error "Error durante la inicialización"
    exit 1
fi


