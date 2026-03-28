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
    print(f"{GREEN}[INFO]{NC} {msg}", flush=True)


def log_error(msg: str) -> None:
    """Imprime mensaje de error en rojo."""
    print(f"{RED}[ERROR]{NC} {msg}", flush=True)


def log_warn(msg: str) -> None:
    """Imprime mensaje de advertencia en amarillo."""
    print(f"{YELLOW}[WARN]{NC} {msg}", flush=True)


def log_step(msg: str) -> None:
    """Imprime paso de ejecucion en azul."""
    print(f"{BLUE}[STEP]{NC} {msg}", flush=True)


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


def check_root() -> None:
    """Verifica que se esta ejecutando como root (necesario para install/uninstall)."""
    if os.geteuid() != 0:
        log_error("Este subcomando requiere permisos de root.")
        log_error("Ejecuta: sudo python deploy.py <comando>")
        sys.exit(1)


def check_extract_done() -> None:
    """Verifica que existe build-output/ con artefactos extraidos."""
    modules_dir = BUILD_OUTPUT_DIR / "modules"
    if not BUILD_OUTPUT_DIR.exists() or not modules_dir.exists():
        log_error("No se encontraron artefactos extraidos.")
        log_error("Ejecuta primero: python deploy.py extract")
        sys.exit(1)
    ko_count = len(list(modules_dir.glob("*.ko")))
    if ko_count == 0:
        log_error("No hay modulos .ko en build-output/modules/.")
        log_error("Ejecuta primero: python deploy.py extract")
        sys.exit(1)


def get_distro() -> str:
    """Detecta la distribucion del host (debian o centos)."""
    try:
        result = run_cmd(["lsb_release", "-is"], check=False, capture=True)
        distro = result.stdout.strip().lower()
        if any(d in distro for d in ["ubuntu", "debian"]):
            return "debian"
        if any(d in distro for d in ["centos", "fedora", "rhel", "rocky"]):
            return "centos"
    except Exception:
        pass
    # Fallback: detectar por archivos del sistema
    if Path("/etc/debian_version").exists():
        return "debian"
    if Path("/etc/redhat-release").exists():
        return "centos"
    return "unknown"


# ── Rutas de instalacion en el host ──────────────────────────────────────────
def _modules_install_dir(kernel_ver: str) -> Path:
    return Path(f"/lib/modules/{kernel_ver}/extra/openss7")


def _libs_install_dir() -> Path:
    return Path("/usr/local/lib/openss7")


def _bin_install_dir() -> Path:
    return Path("/usr/local/bin")


