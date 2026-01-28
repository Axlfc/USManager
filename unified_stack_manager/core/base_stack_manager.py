# unified_stack_manager/core/base_stack_manager.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path

from unified_stack_manager.core.config import UnifiedConfig
from unified_stack_manager.core.logger import AuditLogger
from unified_stack_manager.core.rollback import RollbackManager

class BaseStackManager(ABC):
    """
    Clase base abstracta para WindowsStackManager y LinuxStackManager.
    Define la interfaz común que ambos deben implementar.
    """

    def __init__(self, config: UnifiedConfig, logger: AuditLogger, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.rollback = RollbackManager()
        self.dry_run = dry_run

    @abstractmethod
    def install_components(self, components: List[str]) -> bool:
        """Instala componentes del stack (apache, mysql, php)"""
        pass

    @abstractmethod
    def verify_ai(self, site_name: Optional[str] = None) -> bool:
        """Verifica el entorno de IA y conexiones"""
        pass

    @abstractmethod
    def create_drupal_site(self, site_name: str, php_version: str, drupal_version: str, ai_mode: bool = False) -> bool:
        """Crea un nuevo sitio Drupal"""
        pass

    @abstractmethod
    def list_sites(self) -> List[Dict[str, str]]:
        """Lista todos los sitios existentes"""
        pass

    @abstractmethod
    def switch_php_version(self, site_name: str, php_version: str) -> bool:
        """Cambia la versión de PHP de un sitio"""
        pass

    @abstractmethod
    def show_status(self) -> Dict[str, any]:
        """Muestra el estado del sistema"""
        pass

    @abstractmethod
    def get_site_path(self, site_name: str) -> Path:
        """Retorna el path del sitio"""
        pass

    def _log_operation(self, action: str, target: str, details: Dict = None):
        """Helper para logging consistente"""
        import os
        self.logger.audit(
            action=action,
            target=target,
            user=os.getenv('USERNAME' if self.config.is_windows else 'SUDO_USER', 'unknown'),
            details=details or {}
        )
