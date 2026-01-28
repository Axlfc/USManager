# unified_stack_manager/linux/php_manager.py

from unified_stack_manager.platform.package_manager import get_package_manager
import subprocess

class PHPManager:
    def __init__(self, config, logger, rollback):
        self.pkg_manager = get_package_manager()
        self.config = config
        self.logger = logger
        self.rollback = rollback
        self.ppa = self.config.get('php.ppa_repository', 'ppa:ondrej/php')

    def _add_ppa(self) -> bool:
        """Añade el PPA de ondrej/php si no está presente."""
        try:
            # Comprobar si el PPA ya está añadido
            result = subprocess.run(
                ['grep', '-rh', '^deb', '/etc/apt/sources.list.d/'],
                capture_output=True, text=True, check=True
            )
            if 'ondrej' in result.stdout and 'php' in result.stdout:
                print("El PPA de ondrej/php ya está configurado.")
                return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            # El directorio puede no existir o grep puede no encontrar nada
            pass

        print(f"Añadiendo el PPA: {self.ppa}")

        # Instalar software-properties-common si es necesario
        if not self.pkg_manager.is_installed('software-properties-common'):
            print("Instalando 'software-properties-common'...")
            if not self.pkg_manager.install(['software-properties-common']):
                print("Error: No se pudo instalar 'software-properties-common'.")
                return False

        try:
            subprocess.run(
                ['add-apt-repository', '-y', self.ppa],
                check=True,
                capture_output=True
            )
            print("PPA añadido correctamente. Actualizando caché de paquetes...")
            return self.pkg_manager.update_cache()
        except subprocess.CalledProcessError as e:
            print(f"Error al añadir el PPA: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            print("Error: El comando 'add-apt-repository' no fue encontrado.")
            return False

    def install(self, version: str) -> bool:
        """Instala una versión específica de PHP y módulos comunes."""

        supported_versions = self.config.get('php.supported_versions', [])
        if version not in supported_versions:
            print(f"Error: La versión de PHP '{version}' no está soportada en la configuración.")
            return False

        if not self._add_ppa():
            return False

        package_name = f'php{version}'
        if self.pkg_manager.is_installed(package_name):
            print(f"PHP {version} ya está instalado.")
            return True

        print(f"Instalando PHP {version} y módulos comunes...")

        # Lista de módulos comunes para aplicaciones web (ej. Drupal, WordPress)
        packages = self.config.get(f'php.modules_{version}', [
            f'php{version}',
            f'php{version}-cli',
            f'php{version}-fpm',
            f'php{version}-mysql',
            f'php{version}-gd',
            f'php{version}-xml',
            f'php{version}-curl',
            f'php{version}-mbstring',
            f'php{version}-zip',
            f'php{version}-intl'
        ])

        return self.pkg_manager.install(packages)
