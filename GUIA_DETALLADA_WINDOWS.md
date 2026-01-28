# Guía Técnica: Despliegue y Uso del Proyecto Drupal + IA en Windows

**Versión:** 1.0
**Fecha:** 2025-05-22
**Autor:** Jules (software engineer)

## 1. Introducción
Esta guía detalla el proceso para desplegar un entorno de Drupal 11 optimizado para Inteligencia Artificial en Windows, utilizando **Unified Stack Manager (USM)** y **MobaXterm**.

## 2. Requisitos Previos
- **Sistema Operativo:** Windows 10/11.
- **Entorno de Terminal:** MobaXterm (recomendado) o PowerShell como Administrador.
- **Stack Tecnológico:**
  - PHP 8.4
  - Apache 2.4 (C:\APACHE24)
  - MySQL/MariaDB (C:\mysql)
  - Composer instalado globalmente o manejado por USM.

## 3. Instalación del Entorno

### Flujo de Despliegue
```mermaid
graph TD;
    A[Clonar Repositorio] --> B[Instalar USM: pip install -e .];
    B --> C[Ejecutar usm create-site --ai];
    C --> D[Descarga Drupal 11 + Módulos IA];
    D --> E[Configuración Base de Datos];
    E --> F[Activación de Módulos];
    F --> G[Creación de Blog de Ejemplo];
```

### Paso 1: Clonar e instalar USM
```bash
git clone https://github.com/axlfc/usm.git
cd unified-stack-manager
pip install -e .
```

### Paso 2: Crear el sitio con IA
Ejecuta el siguiente comando para automatizar todo el stack de Drupal + IA:
```bash
usm create-site mi-sitio-ai.local --ai
```
Este comando realizará:
- Descarga de Drupal 11.
- Instalación de módulos como `ai`, `ai_content_suggestions`, `ai_provider_openai`, etc.
- Creación de base de datos y usuario.
- Generación de un blog de prueba con 3 artículos.

## 4. Configuración de Proveedores de IA

Para que la IA funcione, debes configurar tus API Keys.

### Flujo de Configuración de IA
```mermaid
graph TD;
    A[Copiar .env.example a .env] --> B[Editar .env con API Keys];
    B --> C[Ejecutar usm verify-ai];
    C --> D{¿Todo OK?};
    D -- Sí --> E[Usar IA en Drupal];
    D -- No --> F[Revisar logs y conexión];
```

1. Localiza el archivo `.env.example` en la raíz de tu sitio (ej: `C:\APACHE24\htdocs\mi-sitio-ai.local\.env.example`).
2. Cámbiale el nombre a `.env`.
3. Introduce tus credenciales:
   ```env
   OPENAI_API_KEY="sk-..."
   ANTHROPIC_API_KEY="sk-ant-..."
   OLLAMA_BASE_URL="http://localhost:11434"
   ```

## 5. Verificación del Entorno
USM incluye una herramienta de diagnóstico para asegurar que todo esté listo:
```bash
usm verify-ai --site mi-sitio-ai.local
```

**Salida esperada:**
```text
📦 Verificando módulos de Drupal...
  ✅ Módulo 'ai'
  ✅ Módulo 'ai_content_suggestions'
  ...
📄 Validando archivo .env...
  ✅ OPENAI_API_KEY está configurado.
🌐 Probando conexiones...
  ✅ OpenAI API responde correctamente.
```

## 6. Uso de Funcionalidades de IA

### Creación de Contenido Automático
El sistema crea automáticamente 3 posts en `/node`. Puedes usar los módulos instalados para:
- **Sugerencias de contenido:** En el formulario de edición de nodos, usa las herramientas de `ai_content_suggestions`.
- **Traducción:** Usa `ai_translate` para convertir posts a otros idiomas.
- **Imágenes:** `ai_media_image` permite generar imágenes basadas en el texto del post.

### Uso de Ollama (IA Local)
Si deseas usar modelos locales:
1. Instala Ollama en Windows.
2. Ejecuta `ollama run llama3`.
3. En Drupal, configura el proveedor Ollama apuntando a `http://localhost:11434`.

## 7. Solución de Problemas

| Error | Causa Probable | Solución |
|-------|----------------|----------|
| `Drush no encontrado` | Instalación de Composer fallida | Ejecuta `composer install` en la raíz del sitio. |
| `Ollama no responde` | El servicio no está corriendo | Ejecuta `ollama serve` en una terminal. |
| `Acceso denegado DB` | Credenciales incorrectas | Revisa el archivo `web/sites/default/settings.php`. |

## 8. Conclusión
El entorno está diseñado para ser **idempotente** y **robusto**. Cualquier fallo en la conexión de IA puede ser diagnosticado rápidamente con `usm verify-ai`.
