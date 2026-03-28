#!/usr/bin/env python3
"""
OpenSS7 Deploy System — CLI de despliegue containerizado.

Automatiza compilacion, pruebas, extraccion, instalacion,
verificacion y desinstalacion de OpenSS7.

Uso:
    python deploy.py build      # Compila todo en Docker
    python deploy.py test       # Ejecuta make check + valida artefactos
    python deploy.py extract    # Extrae paquetes compilados
    python deploy.py install    # Instala en el host
    python deploy.py verify     # Verifica modulos y servicios
    python deploy.py uninstall  # Desinstala limpiamente
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Directorio raiz del proyecto (donde esta este script)
PROJECT_DIR = Path(__file__).resolve().parent
BUILD_OUTPUT_DIR = PROJECT_DIR / "build-output"

# Colores ANSI
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No color


def log_info(msg: str) -> None:
    """Imprime mensaje informativo en verde."""
    print(f"{GREEN}[INFO]{NC} {msg}")


def log_error(msg: str) -> None:
    """Imprime mensaje de error en rojo."""
    print(f"{RED}[ERROR]{NC} {msg}")


def log_warn(msg: str) -> None:
    """Imprime mensaje de advertencia en amarillo."""
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_step(msg: str) -> None:
    """Imprime paso de ejecucion en azul."""
    print(f"{BLUE}[STEP]{NC} {msg}")


def run_cmd(
    cmd: List[str],
    check: bool = True,
    capture: bool = False,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Ejecuta un comando del sistema con manejo de errores."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True,
            cwd=cwd or str(PROJECT_DIR),
        )
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Comando fallo: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        raise
    except FileNotFoundError:
        log_error(f"Comando no encontrado: {cmd[0]}")
        sys.exit(1)


def check_docker() -> None:
    """Verifica que Docker esta instalado y corriendo."""
    if not shutil.which("docker"):
        log_error("Docker no esta instalado.")
        log_error("Instala Docker: https://docs.docker.com/engine/install/")
        sys.exit(1)

    result = run_cmd(["docker", "info"], check=False, capture=True)
    if result.returncode != 0:
        log_error("Docker no esta corriendo. Inicia el servicio Docker.")
        sys.exit(1)


def check_docker_compose() -> None:
    """Verifica que docker compose esta disponible."""
    result = run_cmd(["docker", "compose", "version"], check=False, capture=True)
    if result.returncode != 0:
        log_error("docker compose no esta disponible.")
        sys.exit(1)


def get_kernel_version() -> str:
    """Obtiene la version del kernel del host."""
    return platform.release()


def get_nproc() -> int:
    """Obtiene el numero de CPUs disponibles."""
    return os.cpu_count() or 1


# ─── Subcomandos ───────────────────────────────────────────────────────────


def cmd_build(args: argparse.Namespace) -> None:
    """Compila OpenSS7 dentro de Docker."""
    check_docker()
    check_docker_compose()

    kernel_ver = get_kernel_version()
    jobs = get_nproc()
    log_info(f"Kernel del host: {kernel_ver}")
    log_info(f"Jobs de compilacion: {jobs}")

    # Verificar kernel headers
    headers_path = Path(f"/lib/modules/{kernel_ver}/build")
    if not headers_path.exists():
        log_error(f"Kernel headers no encontrados en {headers_path}")
        log_error(f"Instala: sudo apt install linux-headers-{kernel_ver}")
        sys.exit(1)
    log_info(f"Kernel headers encontrados: {headers_path}")

    # Crear directorio de salida
    BUILD_OUTPUT_DIR.mkdir(exist_ok=True)

    # Construir imagen y ejecutar build
    log_step("Construyendo imagen Docker...")
    start_time = time.time()

    env = os.environ.copy()
    env["BUILD_JOBS"] = str(jobs)
    env["KERNEL_VERSION"] = kernel_ver

    try:
        subprocess.run(
            ["docker", "compose", "up", "--build", "--abort-on-container-exit"],
            cwd=str(PROJECT_DIR),
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        log_error("Build fallo. Revisa los logs de arriba.")
        sys.exit(1)
    except KeyboardInterrupt:
        log_warn("Build cancelado por el usuario.")
        run_cmd(["docker", "compose", "down"], check=False)
        sys.exit(130)

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    log_info(f"Build completado en {minutes}m {seconds}s")

    # Limpiar contenedores
    run_cmd(["docker", "compose", "down"], check=False)


def check_build_exists() -> None:
    """Verifica que existe un build previo (volumen de cache de Docker)."""
    result = run_cmd(
        ["docker", "volume", "inspect", "openss7-build-cache"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        log_error("No se encontro build previo.")
        log_error("Ejecuta primero: python deploy.py build")
        sys.exit(1)


def cmd_test(args: argparse.Namespace) -> None:
    """Ejecuta make check dentro del contenedor y valida artefactos del build."""
    check_docker()
    check_docker_compose()
    check_build_exists()

    kernel_ver = get_kernel_version()
    jobs = get_nproc()
    log_info(f"Kernel del host: {kernel_ver}")
    log_step("Iniciando tests y validacion de artefactos en Docker...")

    env = os.environ.copy()
    env["BUILD_JOBS"] = str(jobs)
    env["KERNEL_VERSION"] = kernel_ver

    start_time = time.time()
    try:
        subprocess.run(
            ["docker", "compose", "run", "--rm", "builder", "test"],
            cwd=str(PROJECT_DIR),
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        log_error("Tests o validacion de artefactos fallaron. Revisa los logs de arriba.")
        sys.exit(1)
    except KeyboardInterrupt:
        log_warn("Test cancelado por el usuario.")
        sys.exit(130)

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    log_info(f"Tests completados en {minutes}m {seconds}s")


def cmd_extract(args: argparse.Namespace) -> None:
    """Extrae artefactos compilados del contenedor al host en build-output/."""
    check_docker()
    check_docker_compose()
    check_build_exists()

    kernel_ver = get_kernel_version()
    jobs = get_nproc()
    log_info(f"Kernel del host: {kernel_ver}")
    log_step("Extrayendo artefactos del build al host...")

    # Crear directorio de salida en el host
    BUILD_OUTPUT_DIR.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["BUILD_JOBS"] = str(jobs)
    env["KERNEL_VERSION"] = kernel_ver

    start_time = time.time()
    try:
        subprocess.run(
            ["docker", "compose", "run", "--rm", "builder", "extract"],
            cwd=str(PROJECT_DIR),
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        log_error("Extraccion de artefactos fallo. Revisa los logs de arriba.")
        sys.exit(1)
    except KeyboardInterrupt:
        log_warn("Extraccion cancelada por el usuario.")
        sys.exit(130)

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # Listar artefactos extraidos en el host
    if BUILD_OUTPUT_DIR.exists():
        ko_count = len(list((BUILD_OUTPUT_DIR / "modules").glob("*.ko"))) if (BUILD_OUTPUT_DIR / "modules").exists() else 0
        so_count = len(list((BUILD_OUTPUT_DIR / "libs").glob("*.so*"))) if (BUILD_OUTPUT_DIR / "libs").exists() else 0
        bin_count = len(list((BUILD_OUTPUT_DIR / "bin").iterdir())) if (BUILD_OUTPUT_DIR / "bin").exists() else 0
        deb_count = len(list((BUILD_OUTPUT_DIR / "packages").glob("*.deb"))) if (BUILD_OUTPUT_DIR / "packages").exists() else 0
        log_info(f"Artefactos en {BUILD_OUTPUT_DIR}:")
        log_info(f"  Modulos .ko : {ko_count}")
        log_info(f"  Libs .so    : {so_count}")
        log_info(f"  Binarios    : {bin_count}")
        log_info(f"  Paquetes DEB: {deb_count}")

    log_info(f"Extraccion completada en {minutes}m {seconds}s")


def cmd_install(args: argparse.Namespace) -> None:
    """Instala OpenSS7 en el host. (Fase 4)"""
    log_warn("Subcomando 'install' sera implementado en Fase 4.")
    sys.exit(0)


def cmd_verify(args: argparse.Namespace) -> None:
    """Verifica modulos cargados y servicios activos. (Fase 4)"""
    log_warn("Subcomando 'verify' sera implementado en Fase 4.")
    sys.exit(0)


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Desinstala OpenSS7 del host. (Fase 4)"""
    log_warn("Subcomando 'uninstall' sera implementado en Fase 4.")
    sys.exit(0)


