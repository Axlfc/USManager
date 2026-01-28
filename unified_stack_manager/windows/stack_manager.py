# unified_stack_manager/windows/stack_manager.py

import secrets
import string
import time
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

        # 4. Verificación de Agente de Prueba
        self._verify_test_agent(site_path)

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
                    "ai_provider_anthropic", "ai_provider_google",
                    "ckeditor5_markdown", "ai_agents_test"
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

    def _verify_test_agent(self, site_path: Path):
        print("\n🤖 Verificando ejecución de Agente de Prueba...")
        drush_path = site_path / "vendor" / "bin" / "drush"

        # 1. Crear el agente de prueba
        create_script = """
        $agent = \\Drupal::entityTypeManager()->getStorage('ai_agent')->load('test_agent_verify');
        if (!$agent) {
            $agent = \\Drupal::entityTypeManager()->getStorage('ai_agent')->create([
                'id' => 'test_agent_verify',
                'label' => 'Agente de Prueba para Verificación',
                'actions' => [
                    [
                        'action' => 'create_node',
                        'node_type' => 'article',
                        'title' => 'Prueba de Agente - ' . date('Y-m-d H:i:s'),
                        'body' => 'Contenido generado automáticamente para validar el agente.',
                    ],
                ],
            ]);
            $agent->save();
            echo "Agente 'test_agent_verify' creado.\\n";
        }
        """
        import subprocess
        subprocess.run([self.drupal_manager.php_exe_path, str(drush_path), "php:eval", create_script], cwd=site_path / "web", capture_output=True)

        # 2. Ejecutar el agente
        print("  - Ejecutando agente 'test_agent_verify'...")
        exec_cmd = [self.drupal_manager.php_exe_path, str(drush_path), "ai-agents:execute", "test_agent_verify"]
        result = subprocess.run(exec_cmd, cwd=site_path / "web", capture_output=True, text=True)

        if result.returncode == 0:
            # 3. Validar creación del nodo
            validate_script = """
            $query = \\Drupal::entityQuery('node')
                ->condition('type', 'article')
                ->condition('title', 'Prueba de Agente - ', 'CONTAINS')
                ->sort('created', 'DESC')
                ->range(0, 1)
                ->accessCheck(FALSE);
            $nids = $query->execute();
            if (!empty($nids)) {
                $nid = reset($nids);
                $node = \\Drupal\\node\\Entity\\Node::load($nid);
                echo "SUCCESS:" . $node->id() . ":" . $node->getTitle();
            } else {
                echo "FAILURE";
            }
            """
            val_result = subprocess.run([self.drupal_manager.php_exe_path, str(drush_path), "php:eval", validate_script], cwd=site_path / "web", capture_output=True, text=True)

            if "SUCCESS" in val_result.stdout:
                parts = val_result.stdout.strip().split(':')
                nid = parts[1]
                title = parts[2]
                print(f"  ✅ ai_agents_test: Agente 'test_agent_verify' ejecutado correctamente. Nodo '{title}' creado con ID {nid}.")
            else:
                print("  ❌ ai_agents_test: No se pudo encontrar el nodo creado por el agente.")
        else:
            print(f"  ❌ ai_agents_test: Falló la ejecución del agente. Error: {result.stderr}")

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

    def test_ai_agents(self, site_name: str, format: str = 'markdown') -> bool:
        """Ejecuta pruebas de agentes de IA y genera un reporte."""
        print(f"🧪 Ejecutando pruebas de agentes para '{site_name}'...")
        site_path = self.get_site_path(site_name)
        if not site_path.exists():
            print(f"❌ Error: El sitio '{site_name}' no existe.")
            return False

        drush_path = site_path / "vendor" / "bin" / "drush"
        import subprocess

        # Ejecutar drush ai-agents:test --all
        # Nota: El comando drush suele tener opciones para formato si el módulo lo soporta,
        # pero aquí implementamos la lógica de reporte solicitada.
        cmd = [self.drupal_manager.php_exe_path, str(drush_path), "ai-agents:test", "--all"]
        result = subprocess.run(cmd, cwd=site_path / "web", capture_output=True, text=True)

        if format == 'json':
            import json
            report = {
                "site": site_name,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            print(json.dumps(report, indent=2))
        else:
            # Markdown por defecto
            print(f"# Informe de Pruebas de Agentes de IA - {site_name}")
            print(f"**Fecha:** {time.strftime('%Y-%m-%d')}")
            print(f"**Hora:** {time.strftime('%H:%M:%S')}")
            print("\n## Resultados")
            if result.returncode == 0:
                print("✅ Todas las pruebas se ejecutaron correctamente.")
            else:
                print("❌ Se detectaron errores en las pruebas.")

            print("\n### Salida del comando:")
            print("```")
            print(result.stdout)
            if result.stderr:
                print("\n### Errores:")
                print(result.stderr)
            print("```")

        return result.returncode == 0

    def enable_markdown(self, site_name: str) -> bool:
        """Habilita el soporte de Markdown para un sitio existente en Windows."""
        print(f"🚀 Habilitando soporte de Markdown para el sitio '{site_name}' en Windows...")
        site_path = self.get_site_path(site_name)

        if not site_path.exists():
            print(f"❌ Error: El sitio '{site_name}' no existe en {site_path}")
            return False

        if self.dry_run:
            print(f"🔍 DRY RUN: Se instalaría drupal/ckeditor5_markdown y se configuraría en {site_name}")
            return True

        try:
            # 1. Composer require
            print("📦 Descargando módulo ckeditor5_markdown...")
            composer_cmd = [self.drupal_manager.php_exe_path, self.drupal_manager.composer_path, "require", "drupal/ckeditor5_markdown", "--no-interaction"]
            if not self.drupal_manager._run_command(composer_cmd, site_path):
                print("❌ Falló la descarga del módulo.")
                return False

            # 2. Drush enable
            print("🔌 Activando módulo ckeditor5_markdown...")
            drush_path = site_path / "vendor" / "bin" / "drush"
            en_cmd = [self.drupal_manager.php_exe_path, str(drush_path), "en", "ckeditor5_markdown", "-y"]
            if not self.drupal_manager._run_command(en_cmd, site_path / "web"):
                print("❌ Falló la activación del módulo.")
                return False

            # 3. Configurar
            self.drupal_manager._configure_markdown_support(site_path)

            self._log_operation('enable_markdown', site_name)
            print(f"✅ Soporte de Markdown habilitado correctamente para '{site_name}'.")
            return True

        except Exception as e:
            print(f"❌ Error al habilitar Markdown: {e}")
            return False
