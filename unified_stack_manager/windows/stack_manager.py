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

    def create_drupal_site(self, site_name: str, php_version: str, drupal_version: str) -> bool:
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
        if not self.drupal_manager.create_site(site_name, drupal_version):
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

    def get_site_path(self, site_name: str) -> Path:
        base_path = self.config.get('apache.sites_dir', 'C:/xampp/htdocs')
        return Path(base_path) / site_name