# ─── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada principal del CLI."""
    parser = argparse.ArgumentParser(
        description="OpenSS7 Deploy System — Compilacion y despliegue containerizado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python deploy.py build          Compila OpenSS7 en Docker
  python deploy.py test           Ejecuta tests y valida artefactos
  python deploy.py extract        Extrae paquetes compilados
  python deploy.py install        Instala en el host (requiere sudo)
  python deploy.py verify         Verifica instalacion
  python deploy.py uninstall      Desinstala (requiere sudo)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcomando a ejecutar")
    subparsers.required = True

    # build
    p_build = subparsers.add_parser("build", help="Compila OpenSS7 en Docker")
    p_build.set_defaults(func=cmd_build)

    # test
    p_test = subparsers.add_parser("test", help="Ejecuta make check + valida artefactos")
    p_test.set_defaults(func=cmd_test)

    # extract
    p_extract = subparsers.add_parser("extract", help="Extrae paquetes compilados")
    p_extract.set_defaults(func=cmd_extract)

    # install
    p_install = subparsers.add_parser("install", help="Instala en el host")
    p_install.set_defaults(func=cmd_install)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verifica modulos y servicios")
    p_verify.set_defaults(func=cmd_verify)

    # uninstall
    p_uninstall = subparsers.add_parser("uninstall", help="Desinstala OpenSS7")
    p_uninstall.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
