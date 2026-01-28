# unified_stack_manager/platform/package_manager.py

from abc import ABC, abstractmethod
import subprocess
import platform

class PackageManager(ABC):
    """Abstracción para gestores de paquetes"""

    @abstractmethod
    def install(self, packages: list[str]) -> bool:
        pass

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        pass

    @abstractmethod
    def update_cache(self) -> bool:
        pass


class AptPackageManager(PackageManager):
    """Para Debian/Ubuntu"""

    def install(self, packages: list[str]) -> bool:
        try:
            subprocess.run(
                ['apt-get', 'install', '-y'] + packages,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error instalando paquetes: {e.stderr.decode()}")
            return False

    def is_installed(self, package: str) -> bool:
        result = subprocess.run(
            ['dpkg', '-l', package],
            capture_output=True
        )
        return result.returncode == 0

    def update_cache(self) -> bool:
        try:
            subprocess.run(['apt-get', 'update'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class YumPackageManager(PackageManager):
    """Para RedHat/CentOS/Rocky"""

    def install(self, packages: list[str]) -> bool:
        try:
            subprocess.run(
                ['yum', 'install', '-y'] + packages,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error instalando paquetes: {e.stderr.decode()}")
            return False

    def is_installed(self, package: str) -> bool:
        result = subprocess.run(
            ['rpm', '-q', package],
            capture_output=True
        )
        return result.returncode == 0

    def update_cache(self) -> bool:
        try:
            subprocess.run(['yum', 'check-update'], check=False)
            return True
        except subprocess.CalledProcessError:
            return False


def get_package_manager() -> PackageManager:
    """Factory: detecta y retorna el package manager apropiado"""

    if platform.system() != 'Linux':
        raise OSError("LAMPManager solo funciona en Linux")

    # Detectar distribución
    try:
        with open('/etc/os-release') as f:
            os_info = dict(line.strip().split('=', 1) for line in f if '=' in line)
            distro_id = os_info.get('ID', '').strip('"').lower()
    except FileNotFoundError:
        distro_id = 'unknown'

    if distro_id in ['ubuntu', 'debian']:
        return AptPackageManager()
    elif distro_id in ['rhel', 'centos', 'rocky', 'fedora']:
        return YumPackageManager()
    else:
        raise OSError(f"Distribución no soportada: {distro_id}")
