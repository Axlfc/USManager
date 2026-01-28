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
                self._execute_site_creation(site_name, php_version, db_name, doc_root)

            self._log_operation('create_drupal_site', site_name, {'php': php_version, 'drupal': drupal_version})
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
        """Verifica el entorno de IA en Linux (Placeholder)."""
        print("🔍 Verificación de IA en Linux no implementada detalladamente.")
        if not site_name:
            print("✅ .env.example global existe." if Path(".env.example").exists() else "❌ .env.example global falta.")
        return True

    def get_site_path(self, site_name: str) -> Path:
        return Path(self.config.get('apache.sites_dir')) / site_name
