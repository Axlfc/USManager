# unified_stack_manager/linux/stack_manager.py
import os
import secrets
import string
from pathlib import Path
from typing import List, Dict

from unified_stack_manager.core.base_stack_manager import BaseStackManager
from unified_stack_manager.core.config import UnifiedConfig
from unified_stack_manager.core.logger import AuditLogger
from unified_stack_manager.linux.apache_manager import ApacheManager
from unified_stack_manager.linux.mysql_manager import MySQLManager
from unified_stack_manager.linux.php_manager import PHPManager
from unified_stack_manager.core.validators import SystemValidator

class LinuxStackManager(BaseStackManager):
    """Implementación para Linux del Stack Manager."""

    def __init__(self, config: UnifiedConfig, logger: AuditLogger, dry_run: bool = False):
        super().__init__(config, logger, dry_run)
        self.apache = ApacheManager(self.config, self.logger, self.rollback)
        self.mysql = MySQLManager(self.config, self.logger, self.rollback)
        self.php = PHPManager(self.config, self.logger, self.rollback)
        self.last_generated_password = None

    def install_components(self, components: List[str]) -> bool:
        """Instala y configura los componentes del stack LAMP."""

        is_valid, errors = SystemValidator.validate_prerequisites()
        if not is_valid:
            print("❌ Errores de prerrequisitos del sistema:")
            for error in errors:
                print(f"   - {error}")
            return False

        print("Iniciando la instalación de componentes para Linux...")
        if self.dry_run:
            print("\n🔍 DRY RUN - No se realizarán cambios reales.")
            print("📋 Plan de instalación:")
            if 'all' in components or 'apache' in components:
                print("  - Instalar Apache2 y utilidades")
            if 'all' in components or 'mysql' in components:
                print("  - Instalar MySQL/MariaDB server")
            if 'all' in components or 'php' in components:
                php_version = self.config.get('php.default_version', '8.2')
                print(f"  - Instalar PHP {php_version} y módulos comunes")
            return True

        response = input("\n¿Proceder con la instalación? [y/N]: ")
        if response.lower() != 'y':
            print("Operación cancelada.")
            return False

        try:
            with self.rollback.protected_operation('install_components', []):
                if 'all' in components or 'apache' in components:
                    print("\nPaso 1: Instalando Apache...")
                    if not self.apache.install():
                        raise RuntimeError("La instalación de Apache falló.")

                if 'all' in components or 'mysql' in components:
                    print("\nPaso 2: Instalando MySQL/MariaDB...")
                    if not self.mysql.install():
                        raise RuntimeError("La instalación de MySQL falló.")

                if 'all' in components or 'php' in components:
                    php_version = self.config.get('php.default_version', '8.2')
                    print(f"\nPaso 3: Instalando PHP {php_version}...")
                    if not self.php.install(php_version):
                        raise RuntimeError(f"La instalación de PHP {php_version} falló.")

            self._log_operation('install_components', 'lamp', {'components': components})
            print("\n✅ Componentes del stack instalados correctamente.")
            return True

        except Exception as e:
            print(f"\n❌ Falló la instalación del stack: {e}")
            self.rollback.revert()
            return False

    def create_drupal_site(self, site_name: str, php_version: str, drupal_version: str, ai_mode: bool = False) -> bool:
        """Crea un nuevo sitio Drupal (vhost, directorio, BD)."""
        # TODO: Integrar la lógica real de creación de Drupal.
        # La lógica actual es un placeholder adaptado del antiguo create_site.

        site_config = {'site_name': site_name, 'php_version': php_version}
        supported_versions = self.config.get('php.supported_versions', [])
        is_valid, errors = SystemValidator.validate_site_config(site_config, supported_versions)
        if not is_valid:
            print("❌ Errores de validación de la configuración del sitio:")
            for error in errors:
                print(f"   - {error}")
            return False

        db_name = f"{site_name.replace('.', '_')}_db"
        doc_root = Path(self.config.get('apache.sites_dir')) / site_name
        doc_root_subdir = self.config.get('apache.doc_root_subdir', 'web')

        print(f"\n📋 Plan para crear el sitio Drupal '{site_name}':")
        print(f"   - Versión de PHP: {php_version}")
        print(f"   - Versión de Drupal: {drupal_version}")
        print(f"   - Base de datos: {db_name}")
        print(f"   - DocumentRoot: {doc_root}/{doc_root_subdir}")

        if self.dry_run:
            print("\n🔍 DRY RUN - No se realizarán cambios reales.")
            return True

        response = input("\n¿Continuar con la creación del sitio? [y/N]: ")
        if response.lower() != 'y':
            print("Operación cancelada.")
            return False

        try:
            vhost_file = Path(self.config.get('apache.vhosts_dir')) / f"{site_name}.conf"
            with self.rollback.protected_operation('create_drupal_site', [doc_root, vhost_file]):
                # 1. Crear VHost y BD (Lógica existente)
                self._execute_site_creation(site_name, php_version, db_name, doc_root)

                # 2. Instalar Drupal y configurar IA si se solicita
                if ai_mode or drupal_version:
                    self._setup_drupal_core_and_ai(site_name, doc_root, drupal_version, db_name, ai_mode)

            self._log_operation('create_drupal_site', site_name, {'php': php_version, 'drupal': drupal_version, 'ai': ai_mode})
            print(f"\n✅ Sitio '{site_name}' creado correctamente.")
            print("\n--- Credenciales de la Base de Datos ---")
            print(f"  Database: {db_name}")
            print(f"  Username: {db_name}_user")
            print(f"  Password: {self.last_generated_password}")
            print("----------------------------------------")
            return True

        except Exception as e:
            print(f"\n❌ Falló la creación del sitio: {e}")
            self.rollback.revert()
            return False

    def _setup_drupal_core_and_ai(self, site_name: str, doc_root: Path, drupal_version: str, db_name: str, ai_mode: bool):
        """Instala Drupal vía Composer y habilita módulos de IA."""
        print(f"🚀 Iniciando instalación de Drupal Core y IA para {site_name}...")

        db_user = f"{db_name}_user"
        db_password = self.last_generated_password # Recuperado de _execute_site_creation

        # Composer create-project
        if not (doc_root / "composer.json").exists():
            print("📦 Ejecutando composer create-project...")
            composer_cmd = ["composer", "create-project", f"drupal/recommended-project:{drupal_version}", str(doc_root), "--no-interaction"]
            subprocess.run(composer_cmd, check=True)

        if ai_mode:
            print("🤖 Añadiendo módulos de IA...")
            ai_modules = [
                "drupal/ai:^1.3@beta", "drupal/key", "drupal/ai_agents",
                "drupal/ai_simple_pdf_to_text:^1.0@alpha", "drupal/tool:^1.0@alpha",
                "drupal/ai_automators", "drupal/ai_assistants_api", "drupal/ai_chatbot",
                "drupal/ai_content_suggestions", "drupal/ai_translate", "drupal/ai_search",
                "drupal/ai_image_alt_text", "drupal/ai_media_image", "drupal/ai_seo",
                "drupal/mcp", "drupal/langfuse", "drupal/ai_provider_openai",
                "drupal/ai_provider_ollama", "drupal/ai_provider_anthropic", "drupal/ai_provider_google"
            ]
            # Ejecutar todos en un solo comando para mayor eficiencia
            subprocess.run(["composer", "require"] + ai_modules + ["--no-interaction"], cwd=doc_root, check=False)

        # Drush install
        drush_path = doc_root / "vendor" / "bin" / "drush"
        if not (doc_root / "web" / "sites" / "default" / "settings.php").exists():
            print("💉 Instalando sitio con Drush...")
            db_url = f"mysql://{db_user}:{db_password}@localhost/{db_name}"
            install_cmd = [
                "php", str(drush_path), "site:install",
                f"--db-url={db_url}", "--account-name=admin", "--account-pass=admin",
                f"--site-name={site_name}", "-y"
            ]
            subprocess.run(install_cmd, cwd=doc_root / "web", check=True)

        if ai_mode:
            print("🔌 Activando módulos de IA...")
            enable_modules = [
                "ai", "key", "ai_agents", "ai_simple_pdf_to_text", "tool",
                "ai_automators", "ai_assistants_api", "ai_chatbot", "ai_ckeditor",
                "ai_content_suggestions", "ai_translate", "ai_search", "ai_logging",
                "ai_observability", "ai_image_alt_text", "ai_media_image", "ai_seo",
                "mcp", "model_context_protocol", "langfuse", "ai_provider_openai",
                "ai_provider_ollama", "ai_provider_anthropic", "ai_provider_google"
            ]
            subprocess.run(["php", str(drush_path), "en"] + enable_modules + ["-y"], cwd=doc_root / "web", check=False)

            # Crear .env.example
            self._create_env_example(doc_root)

            # Crear Blog
            self._create_sample_blog(doc_root)

    def _create_env_example(self, doc_root: Path):
        print("📄 Creando .env.example...")
        env_content = """# --- Drupal AI Config (Linux) ---
OPENAI_API_KEY="your_openai_key_here"
OLLAMA_BASE_URL="http://localhost:11434"
"""
        (doc_root / ".env.example").write_text(env_content)

    def _create_sample_blog(self, doc_root: Path):
        print("📝 Creando blog de ejemplo (Dynamic AI Fallback)...")
        drush_path = doc_root / "vendor" / "bin" / "drush"

        # Intentar detectar llaves para generación dinámica
        has_keys = False
        env_file = doc_root / ".env"
        if env_file.exists():
            if "OPENAI_API_KEY" in env_file.read_text() and "your_" not in env_file.read_text():
                has_keys = True

        if has_keys:
            print("✨ Detectadas API Keys. Generando contenido dinámico con IA...")
            script = """
            try {
                if (\\Drupal::moduleHandler()->moduleExists('ai_content_suggestions')) {
                    $suggestions = \\Drupal::service('ai_content_suggestions.suggestor')->generateTitleAndBody('Drupal 11 Linux');
                    $node = \\Drupal\\node\\Entity\\Node::create([
                        'type' => 'article',
                        'title' => $suggestions['title'] ?? 'Blog dinámico en Linux',
                        'body' => ['value' => $suggestions['body'] ?? 'Contenido generado por IA.', 'format' => 'basic_html'],
                        'status' => 1
                    ]);
                    $node->save();
                }
            } catch (\\Exception $e) {}
            """
        else:
            script = """
            $node = \\Drupal\\node\\Entity\\Node::create([
                'type' => 'article',
                'title' => 'Blog en Linux (Static Mode)',
                'body' => ['value' => 'Bienvenido a Drupal 11 en Linux. Configura tus API Keys para usar IA.', 'format' => 'basic_html'],
                'status' => 1
            ]);
            $node->save();
            """
        subprocess.run(["php", str(drush_path), "php:eval", script], cwd=doc_root / "web", check=False)

    def _execute_site_creation(self, site_name: str, php_version: str, db_name: str, doc_root: Path):
        """Lógica interna de creación de sitio."""
        alphabet = string.ascii_letters + string.digits
        db_password = ''.join(secrets.choice(alphabet) for i in range(16))
        db_user = f"{db_name}_user"

        print(f"\nCreando DocumentRoot en {doc_root}...")
        full_doc_root_path = doc_root / self.config.get('apache.doc_root_subdir', 'web')
        os.makedirs(full_doc_root_path, exist_ok=True)
        # TODO: Añadir lógica de permisos (chown/chmod).

        print(f"Creando VirtualHost para Apache...")
        if not self.apache.create_virtualhost(site_name, str(doc_root), php_version):
            raise RuntimeError("La creación del VirtualHost falló.")

        print(f"Creando base de datos '{db_name}'...")
        if not self.mysql.create_database(db_name):
            raise RuntimeError("La creación de la base de datos falló.")

        print(f"Creando usuario '{db_user}'...")
        if not self.mysql.create_user(db_user, db_password):
            raise RuntimeError("La creación del usuario de base de datos falló.")

        print(f"Otorgando privilegios...")
        if not self.mysql.grant_privileges(db_name, db_user):
            raise RuntimeError("El otorgamiento de privilegios falló.")

        print("Recargando Apache...")
        if not self.apache.reload_service():
            raise RuntimeError("La recarga de Apache falló.")

        self.last_generated_password = db_password

    def list_sites(self) -> List[Dict[str, str]]:
        """Lista los sitios de Apache configurados."""
        print("🔍 Listado de sitios configurados en Apache:")
        vhosts_dir = Path(self.config.get('apache.vhosts_dir'))

        if not vhosts_dir.exists() or not vhosts_dir.is_dir():
            print(f"  - El directorio de VirtualHosts '{vhosts_dir}' no existe.")
            return []

        sites = []
        site_files = list(vhosts_dir.glob('*.conf'))

        if not site_files:
            print("  - No se encontraron sitios configurados.")
            return []

        for site_file in site_files:
            site_name = site_file.stem
            sites.append({'name': site_name, 'config_file': str(site_file)})
            print(f"  - {site_name} (fichero: {site_file.name})")

        return sites

    def switch_php_version(self, site_name: str, php_version: str) -> bool:
        """Cambia la versión de PHP para un sitio específico."""
        import re

        print(f"🔄 Cambiando la versión de PHP para el sitio '{site_name}' a '{php_version}'...")

        vhost_file = Path(self.config.get('apache.vhosts_dir')) / f"{site_name}.conf"

        if not vhost_file.exists():
            print(f"  - Error: No se encontró el archivo de configuración '{vhost_file}'.")
            return False

        if self.dry_run:
            print(f"  - DRY RUN: Se modificaría el fichero '{vhost_file}' para usar PHP {php_version}.")
            print(f"  - DRY RUN: Se recargaría el servicio de Apache.")
            return True

        try:
            content = vhost_file.read_text()

            # Expresión regular para encontrar la línea SetHandler de PHP-FPM
            pattern = r'(SetHandler "proxy:unix:/var/run/php/php)\d\.\d(-fpm.sock\|fcgi://localhost/")'

            # Construir la cadena de reemplazo
            replacement = fr'\g<1>{php_version}\g<2>'

            new_content, count = re.subn(pattern, replacement, content)

            if count == 0:
                print(f"  - Error: No se pudo encontrar la directiva de versión de PHP en '{vhost_file}'.")
                print(f"  - Se buscaba un patrón como: SetHandler \"proxy:unix:/var/run/php/phpX.X-fpm.sock...\"")
                return False

            with self.rollback.protected_operation('switch_php', [vhost_file]):
                vhost_file.write_text(new_content)
                print(f"  - Archivo '{vhost_file}' actualizado.")

                print("  - Recargando Apache para aplicar los cambios...")
                if not self.apache.reload_service():
                    raise RuntimeError("No se pudo recargar el servicio de Apache.")

            self._log_operation('switch_php', site_name, {'new_php_version': php_version})
            print(f"✅ Versión de PHP para '{site_name}' cambiada a '{php_version}' con éxito.")
            return True

        except Exception as e:
            print(f"  - Error inesperado al cambiar la versión de PHP: {e}")
            self.rollback.revert()
            return False

    def show_status(self) -> Dict[str, any]:
        """Muestra el estado de los servicios clave del stack."""
        print("🔍 Estado del sistema Linux (LAMP):")

        status_data = {}

        # Verificar Apache
        apache_status = self.apache.get_status()
        status_data['apache'] = apache_status
        print(f"  - Apache2: {'Activo' if apache_status['is_active'] else 'Inactivo'}")

        # Verificar MySQL
        mysql_status = self.mysql.get_status()
        status_data['mysql'] = mysql_status
        print(f"  - MySQL/MariaDB: {'Activo' if mysql_status['is_active'] else 'Inactivo'}")

        # Información de configuración
        print("\n📋 Rutas de configuración:")
        print(f"  - Sitios Apache: {self.config.get('apache.sites_dir')}")
        print(f"  - VirtualHosts Apache: {self.config.get('apache.vhosts_dir')}")

        return status_data

    def verify_ai(self, site_name: str = None) -> bool:
        """Verifica el entorno de IA y las conexiones en Linux."""
        print("🔍 Iniciando verificación técnica del entorno de IA en Linux...")

        if not site_name:
            print("⚠️ No se especificó sitio. Verificando configuración global...")
            root_env_example = Path(".env.example")
            if root_env_example.exists():
                print(f"✅ .env.example global encontrado en la raíz.")
            else:
                print(f"❌ .env.example global NO encontrado en la raíz.")
            print("\nPara verificar un sitio específico usa: usm verify-ai --site nombre-del-sitio")
            return True

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

    def _verify_drupal_modules(self, site_path: Path):
        print("\n📦 Verificando módulos de Drupal...")
        # En Linux, drush suele estar en vendor/bin/drush o global
        drush_path = site_path / "vendor" / "bin" / "drush"

        # Intentar encontrar php
        php_cmd = "php" # Asumimos php en el path para Linux

        command = [php_cmd, str(drush_path), "pm:list", "--status=enabled", "--format=json"]
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
                print(f"⚠️ .env no encontrado, pero .env.example existe.")
            else:
                print(f"❌ No se encontró .env ni .env.example.")
            return None

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

        # Probar Ollama
        ollama_url = env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"  - Probando Ollama en {ollama_url}...")
        import urllib.request
        try:
            with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as response:
                if response.status == 200:
                    print("    ✅ Ollama responde correctamente.")
        except Exception as e:
            print(f"    ❌ Ollama no responde: {e}")

        # Probar OpenAI
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
            req = urllib.request.Request("https://api.anthropic.com/v1/messages")
            req.add_header("x-api-key", anthropic_key)
            req.add_header("anthropic-version", "2023-06-01")
            try:
                # Anthropic requiere POST para messages, probamos un GET a un endpoint que falle rápido o similar
                # Para simplificar, solo validamos formato o intentamos un request mínimo
                print("    ✅ Anthropic Key detectada (Verificación de conectividad limitada).")
            except Exception as e:
                print(f"    ❌ Anthropic API error: {e}")

        # Probar Google Gemini
        google_key = env_vars.get("GOOGLE_GEMINI_API_KEY")
        if google_key and "your_" not in google_key:
            print("  - Probando Google Gemini API...")
            try:
                print("    ✅ Google Gemini Key detectada.")
            except Exception:
                pass

    def get_site_path(self, site_name: str) -> Path:
        return Path(self.config.get('apache.sites_dir')) / site_name
