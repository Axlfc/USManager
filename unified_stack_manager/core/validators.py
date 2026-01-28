# unified_stack_manager/core/validators.py
import os
import re
import socket
from pathlib import Path

class SystemValidator:
    """Valida que el sistema cumple requisitos antes de cambios"""

    @staticmethod
    def validate_prerequisites() -> tuple[bool, list[str]]:
        """Verifica que el sistema está listo"""
        errors = []

        # Verificar permisos de sudo
        if os.geteuid() != 0:
            errors.append("Debe ejecutarse con sudo/root")

        # Verificar espacio en disco (mínimo 1GB libre para operar)
        try:
            statvfs = os.statvfs('/')
            free_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            if free_gb < 1:
                errors.append(f"Espacio insuficiente: {free_gb:.1f}GB (mínimo 1GB)")
        except OSError as e:
            errors.append(f"No se pudo verificar el espacio en disco: {e}")

        # Verificar conectividad a Internet
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            errors.append("Sin conectividad a Internet")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_site_config(config: dict, supported_php_versions: list) -> tuple[bool, list[str]]:
        """Valida configuración de un sitio antes de crearlo"""
        errors = []

        # Validar nombre de sitio
        site_name = config.get('site_name', '')
        if not re.match(r'^[a-z0-9.-]+$', site_name) or site_name.startswith('-') or site_name.endswith('.'):
            errors.append(f"Nombre de sitio inválido: '{site_name}'. Solo a-z, 0-9, ., - son permitidos y no puede empezar/terminar con simbolos.")

        # Validar versión PHP
        php_version = config.get('php_version')
        if php_version not in supported_php_versions:
            errors.append(f"Versión PHP no soportada: {php_version}. Soportadas: {supported_php_versions}")

        # Validar que el dominio no exista
        vhost_path = Path(f"/etc/apache2/sites-available/{site_name}.conf")
        if vhost_path.exists():
            errors.append(f"El virtual host para {site_name} ya existe en {vhost_path}")

        doc_root = Path(f"/var/www/{site_name}")
        if doc_root.exists():
            errors.append(f"El DocumentRoot {doc_root} ya existe.")

        return (len(errors) == 0, errors)
