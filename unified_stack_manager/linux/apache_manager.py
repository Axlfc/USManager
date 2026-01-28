# unified_stack_manager/linux/apache_manager.py

import subprocess
from pathlib import Path
from unified_stack_manager.platform.package_manager import get_package_manager

class ApacheManager:
    def __init__(self, config, logger, rollback):
        self.pkg_manager = get_package_manager()
        self.config = config
        self.logger = logger
        self.rollback = rollback

    def install(self) -> bool:
        """Instala Apache HTTP Server"""

        if self.pkg_manager.is_installed('apache2'):
            print("Apache ya está instalado.")
            return True

        print("Instalando Apache...")
        packages = self.config.get('apache.install_packages', [
            'apache2',
            'apache2-utils',
            'libapache2-mod-fcgid'
        ])

        self.pkg_manager.update_cache()
        return self.pkg_manager.install(packages)

    def create_virtualhost(self, site_name: str, doc_root: str, php_version: str) -> bool:
        """Crea un archivo de VirtualHost para un sitio."""
        vhost_dir = Path(self.config.get('apache.vhosts_dir'))
        vhost_file = vhost_dir / f"{site_name}.conf"

        doc_root_subdir = self.config.get('apache.doc_root_subdir', '')
        full_doc_root = Path(doc_root) / doc_root_subdir

        # Template del VirtualHost
        vhost_template = f"""
<VirtualHost *:80>
    ServerName {site_name}
    DocumentRoot {full_doc_root}

    <Directory {full_doc_root}>
        AllowOverride All
        Require all granted
    </Directory>

    <FilesMatch \.php$>
        SetHandler "proxy:unix:/var/run/php/php{php_version}-fpm.sock|fcgi://localhost/"
    </FilesMatch>

    ErrorLog ${{APACHE_LOG_DIR}}/{site_name}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{site_name}_access.log combined
</VirtualHost>
"""
        try:
            with self.rollback.protected_operation('create_vhost', [vhost_file]):
                vhost_file.write_text(vhost_template)
                # Activar el sitio y desactivar el default
                subprocess.run(['a2ensite', site_name], check=True, capture_output=True)
                subprocess.run(['a2dissite', '000-default'], check=False, capture_output=True)
            return True
        except (subprocess.CalledProcessError, IOError) as e:
            print(f"Error al crear o activar el VirtualHost: {e}")
            return False

    def manage_service(self, action: str) -> bool:
        """Gestiona el servicio de Apache (start, stop, restart, reload, status)."""
        if action not in ['start', 'stop', 'restart', 'reload', 'status']:
            print(f"Acción '{action}' no válida para Apache.")
            return False
        try:
            subprocess.run(['systemctl', action, 'apache2'], check=True)
            print(f"Servicio Apache {action}ed correctamente.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar '{action}' en el servicio Apache: {e}")
            return False
        except FileNotFoundError:
            print("Error: El comando 'systemctl' no fue encontrado.")
            return False

    def reload_service(self) -> bool:
        """Recarga la configuración de Apache sin reiniciar."""
        return self.manage_service('reload')

    def get_status(self) -> Dict[str, any]:
        """Obtiene el estado del servicio Apache."""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'apache2'], capture_output=True, text=True)
            is_active = result.stdout.strip() == 'active'
            return {'is_active': is_active, 'status': result.stdout.strip()}
        except FileNotFoundError:
            return {'is_active': False, 'status': 'unknown', 'error': 'systemctl not found'}
