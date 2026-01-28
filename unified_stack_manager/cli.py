#!/usr/bin/env python3
"""
UnifiedStackManager - Gestión unificada de stacks WAMP/LAMP
"""

import sys
import click
from pathlib import Path

from unified_stack_manager.platform.detector import platform_info, PlatformEnum
from unified_stack_manager.core.logger import AuditLogger
from unified_stack_manager.core.config import UnifiedConfig
from unified_stack_manager.core.base_stack_manager import BaseStackManager

@click.group()
@click.option('--dry-run', is_flag=True, help='Simula las acciones sin ejecutarlas')
@click.option('--config', type=click.Path(exists=True, dir_okay=False, path_type=Path), help='Archivo de configuración custom')
@click.option('--verbose', '-v', is_flag=True, help='Salida detallada')
@click.pass_context
def cli(ctx, dry_run, config, verbose):
    """UnifiedStackManager - Herramienta para gestionar stacks WAMP/LAMP."""

    # Banner
    click.echo("╔════════════════════════════════════════╗")
    click.echo("║   UnifiedStackManager v1.0.0           ║")
    click.echo("║   WAMP/LAMP Management Tool            ║")
    click.echo("╚════════════════════════════════════════╝")
    click.echo()

    # Detectar y mostrar plataforma
    click.echo(f"🖥️  Plataforma detectada: {platform_info}")
    click.echo(f"🔑  Privilegios admin: {'✓' if platform_info.is_admin else '✗'}")
    click.echo()

    # Verificar si la plataforma está soportada
    if not platform_info.is_supported():
        click.secho(f"❌ Error: Plataforma no soportada", fg='red')
        click.secho(f"   OS: {platform_info.os.value}", fg='red')
        if platform_info.os == PlatformEnum.LINUX:
            click.secho(f"   Distribución: {platform_info.distribution.value}", fg='red')
        sys.exit(1)

    # Verificar privilegios de administrador
    if not platform_info.is_admin:
        click.secho("❌ Error: Se requieren privilegios de administrador", fg='red')
        if platform_info.os == PlatformEnum.WINDOWS:
            click.secho("   Ejecuta PowerShell como Administrador", fg='yellow')
        else:
            click.secho("   Ejecuta con sudo: sudo unified-stack-manager ...", fg='yellow')
        sys.exit(1)

    # Cargar configuración y logger
    app_config = UnifiedConfig(config_file=config)
    logger = AuditLogger()

    # Importar e instanciar el stack manager apropiado
    manager: BaseStackManager
    if platform_info.os == PlatformEnum.WINDOWS:
        from unified_stack_manager.windows.stack_manager import WindowsStackManager
        manager = WindowsStackManager(config=app_config, logger=logger, dry_run=dry_run)
    elif platform_info.os == PlatformEnum.LINUX:
        from unified_stack_manager.linux.stack_manager import LinuxStackManager
        manager = LinuxStackManager(config=app_config, logger=logger, dry_run=dry_run)
    else:
        click.secho(f"❌ Plataforma no implementada: {platform_info.os.value}", fg='red')
        sys.exit(1)

    ctx.obj = {
        'manager': manager,
        'verbose': verbose
    }

@cli.command()
@click.argument('components', nargs=-1, required=True, type=click.Choice(['apache', 'mysql', 'php', 'all']))
@click.pass_context
def install(ctx, components):
    """Instalar componentes del stack."""
    manager = ctx.obj['manager']
    try:
        manager.install_components(list(components))
    except Exception as e:
        handle_exception(e, ctx.obj['verbose'])

@cli.command('create-site')
@click.argument('site_name')
@click.option('--php-version', default='8.4', type=click.Choice(['7.4', '8.1', '8.2', '8.3', '8.4']), help='Versión de PHP')
@click.option('--drupal-version', default='^11', help='Versión de Drupal (ej: ^11, 11.0.0)')
@click.pass_context
def create_site(ctx, site_name, php_version, drupal_version):
    """Crear un nuevo sitio Drupal."""
    manager = ctx.obj['manager']
    try:
        manager.create_drupal_site(
            site_name=site_name,
            php_version=php_version,
            drupal_version=drupal_version
        )
    except Exception as e:
        handle_exception(e, ctx.obj['verbose'])

@cli.command('list-sites')
@click.pass_context
def list_sites(ctx):
    """Listar sitios existentes."""
    manager = ctx.obj['manager']
    try:
        manager.list_sites()
    except Exception as e:
        handle_exception(e, ctx.obj['verbose'])

@cli.command('switch-php')
@click.argument('site_name')
@click.argument('php_version', type=click.Choice(['7.4', '8.1', '8.2', '8.3', '8.4']))
@click.pass_context
def switch_php(ctx, site_name, php_version):
    """Cambiar la versión de PHP de un sitio."""
    manager = ctx.obj['manager']
    try:
        manager.switch_php_version(site_name, php_version)
    except Exception as e:
        handle_exception(e, ctx.obj['verbose'])

@cli.command()
@click.pass_context
def status(ctx):
    """Mostrar el estado del sistema."""
    manager = ctx.obj['manager']
    try:
        manager.show_status()
    except Exception as e:
        handle_exception(e, ctx.obj['verbose'])

def handle_exception(e, verbose):
    """Manejador de excepciones centralizado."""
    click.secho(f"\n❌ Error: {e}", fg='red', err=True)
    if verbose:
        import traceback
        traceback.print_exc()
    sys.exit(1)

def main():
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.secho("\n⚠️  Operación cancelada por el usuario", fg='yellow')
        sys.exit(130)
    except Exception as e:
        handle_exception(e, True) # Mostrar traceback para errores inesperados en el CLI

if __name__ == '__main__':
    main()
