# Proyecto Drupal + IA (Unified Stack Manager)

**Estado:** En desarrollo (Drupal 11 + Módulos de IA).

Unified Stack Manager (USM) es una herramienta versátil de línea de comandos diseñada para simplificar la configuración y gestión de entornos de desarrollo local para Drupal, con un enfoque especial en la integración de Inteligencia Artificial.

---

## 📋 Requisitos
- **Sistema Operativo:** Windows 10/11 (vía MobaXterm) o Linux (Debian/Ubuntu).
- **Stack:** PHP 8.4, Apache 2.4, MySQL/MariaDB.
- **Python:** 3.8 o superior.
- **Permisos:** Acceso de Administrador / sudo.

---

## 🚀 Instalación y Despliegue

### 1. Clonar el repositorio
```bash
git clone https://github.com/axlfc/usm.git unified-stack-manager
cd unified-stack-manager
```

### 2. Instalar el paquete en modo editable
```bash
pip install -e .
```

### 3. Crear un sitio con automatización de IA
```bash
usm create-site mi-sitio-ia.local --ai
```
Este comando instala Drupal 11, activa todos los módulos de IA necesarios y crea un blog de ejemplo con contenido inicial.

---

## 🔧 Configuración de IA

Para habilitar las funciones de IA, sigue estos pasos:
1. Copia el archivo `.env.example` de la raíz del proyecto al directorio de tu sitio como `.env`.
2. Añade tus API Keys (OpenAI, Anthropic, etc.).
3. Valida tu entorno con el comando de verificación:
```bash
usm verify-ai --site mi-sitio-ia.local
```

Para una guía paso a paso detallada en Windows, consulta: [GUIA_DETALLADA_WINDOWS.md](./GUIA_DETALLADA_WINDOWS.md)

---

## 🤖 Módulos de IA Activados

| Módulo | Descripción |
| :--- | :--- |
| `ai` | Core del ecosistema de IA en Drupal. |
| `ai_agents` | Framework para agentes autónomos. |
| `ai_automators` | Automatización de tareas basada en IA. |
| `ai_content_suggestions` | Genera títulos, resúmenes y sugerencias de contenido. |
| `ai_translate` | Traducción automática de entidades y campos. |
| `ai_media_image` | Generación de imágenes mediante IA. |
| `ai_chatbot` | Interfaz de chat integrada. |
| `ai_provider_openai` | Soporte para OpenAI (GPT-4o/o1). |
| `ai_provider_ollama` | Soporte para LLMs locales (Llama 3, etc.). |
| `mcp` | Model Context Protocol para herramientas externas. |
| `langfuse` | Observabilidad y trazabilidad de prompts. |

---

## 🛠️ Comandos Principales

- `usm create-site [SITE_NAME] --ai`: Despliegue completo con IA.
- `usm verify-ai --site [SITE_NAME]`: Diagnóstico técnico del entorno de IA.
- `usm status`: Muestra el estado de los servicios (Apache, MySQL, PHP).
- `usm switch-php [SITE_NAME] [VERSION]`: Cambia la versión de PHP del sitio.

---

## ❓ Solución de Problemas

- **Error: "API key no válida"**: Verifica tu archivo `.env` y asegúrate de que no haya espacios extra.
- **Error: "Ollama no responde"**: Asegúrate de que Ollama esté ejecutándose en `http://localhost:11434`.
- **Módulo no encontrado**: Ejecuta `composer require drupal/[modulo]` en la carpeta del sitio.

---

## 📝 Documentación Adicional
- [Guía Detallada para Windows](./GUIA_DETALLADA_WINDOWS.md)
- [Registro de Auditoría](./logs/audit.log) (si está habilitado)
