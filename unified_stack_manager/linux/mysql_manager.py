# unified_stack_manager/linux/mysql_manager.py

from unified_stack_manager.platform.package_manager import get_package_manager
import subprocess

class MySQLManager:
    def __init__(self, config, logger, rollback):
        self.pkg_manager = get_package_manager()
        self.config = config
        self.logger = logger
        self.rollback = rollback

    def install(self) -> bool:
        """Instala MySQL Server (o MariaDB, el default del sistema)"""

        if self.pkg_manager.is_installed('mysql-server'):
            print("MySQL ya está instalado.")
            return True

        print("Instalando MySQL/MariaDB...")

        # mysql-server es un paquete virtual en Debian/Ubuntu que instala
        # el default (usualmente mariadb-server)
        packages = ['mysql-server']

        self.pkg_manager.update_cache()
        if not self.pkg_manager.install(packages):
            return False

        # Asegurarse que el servicio está corriendo para operaciones post-install
        self.manage_service('start')

        # Aquí se podría ejecutar mysql_secure_installation de forma no interactiva
        # pero es complejo y depende de la versión. Por ahora, se omite.

        return True

    def manage_service(self, action: str) -> bool:
        """Gestiona el servicio de MySQL (start, stop, restart, status)"""
        if action not in ['start', 'stop', 'restart', 'status']:
            print(f"Acción '{action}' no válida.")
            return False
        try:
            # systemctl es el estándar en sistemas modernos (Ubuntu >= 16.04)
            subprocess.run(['systemctl', action, 'mysql'], check=True, capture_output=True)
            print(f"Servicio MySQL {action}ed correctamente.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar '{action}' en el servicio MySQL: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            print("Error: El comando 'systemctl' no fue encontrado.")
            return False

    def _execute_query(self, query: str) -> bool:
        """Ejecuta una consulta SQL como root."""
        try:
            # Usar -e para pasar el comando directamente
            subprocess.run(['mysql', '-e', query], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar la consulta SQL: {e.stderr.decode()}")
            return False

    def create_database(self, db_name: str) -> bool:
        """Crea una nueva base de datos."""
        charset = self.config.get('mysql.default_charset', 'utf8mb4')
        collation = self.config.get('mysql.default_collation', 'utf8mb4_unicode_ci')
        query = f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET {charset} COLLATE {collation};"
        return self._execute_query(query)

    def create_user(self, username: str, password: str, host: str = 'localhost') -> bool:
        """Crea un nuevo usuario de base de datos."""
        query = f"CREATE USER IF NOT EXISTS '{username}'@'{host}' IDENTIFIED BY '{password}';"
        return self._execute_query(query)

    def grant_privileges(self, db_name: str, username: str, host: str = 'localhost') -> bool:
        """Otorga todos los privilegios a un usuario sobre una base de datos."""
        query = f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'{host}';"
        if not self._execute_query(query):
            return False
        # Aplicar los cambios
        return self._execute_query("FLUSH PRIVILEGES;")

    def get_status(self) -> Dict[str, any]:
        """Obtiene el estado del servicio MySQL."""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'mysql'], capture_output=True, text=True)
            is_active = result.stdout.strip() == 'active'
            return {'is_active': is_active, 'status': result.stdout.strip()}
        except FileNotFoundError:
            return {'is_active': False, 'status': 'unknown', 'error': 'systemctl not found'}
