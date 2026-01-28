# unified_stack_manager/windows/stack_manager.py

import secrets
import string
from typing import List, Dict
from pathlib import Path

from unified_stack_manager.core.base_stack_manager import BaseStackManager
from unified_stack_manager.core.config import UnifiedConfig
from unified_stack_manager.core.logger import AuditLogger

# Importar componentes legacy de wamp
from unified_stack_manager.windows.legacy.core.orchestrator import Orchestrator
from unified_stack_manager.windows.legacy.drupal_manager import DrupalManager

class WindowsStackManager(BaseStackManager):
    """
    Wrapper para la implementación legacy de WAMP.
    Actúa como un adaptador entre la nueva interfaz y el código antiguo.
    """

    def __init__(self, config: UnifiedConfig, logger: AuditLogger, dry_run: bool = False):
        super().__init__(config, logger, dry_run)
        self.wamp_orchestrator = Orchestrator()
        # El DrupalManager legacy necesita saber dónde está el htdocs.
        apache_htdocs = self.config.get('apache.sites_dir', 'C:/APACHE24/htdocs')
        self.drupal_manager = DrupalManager(apache_htdocs=apache_htdocs)

    def install_components(self, components: List[str]) -> bool:
        """Instala componentes del stack WAMP."""
        print("La instalación de componentes en Windows se enfoca en PHP.")
        if self.dry_run:
            print("DRY RUN: Simularía la instalación de PHP si 'php' está en los componentes.")
            return True

        if 'php' in components or 'all' in components:
            php_version = self.config.get('php.default_version', '8.4')
            print(f"Instalando PHP v{php_version} usando el orquestador legacy...")
            return self.wamp_orchestrator.setup_php_and_apache(php_version)

        print("No se especificó 'php' o 'all', no se realiza ninguna acción de instalación.")
        return True

    def create_drupal_site(self, site_name: str, php_version: str, drupal_version: str, ai_mode: bool = False) -> bool:
        """Crea un nuevo sitio Drupal coordinando los gestores legacy."""
        print(f"Iniciando la creación del sitio Drupal '{site_name}' en Windows...")

        # Generar credenciales para la base de datos
        db_name = f"{site_name.replace('.', '_')}_db"
        db_user = f"{db_name}_user"
        alphabet = string.ascii_letters + string.digits
        db_password = ''.join(secrets.choice(alphabet) for i in range(16))

        if self.dry_run:
            print("DRY RUN: Simulación de creación de sitio Drupal.")
            print(f"  - Se crearía la base de datos '{db_name}' y el usuario '{db_user}'.")
            print(f"  - Se ejecutaría composer create-project para '{site_name}'.")
            print(f"  - Se instalaría el sitio con Drush.")
            return True

        # Paso 1: Crear la base de datos y el usuario con el gestor de MySQL legacy
        print(f"Creando base de datos '{db_name}' y usuario '{db_user}'...")
        if not self.wamp_orchestrator.mysql.create_database_and_user(db_name, db_user, db_password):
            print("Error: No se pudo crear la base de datos o el usuario.")
            return False

        # Paso 2: Modificar la configuración de Drush en el DrupalManager legacy para usar las nuevas credenciales
        db_config_string = f"mysql://{db_user}:{db_password}@localhost/{db_name}"
        self.drupal_manager._install_site = lambda project_path: self._custom_install_site(
            self.drupal_manager, project_path, db_config_string
        )

        # Paso 3: Crear el sitio Drupal usando el gestor legacy
        print("Ejecutando el proceso de creación de Drupal (Composer y Drush)...")
        if not self.drupal_manager.create_site(site_name, drupal_version, ai_mode=ai_mode):
            print("Error: El DrupalManager legacy falló al crear el sitio.")
            # TODO: Añadir lógica de rollback para la base de datos si esto falla.
            return False

        print("\n✅ Sitio Drupal creado con éxito en Windows.")
        print("\n--- Credenciales de la Base de Datos ---")
        print(f"  Database: {db_name}")
        print(f"  Username: {db_user}")
        print(f"  Password: {db_password}")
        print("----------------------------------------")
        return True

    def _custom_install_site(self, drupal_manager_instance, project_path, db_config):
        """Método helper para sobreescribir la instalación de Drush con la config correcta."""
        drush_path = project_path / "vendor" / "bin" / "drush"
        command = [
            drupal_manager_instance.php_exe_path,
            str(drush_path),
            "site:install",
            f"--db-url={db_config}",
            "--account-name=admin",
            "--account-pass=admin",
            f"--site-name={project_path.name}",
            "-y"
        ]
        return drupal_manager_instance._run_command(command, project_path / "web")


    def list_sites(self) -> List[Dict[str, str]]:
        """Lista todos los sitios existentes."""
        print("El listado de sitios no está implementado en el wrapper de Windows.")
        return []

    def switch_php_version(self, site_name: str, php_version: str) -> bool:
        """Cambia la versión de PHP de un sitio."""
        print(f"Cambiando la versión de PHP para '{site_name}' a '{php_version}'.")
        if self.dry_run:
            print(f"DRY RUN: Simularía el cambio de PHP para el sitio '{site_name}'.")
            return True

        print("Advertencia: El gestor legacy de WAMP cambia la versión de PHP globalmente.")
        return self.wamp_orchestrator.setup_php_and_apache(php_version, restart_apache=True)

    def show_status(self) -> Dict[str, any]:
        """Muestra el estado del sistema."""
        print("Mostrando estado del sistema WAMP (legacy)...")
        self.wamp_orchestrator.info()
        return {}

    def verify_ai(self, site_name: str = None) -> bool:
        """Verifica el entorno de IA y las conexiones."""
        print("🔍 Iniciando verificación técnica del entorno de IA...")

        if not site_name:
            # Si no se especifica sitio, buscar el último o listar disponibles
            print("⚠️ No se especificó sitio. Verificando configuración global...")
            return self._verify_global_ai_config()

        site_path = self.get_site_path(site_name)
        if not site_path.exists():
            print(f"❌ Error: El sitio '{site_name}' no existe en {site_path}")
            return False

        print(f"📂 Verificando sitio: {site_name}")

        # 1. Verificar módulos con Drush
        self._verify_drupal_modules(site_path)

        # 2. Validar .env
        env_vars = self._validate_env_file(site_path)

        # 3. Probar conexiones
        if env_vars:
            self._test_ai_connections(env_vars)
        else:
            print("⚠️ Saltando pruebas de conexión debido a falta de archivo .env")

        return True

    def _verify_global_ai_config(self):
        root_env_example = Path(".env.example")
        if root_env_example.exists():
            print(f"✅ .env.example global encontrado en la raíz.")
        else:
            print(f"❌ .env.example global NO encontrado en la raíz.")

        print("\nPara verificar un sitio específico usa: usm verify-ai --site nombre-del-sitio")
        return True

    def _verify_drupal_modules(self, site_path: Path):
        print("\n📦 Verificando módulos de Drupal...")
        drush_path = site_path / "vendor" / "bin" / "drush"
        if not drush_path.exists():
            print("❌ No se encontró Drush en el proyecto.")
            return

        command = [self.drupal_manager.php_exe_path, str(drush_path), "pm:list", "--status=enabled", "--format=json"]
        import subprocess
        import json
        try:
            result = subprocess.run(command, cwd=site_path / "web", capture_output=True, text=True)
            if result.returncode == 0:
                enabled_modules = json.loads(result.stdout)
                required_modules = [
                    "ai", "key", "ai_agents", "ai_simple_pdf_to_text", "tool",
                    "ai_automators", "ai_assistants_api", "ai_chatbot",
                    "ai_ckeditor", "ai_content_suggestions", "ai_translate",
                    "ai_search", "ai_logging", "ai_observability",
                    "ai_image_alt_text", "ai_media_image", "ai_seo",
                    "mcp", "model_context_protocol", "langfuse",
                    "ai_provider_openai", "ai_provider_ollama",
                    "ai_provider_anthropic", "ai_provider_google"
                ]
                for mod in required_modules:
                    status = "✅" if mod in enabled_modules else "❌"
                    print(f"  {status} Módulo '{mod}'")
            else:
                print(f"❌ Error al ejecutar Drush: {result.stderr}")
        except Exception as e:
            print(f"❌ Error verificando módulos: {e}")

    def _validate_env_file(self, site_path: Path):
        print("\n📄 Validando archivo .env...")
        env_file = site_path / ".env"
        if not env_file.exists():
            env_example = site_path / ".env.example"
            if env_example.exists():
                print(f"⚠️ .env no encontrado, pero .env.example existe. Por favor, cópialo y configúralo.")
            else:
                print(f"❌ No se encontró .env ni .env.example.")
            return None

        # Cargar variables básicas
        vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        vars[key] = val.strip('"').strip("'")

            check_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_GEMINI_API_KEY", "OLLAMA_BASE_URL"]
            for k in check_keys:
                if k in vars and vars[k] and "your_" not in vars[k]:
                    print(f"  ✅ {k} está configurado.")
                else:
                    print(f"  ⚠️ {k} no está configurado o tiene valor por defecto.")
            return vars
        except Exception as e:
            print(f"❌ Error leyendo .env: {e}")
            return None

    def _test_ai_connections(self, env_vars):
        print("\n🌐 Probando conexiones a proveedores de IA...")

        # Probar Ollama (Local)
        ollama_url = env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"  - Probando Ollama en {ollama_url}...")
        import urllib.request
        try:
            with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as response:
                if response.status == 200:
                    print("    ✅ Ollama responde correctamente.")
                else:
                    print(f"    ❌ Ollama respondió con status {response.status}.")
        except Exception as e:
            print(f"    ❌ Ollama no responde: {e}")

        # Probar OpenAI (solo si hay key)
        openai_key = env_vars.get("OPENAI_API_KEY")
        if openai_key and "your_" not in openai_key:
            print("  - Probando OpenAI API...")
            req = urllib.request.Request("https://api.openai.com/v1/models")
            req.add_header("Authorization", f"Bearer {openai_key}")
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        print("    ✅ OpenAI API responde correctamente.")
            except Exception as e:
                print(f"    ❌ OpenAI API error: {e}")

        # Probar Anthropic
        anthropic_key = env_vars.get("ANTHROPIC_API_KEY")
        if anthropic_key and "your_" not in anthropic_key:
            print("  - Probando Anthropic API...")
            try:
                print("    ✅ Anthropic Key detectada.")
            except Exception:
                pass

        # Probar Google Gemini
        google_key = env_vars.get("GOOGLE_GEMINI_API_KEY")
        if google_key and "your_" not in google_key:
            print("  - Probando Google Gemini API...")
            try:
                print("    ✅ Google Gemini Key detectada.")
            except Exception:
                pass

    def get_site_path(self, site_name: str) -> Path:
        base_path = self.config.get('apache.sites_dir', 'C:/APACHE24/htdocs')
        return Path(base_path) / site_name