def cmd_install(args: argparse.Namespace) -> None:
    """Instala OpenSS7 en el host desde build-output/."""
    check_root()
    check_extract_done()

    kernel_ver = get_kernel_version()
    distro = get_distro()
    log_info(f"Kernel del host: {kernel_ver}")
    log_info(f"Distribucion detectada: {distro}")
    log_step("Instalando OpenSS7 en el host...")

    modules_src = BUILD_OUTPUT_DIR / "modules"
    libs_src = BUILD_OUTPUT_DIR / "libs"
    bins_src = BUILD_OUTPUT_DIR / "bin"
    packages_src = BUILD_OUTPUT_DIR / "packages"

    # ── Intentar instalacion por paquetes si estan disponibles ───────────
    deb_files = list(packages_src.glob("*.deb")) if packages_src.exists() else []
    rpm_files = list(packages_src.glob("*.rpm")) if packages_src.exists() else []

    if deb_files and distro == "debian":
        log_step("Instalando paquetes DEB...")
        for deb in deb_files:
            run_cmd(["dpkg", "-i", str(deb)])
        log_info("Paquetes DEB instalados.")
    elif rpm_files and distro == "centos":
        log_step("Instalando paquetes RPM...")
        for rpm in rpm_files:
            run_cmd(["rpm", "-i", "--force", str(rpm)])
        log_info("Paquetes RPM instalados.")
    else:
        # ── Instalacion manual desde artefactos ──────────────────────────
        log_step("Instalacion manual desde artefactos (no hay paquetes DEB/RPM)...")

        # 1. Modulos kernel
        mod_dest = _modules_install_dir(kernel_ver)
        mod_dest.mkdir(parents=True, exist_ok=True)
        ko_files = list(modules_src.glob("*.ko"))
        for ko in ko_files:
            shutil.copy2(str(ko), str(mod_dest / ko.name))
        log_info(f"{len(ko_files)} modulos .ko instalados en {mod_dest}")

        # 2. Librerias compartidas
        lib_dest = _libs_install_dir()
        lib_dest.mkdir(parents=True, exist_ok=True)
        so_files = list(libs_src.glob("*.so*")) if libs_src.exists() else []
        for so in so_files:
            shutil.copy2(str(so), str(lib_dest / so.name))
        if so_files:
            log_info(f"{len(so_files)} librerias .so instaladas en {lib_dest}")
            # Agregar al ld.so.conf y actualizar cache
            ld_conf = Path("/etc/ld.so.conf.d/openss7.conf")
            ld_conf.write_text(f"{lib_dest}\n")
            # -n: actualizar solo los directorios especificados (silencia warnings de non-symlinks)
            run_cmd(["ldconfig", "-n", str(lib_dest)])
            run_cmd(["ldconfig"])
            log_info("ldconfig actualizado.")

        # 3. Binarios
        bin_dest = _bin_install_dir()
        bin_files = [f for f in bins_src.iterdir() if f.is_file()] if bins_src.exists() else []
        for b in bin_files:
            dest = bin_dest / b.name
            shutil.copy2(str(b), str(dest))
            dest.chmod(0o755)
        if bin_files:
            log_info(f"{len(bin_files)} binarios instalados en {bin_dest}")

    # ── depmod para registrar los modulos ─────────────────────────────────
    log_step("Ejecutando depmod -a...")
    run_cmd(["depmod", "-a"])
    log_info("depmod -a completado.")

    # ── Cargar modulos criticos ───────────────────────────────────────────
    log_step("Cargando modulos kernel...")
    modules_to_load = ["streams", "specfs"]
    for mod in modules_to_load:
        result = run_cmd(["modprobe", mod], check=False, capture=True)
        if result.returncode == 0:
            log_info(f"Modulo '{mod}' cargado correctamente.")
        else:
            log_warn(f"No se pudo cargar '{mod}': {result.stderr.strip()}")

    # ── Activar servicios systemd si existen ─────────────────────────────
    log_step("Verificando servicios systemd...")
    for svc in ["openss7", "streams"]:
        result = run_cmd(["systemctl", "enable", "--now", svc], check=False, capture=True)
        if result.returncode == 0:
            log_info(f"Servicio '{svc}' habilitado y arrancado.")
        else:
            log_warn(f"Servicio '{svc}' no encontrado o no disponible (no critico).")

    log_info("Instalacion completada. Ejecuta 'python deploy.py verify' para validar.")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verifica que OpenSS7 esta correctamente instalado y operativo."""
    kernel_ver = get_kernel_version()
    log_info(f"Kernel del host: {kernel_ver}")
    log_step("Verificando instalacion de OpenSS7...")

    pass_count = 0
    fail_count = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        """Registra un resultado de verificacion."""
        nonlocal pass_count, fail_count
        if ok:
            log_info(f"PASS: {label}{' — ' + detail if detail else ''}")
            pass_count += 1
        else:
            log_error(f"FAIL: {label}{' — ' + detail if detail else ''}")
            fail_count += 1

    # ── Modulos kernel ────────────────────────────────────────────────────
    lsmod_result = run_cmd(["lsmod"], check=False, capture=True)
    lsmod_output = lsmod_result.stdout if lsmod_result.returncode == 0 else ""

    for mod in ["streams", "specfs"]:
        loaded = mod in lsmod_output
        check(f"Modulo '{mod}' cargado", loaded,
              "visible en lsmod" if loaded else "no aparece en lsmod")

    # ── Modulos opcionales (no criticos) ─────────────────────────────────
    for mod in ["streams_sctp", "streams_ip"]:
        if mod in lsmod_output:
            log_info(f"INFO: Modulo opcional '{mod}' tambien cargado.")

    # ── Servicios systemd ────────────────────────────────────────────────
    for svc in ["openss7", "streams"]:
        result = run_cmd(["systemctl", "is-active", svc], check=False, capture=True)
        active = result.returncode == 0 and result.stdout.strip() == "active"
        # Los servicios son opcionales — solo se instalan si los unit files existen
        svc_exists = run_cmd(
            ["systemctl", "status", svc], check=False, capture=True
        ).returncode != 4  # 4 = unit not found
        if svc_exists:
            check(f"Servicio '{svc}' activo", active, result.stdout.strip())
        else:
            log_warn(f"INFO: Servicio '{svc}' no instalado (unit file no encontrado).")

    # ── Binarios operativos ───────────────────────────────────────────────
    for bin_name in ["strinfo", "scls"]:
        bin_path = shutil.which(bin_name) or str(_bin_install_dir() / bin_name)
        if Path(bin_path).exists():
            result = run_cmd([bin_path, "--version"], check=False, capture=True)
            # Algunos binarios retornan != 0 en --version pero producen output
            has_output = bool(result.stdout.strip() or result.stderr.strip())
            check(f"Binario '{bin_name}' ejecutable", has_output,
                  f"retorno {result.returncode}")
        else:
            check(f"Binario '{bin_name}' encontrado", False, f"{bin_path} no existe")

    # ── Archivos de modulos instalados ────────────────────────────────────
    mod_dir = _modules_install_dir(kernel_ver)
    if mod_dir.exists():
        ko_count = len(list(mod_dir.glob("*.ko")))
        check(f"Directorio de modulos {mod_dir}", ko_count > 0,
              f"{ko_count} modulos .ko")
    else:
        # Los modulos pueden haber sido instalados via dpkg en otra ruta
        alt_check = run_cmd(
            ["find", f"/lib/modules/{kernel_ver}", "-name", "streams.ko"],
            check=False, capture=True
        )
        streams_found = bool(alt_check.stdout.strip())
        check("streams.ko instalado en /lib/modules", streams_found)

    # ── Resumen ───────────────────────────────────────────────────────────
    print()
    log_step(f"Resultado: {pass_count} PASS, {fail_count} FAIL")
    if fail_count == 0:
        log_info("OpenSS7 verificado correctamente.")
    else:
        log_error(f"{fail_count} verificaciones fallaron.")
        sys.exit(1)


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Desinstala OpenSS7 del host limpiamente."""
    check_root()

    kernel_ver = get_kernel_version()
    distro = get_distro()
    log_info(f"Kernel del host: {kernel_ver}")
    log_step("Desinstalando OpenSS7 del host...")

    # ── Detener y deshabilitar servicios ─────────────────────────────────
    log_step("Deteniendo servicios systemd...")
    for svc in ["openss7", "streams"]:
        run_cmd(["systemctl", "stop", svc], check=False, capture=True)
        run_cmd(["systemctl", "disable", svc], check=False, capture=True)
        log_info(f"Servicio '{svc}' detenido y deshabilitado.")

    # ── Descargar modulos kernel ──────────────────────────────────────────
    log_step("Descargando modulos kernel...")
    lsmod_result = run_cmd(["lsmod"], check=False, capture=True)
    lsmod_output = lsmod_result.stdout if lsmod_result.returncode == 0 else ""

    # Descargar en orden correcto:
    # streams usa specfs, por tanto streams se descarga ANTES que specfs
    modules_to_unload = ["streams_sctp", "streams_ip", "streams", "specfs"]
    for mod in modules_to_unload:
        if mod in lsmod_output:
            result = run_cmd(["rmmod", mod], check=False, capture=True)
            if result.returncode == 0:
                log_info(f"Modulo '{mod}' descargado.")
            else:
                log_warn(f"No se pudo descargar '{mod}': {result.stderr.strip()}")
        else:
            log_info(f"Modulo '{mod}' no estaba cargado, saltando.")

    # ── Desinstalar paquetes si fueron instalados ─────────────────────────
    # Intentar dpkg -r (debian) o rpm -e (centos)
    if distro == "debian":
        result = run_cmd(
            ["dpkg", "--list"], check=False, capture=True
        )
        openss7_pkgs = [
            line.split()[1]
            for line in result.stdout.splitlines()
            if "openss7" in line.lower() and line.startswith("ii")
        ]
        for pkg in openss7_pkgs:
            run_cmd(["dpkg", "-r", pkg], check=False)
            log_info(f"Paquete '{pkg}' eliminado.")
    elif distro == "centos":
        result = run_cmd(["rpm", "-qa", "openss7*"], check=False, capture=True)
        for pkg in result.stdout.splitlines():
            if pkg.strip():
                run_cmd(["rpm", "-e", pkg.strip()], check=False)
                log_info(f"Paquete '{pkg}' eliminado.")

    # ── Eliminar archivos instalados manualmente ──────────────────────────
    log_step("Eliminando archivos instalados...")

    mod_dir = _modules_install_dir(kernel_ver)
    if mod_dir.exists():
        shutil.rmtree(str(mod_dir))
        log_info(f"Directorio de modulos eliminado: {mod_dir}")

    lib_dir = _libs_install_dir()
    if lib_dir.exists():
        shutil.rmtree(str(lib_dir))
        log_info(f"Directorio de librerias eliminado: {lib_dir}")
        ld_conf = Path("/etc/ld.so.conf.d/openss7.conf")
        if ld_conf.exists():
            ld_conf.unlink()
        run_cmd(["ldconfig"], check=False)
        log_info("ldconfig actualizado.")

    bin_dir = _bin_install_dir()
    for bin_name in ["strinfo", "scls", "strace", "strerr", "slconfig", "stracer"]:
        bin_path = bin_dir / bin_name
        if bin_path.exists():
            bin_path.unlink()
            log_info(f"Binario '{bin_name}' eliminado.")

    # ── depmod final ──────────────────────────────────────────────────────
    log_step("Actualizando modulos del kernel (depmod -a)...")
    run_cmd(["depmod", "-a"], check=False)
    log_info("depmod -a completado.")

    log_info("Desinstalacion completada.")


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
