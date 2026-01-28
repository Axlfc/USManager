# unified_stack_manager/core/logger.py

import logging
import json
import os
from datetime import datetime
from pathlib import Path

class AuditLogger:
    """Logger especializado para auditoría de cambios en producción"""

    def __init__(self, log_dir: Path = Path("/var/log/unified-stack-manager")):
        self.log_dir = log_dir
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"Warning: No permission to create log directory {self.log_dir}. Logging may fail.")
            # In a real scenario, you might want to fallback to a user-local directory
            # For now, we'll let it fail during handler creation if permissions are not set

        # Logger técnico (para debugging)
        self.tech_logger = self._setup_tech_logger()

        # Logger de auditoría (para compliance)
        self.audit_logger = self._setup_audit_logger()

    def _setup_tech_logger(self):
        logger = logging.getLogger('unified_stack_manager.technical')
        logger.setLevel(logging.DEBUG)

        try:
            handler = logging.FileHandler(self.log_dir / 'technical.log')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)
        except PermissionError:
            print(f"Warning: Could not attach file handler for technical.log due to permissions.")
        return logger

    def _setup_audit_logger(self):
        logger = logging.getLogger('unified_stack_manager.audit')
        logger.setLevel(logging.INFO)

        try:
            handler = logging.FileHandler(self.log_dir / 'audit.log')
            logger.addHandler(handler)
        except PermissionError:
            print(f"Warning: Could not attach file handler for audit.log due to permissions.")

        return logger

    def audit(self, action: str, target: str, user: str, details: dict = None):
        """Registra acción auditable en formato JSON"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'target': target,
            'user': user,
            'details': details or {}
        }
        self.audit_logger.info(json.dumps(entry))
