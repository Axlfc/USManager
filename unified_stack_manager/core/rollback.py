# unified_stack_manager/core/rollback.py

import shutil
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

class RollbackManager:
    """Gestiona backups y rollbacks automáticos"""

    def __init__(self, backup_dir: Path = Path('/var/backups/lamp-manager')):
        self.backup_dir = backup_dir
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"Warning: No permission to create backup directory {self.backup_dir}. Rollback may fail.")

    @contextmanager
    def protected_operation(self, operation_name: str, targets: list[Path]):
        """
        Context manager que hace backup antes y rollback si falla.

        Uso:
            with rollback.protected_operation('update_vhost', [vhost_file]):
                # hacer cambios arriesgados
                modify_virtualhost()
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = f"{operation_name}_{timestamp}"
        backups = []

        try:
            # Crear backups
            for target in targets:
                if target.exists():
                    backup_path = self.backup_dir / f"{backup_id}_{target.name.replace('/', '_')}"
                    try:
                        if target.is_dir():
                            shutil.copytree(target, backup_path)
                        else:
                            shutil.copy2(target, backup_path)
                        backups.append((target, backup_path))
                    except (IOError, OSError) as e:
                        print(f"Warning: Could not create backup for {target}. Error: {e}")


            yield  # Ejecutar la operación

            # Si llegamos aquí, todo OK - mantener backups por 7 días
            self._cleanup_old_backups(days=7)

        except Exception as e:
            # Si falla, restaurar backups
            print(f"❌ Error in {operation_name}: {e}")
            print("🔄 Executing rollback...")

            for original, backup in backups:
                try:
                    if original.is_dir():
                        shutil.rmtree(original)
                        shutil.copytree(backup, original)
                    else:
                        shutil.copy2(backup, original)
                    print(f"   ✓ Restored: {original}")
                except (IOError, OSError) as e:
                    print(f"FATAL: Could not restore backup from {backup} to {original}. Manual intervention required. Error: {e}")

            raise  # Re-raise la excepción

    def _cleanup_old_backups(self, days: int):
        """Elimina backups más antiguos de X días"""
        import time
        cutoff = time.time() - (days * 86400)

        try:
            for backup in self.backup_dir.glob('*'):
                if backup.stat().st_mtime < cutoff:
                    backup.unlink()
        except (IOError, OSError) as e:
            print(f"Warning: Could not clean up old backups. Error: {e}")
