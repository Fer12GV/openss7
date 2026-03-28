#!/bin/bash
# Script de build para ejecutar dentro del contenedor Docker
# Uso: docker-build.sh [build|test|extract]
set -e

ACTION="${1:-build}"
BUILD_DIR="/build"
OUTPUT_DIR="/output"
JOBS="${BUILD_JOBS:-$(nproc)}"
KERNEL_VERSION="${KERNEL_VERSION:?ERROR: KERNEL_VERSION must be set via environment}"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_kernel_headers() {
    if [ ! -d "/lib/modules/${KERNEL_VERSION}" ]; then
        log_error "Kernel headers not found for ${KERNEL_VERSION}"
        log_error "Mount /lib/modules from host via docker-compose"
        exit 1
    fi
    log_info "Kernel headers found: ${KERNEL_VERSION}"
}

do_autogen() {
    log_info "Running autogen.sh..."
    cd /opt/openss7

    # Git safe directory (el repo es montado desde el host con otro owner)
    git config --global --add safe.directory /opt/openss7 2>/dev/null || true

    if [ ! -f configure ]; then
        bash ./autogen.sh
        log_info "autogen.sh completed"
    else
        log_info "configure already exists, skipping autogen"
    fi
}

do_configure() {
    log_info "Configuring with --prefix=/usr --sysconfdir=/etc..."
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    if [ ! -f Makefile ]; then
        # KCC: compilador del kernel
        # linux_cv_k_running=no: fuerza a leer version de compile.h en vez de /proc/version
        #   (el sed de /proc/version no parsea correctamente el formato Ubuntu)
        # linux_cv_k_compiler_match=yes: skip check si compile.h tampoco existe
        # --disable-maintainer-mode: evita -Werror en kernel CFLAGS (warnings != errores)
        KCC=gcc linux_cv_k_running=no linux_cv_k_compiler_match=yes linux_cv_k_compiler_vmatch=yes \
        /opt/openss7/configure \
            --prefix=/usr \
            --sysconfdir=/etc \
            --localstatedir=/var \
            --enable-autotest \
            --enable-silent-rules \
            --disable-java \
            --disable-maintainer-mode \
            --disable-32bit-libs \
            --with-k-release="${KERNEL_VERSION}"
        log_info "Configure completed"
    else
        log_info "Makefile already exists, skipping configure"
    fi
}

do_patch_makefile() {
    # Parchar el Makefile generado para resolver dependencias de build del kernel.
    #
    # Contexto: modules.Pk (generado por configure/make) lista dependencias como:
    #   stamp-mobjects: specfs.mod.c streams.mod.c streams_mstr.mod.c ...
    #   stamp-kobjects: specfs.o streams.o streams_mstr.o ...
    #
    # Los archivos .mod.c los genera stamp-modpost (via modpost.awk) como side effects.
    # Los archivos streams_*.o los genera stamp-verobjs (via ld -r) como side effects.
    # Make no tiene reglas explicitas para ellos y falla con:
    #   "No rule to make target 'specfs.mod.c', needed by 'stamp-mobjects'"
    #   "No rule to make target 'streams_mstr.o', needed by 'stamp-kobjects'"
    #
    # Fix: agregar pattern rules al Makefile que declaran que:
    #   - cualquier .mod.c se obtiene corriendo stamp-modpost
    #   - cualquier streams_*.o se obtiene corriendo stamp-verobjs
    local makefile="${BUILD_DIR}/Makefile"
    if [ ! -f "${makefile}" ]; then
        return 0
    fi
    if ! grep -q 'compat-pattern-rules-marker' "${makefile}" 2>/dev/null; then
        # Nota: el tab de receta DEBE ser un tab real (heredoc lo preserva)
        cat >> "${makefile}" << 'EOF'

###################################################################################################
# compat-pattern-rules-marker
# Reglas de patron para archivos generados como side effects de stamp-modpost/stamp-verobjs.
# stamp-modpost (via modpost.awk) genera .mod.c; stamp-verobjs (via ld -r) genera streams_*.o
# Sin estas reglas, make falla con "No rule to make target X" durante resolucion de deps.
%.mod.c: stamp-modpost
	@true
streams_%.o: stamp-verobjs
	@true
###################################################################################################
EOF
        log_info "Makefile parchado: pattern rules para .mod.c y streams_*.o"
    fi
}

do_build() {
    check_kernel_headers
    do_autogen
    do_configure
    do_patch_makefile

    log_info "Building with ${JOBS} parallel jobs..."
    cd "${BUILD_DIR}"

    # Header de compatibilidad para kernel 5.x+ (resuelve f_dentry, time_t, proc_ops, etc.)
    COMPAT_HEADER="/opt/openss7/scripts/compat-kernel.h"
    COMPAT_CPPFLAGS="-include ${COMPAT_HEADER}"
    # -Wno-error: el kernel 5.x agrega -Werror=xxx que rompe con warnings del codigo legacy
    # KCFLAGS: flags extra para kbuild (compilacion de modulos kernel)
    COMPAT_CFLAGS="-Wno-error"

    # MODPOST_OPTIONS: quitamos -m (modversions) porque ld -r pierde el flag 'O' (object type)
    # de los simbolos __ksymtab_*, y modpost.awk lo necesita para reconocerlos como exports.
    # Sin -m, la condicion "substr(flags,7,1) == 'O' || !values['modversions']" = TRUE
    # para todos los __ksymtab_*, resolviendo los 2439 errores "unresolved; symbol".
    # Conservamos: -u (module unload), -x (export syms), -w (weak symbols)
    COMPAT_MODPOST_OPTIONS="-u -x -w"

    # KERNEL_MODFLAGS: -DINCLUDE_VERMAGIC habilita linux/vermagic.h en .mod.c generados.
    # En kernel 5.x, vermagic.h tiene un guard que requiere INCLUDE_VERMAGIC para compilar.
    # El Kbuild oficial lo define automaticamente; el build system de OpenSS7 no lo hace.
    # Preservamos -DMODULE (original) + agregamos -DINCLUDE_VERMAGIC.
    COMPAT_KERNEL_MODFLAGS="-DMODULE -DINCLUDE_VERMAGIC"

    make -j"${JOBS}" V=0 \
        CPPFLAGS="${COMPAT_CPPFLAGS}" \
        CFLAGS="${COMPAT_CFLAGS}" \
        KCFLAGS="-Wno-error" \
        EXTRA_CFLAGS="-Wno-error" \
        MODPOST_OPTIONS="${COMPAT_MODPOST_OPTIONS}" \
        KERNEL_MODFLAGS="${COMPAT_KERNEL_MODFLAGS}" \
        2>&1
    log_info "Build completed successfully"

    # Inyectar seccion __versions en los .ko generados.
    # El build de OpenSS7 usa modpost.awk sin -m (modversions), lo que evita
    # 2439 errores de build pero genera .ko sin __versions. Kernels con
    # CONFIG_MODVERSIONS=y (ej. Ubuntu) necesitan esta seccion para cargar el modulo.
    do_inject_modversions
}

do_inject_modversions() {
    log_info "Inyectando seccion __versions en modulos .ko (CONFIG_MODVERSIONS=y)..."

    # Verificar dependencias
    if ! command -v python3 >/dev/null 2>&1; then
        log_warn "python3 no disponible — saltando inyeccion de modversions"
        return 0
    fi
    if ! command -v objcopy >/dev/null 2>&1; then
        log_warn "objcopy no disponible — saltando inyeccion de modversions"
        return 0
    fi

    local KERNEL_SYMVERS="/lib/modules/${KERNEL_VERSION}/build/Module.symvers"
    if [ ! -f "${KERNEL_SYMVERS}" ]; then
        log_warn "Module.symvers del kernel no encontrado en ${KERNEL_SYMVERS} — saltando"
        return 0
    fi

    if python3 /opt/openss7/scripts/inject_modversions.py "${BUILD_DIR}" "${KERNEL_VERSION}"; then
        log_info "Seccion __versions inyectada correctamente en los modulos .ko"
    else
        log_warn "Inyeccion de __versions fallo en algunos modulos (ver errores arriba)"
    fi
}

do_test() {
    log_info "Verificando pre-condiciones del build..."
    cd "${BUILD_DIR}"
    if [ ! -f Makefile ]; then
        log_error "No se encontro build previo en ${BUILD_DIR}."
        log_error "Ejecuta 'python deploy.py build' primero."
        exit 1
    fi

    # ── make check ─────────────────────────────────────────────────────────
    log_info "Ejecutando make check (puede tomar varios minutos)..."
    make check V=0 2>&1
    MAKE_CHECK_EXIT=$?

    # Parsear resultados del log de autotest si existe
    TEST_LOG="${BUILD_DIR}/tests/testsuite.log"
    log_info "=== RESULTADOS DE TESTS ==="
    if [ -f "${TEST_LOG}" ]; then
        grep -E "^(# TOTAL|# PASS|# SKIP|# XFAIL|# FAIL|# XPASS|# ERROR)" "${TEST_LOG}" 2>/dev/null || true
    else
        # Formato alternativo de make check (GNU Automake)
        if [ ${MAKE_CHECK_EXIT} -eq 0 ]; then
            log_info "# RESULT: PASS (make check completado sin errores)"
        else
            log_error "# RESULT: FAIL (make check salio con codigo ${MAKE_CHECK_EXIT})"
        fi
    fi

    # ── Validacion de artefactos ──────────────────────────────────────────
    log_info "=== VALIDACION DE ARTEFACTOS ==="
    ARTIFACT_PASS=0
    ARTIFACT_FAIL=0

    # Contar modulos .ko
    KO_COUNT=$(find "${BUILD_DIR}" -name "*.ko" | wc -l)
    if [ "${KO_COUNT}" -gt 0 ]; then
        log_info "ARTIFACT_PASS: ${KO_COUNT} modulos kernel (.ko) encontrados"
        ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
    else
        log_error "ARTIFACT_FAIL: No se encontraron modulos .ko — build incompleto"
        ARTIFACT_FAIL=$((ARTIFACT_FAIL + 1))
    fi

    # Contar librerias .so
    SO_COUNT=$(find "${BUILD_DIR}" -name "*.so" | wc -l)
    if [ "${SO_COUNT}" -gt 0 ]; then
        log_info "ARTIFACT_PASS: ${SO_COUNT} librerias compartidas (.so) encontradas"
        ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
    else
        log_error "ARTIFACT_FAIL: No se encontraron librerias .so — build incompleto"
        ARTIFACT_FAIL=$((ARTIFACT_FAIL + 1))
    fi

    # Modulos criticos
    for mod in streams specfs; do
        KO_PATH=$(find "${BUILD_DIR}" -name "${mod}.ko" | head -1)
        if [ -n "${KO_PATH}" ]; then
            log_info "ARTIFACT_PASS: ${mod}.ko encontrado en ${KO_PATH}"
            ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
        else
            log_error "ARTIFACT_FAIL: ${mod}.ko NO encontrado — modulo critico faltante"
            ARTIFACT_FAIL=$((ARTIFACT_FAIL + 1))
        fi
    done

    # Binarios criticos
    for bin in strinfo scls; do
        BIN_PATH=$(find "${BUILD_DIR}" -name "${bin}" -type f -perm /111 | head -1)
        if [ -n "${BIN_PATH}" ]; then
            log_info "ARTIFACT_PASS: binario '${bin}' encontrado en ${BIN_PATH}"
            ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
        else
            log_error "ARTIFACT_FAIL: binario '${bin}' NO encontrado"
            ARTIFACT_FAIL=$((ARTIFACT_FAIL + 1))
        fi
    done

    # Verificar vermagic de streams.ko (debe coincidir con el kernel del host)
    STREAMS_KO=$(find "${BUILD_DIR}" -name "streams.ko" | head -1)
    if [ -n "${STREAMS_KO}" ]; then
        VERMAGIC=$(modinfo "${STREAMS_KO}" 2>/dev/null | grep "^vermagic" | awk '{print $2}')
        if [ "${VERMAGIC}" = "${KERNEL_VERSION}" ]; then
            log_info "ARTIFACT_PASS: vermagic de streams.ko coincide con kernel ${KERNEL_VERSION}"
            ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
        else
            log_warn "ARTIFACT_WARN: vermagic '${VERMAGIC}' != kernel '${KERNEL_VERSION}' (puede ser cross-compile)"
        fi
    fi

    # ── Validacion de paquetes DEB ────────────────────────────────────────
    log_info "=== VALIDACION DE PAQUETES DEB ==="
    DEB_COUNT=$(find "${BUILD_DIR}" -name "*.deb" | wc -l)
    if [ "${DEB_COUNT}" -gt 0 ]; then
        log_info "PACKAGE_PASS: ${DEB_COUNT} paquetes .deb encontrados"
        # Validar contenido de cada paquete
        find "${BUILD_DIR}" -name "*.deb" | while read -r deb; do
            PKG_NAME=$(basename "${deb}")
            if dpkg -c "${deb}" > /dev/null 2>&1; then
                log_info "PACKAGE_PASS: ${PKG_NAME} es un .deb valido"
            else
                log_warn "PACKAGE_WARN: ${PKG_NAME} no paso validacion dpkg -c"
            fi
        done
    else
        log_warn "PACKAGE_WARN: No se encontraron .deb (ejecuta 'extract' para generarlos)"
    fi

    # ── Resumen final ─────────────────────────────────────────────────────
    log_info "=== RESUMEN FINAL ==="
    log_info "ARTIFACT_SUMMARY: ${ARTIFACT_PASS} PASS, ${ARTIFACT_FAIL} FAIL"
    log_info "KO_COUNT:${KO_COUNT}  SO_COUNT:${SO_COUNT}  DEB_COUNT:${DEB_COUNT}"

    if [ "${MAKE_CHECK_EXIT}" -ne 0 ] || [ "${ARTIFACT_FAIL}" -gt 0 ]; then
        log_error "Validacion FALLIDA — make_check_exit=${MAKE_CHECK_EXIT}, artifact_fails=${ARTIFACT_FAIL}"
        exit 1
    fi

    log_info "Validacion EXITOSA — todos los artefactos presentes y tests pasaron"
}

do_extract() {
    log_info "Verificando pre-condiciones del build..."
    cd "${BUILD_DIR}"
    if [ ! -f Makefile ]; then
        log_error "No se encontro build previo en ${BUILD_DIR}."
        log_error "Ejecuta 'python deploy.py build' primero."
        exit 1
    fi

    # Crear estructura de directorios organizada
    mkdir -p "${OUTPUT_DIR}/modules"
    mkdir -p "${OUTPUT_DIR}/libs"
    mkdir -p "${OUTPUT_DIR}/bin"
    mkdir -p "${OUTPUT_DIR}/packages"

    # ── Modulos kernel (.ko) ──────────────────────────────────────────────
    log_info "Extrayendo modulos kernel (.ko)..."
    find "${BUILD_DIR}" -name "*.ko" -exec cp {} "${OUTPUT_DIR}/modules/" \;
    KO_COUNT=$(find "${OUTPUT_DIR}/modules" -name "*.ko" | wc -l)
    if [ "${KO_COUNT}" -gt 0 ]; then
        log_info "EXTRACT_PASS: ${KO_COUNT} modulos .ko extraidos a ${OUTPUT_DIR}/modules/"
    else
        log_error "EXTRACT_FAIL: No se encontraron modulos .ko"
    fi

    # ── Librerias compartidas (.so) ───────────────────────────────────────
    log_info "Extrayendo librerias compartidas (.so)..."
    find "${BUILD_DIR}" -name "*.so" -not -path "*/.libs/*" \
        -exec cp {} "${OUTPUT_DIR}/libs/" \; 2>/dev/null
    # Incluir versiones con symlinks (.so.X.Y.Z) desde .libs/
    find "${BUILD_DIR}/.libs" -name "*.so*" -maxdepth 1 \
        -exec cp -P {} "${OUTPUT_DIR}/libs/" \; 2>/dev/null || true
    SO_COUNT=$(find "${OUTPUT_DIR}/libs" -name "*.so*" | wc -l)
    if [ "${SO_COUNT}" -gt 0 ]; then
        log_info "EXTRACT_PASS: ${SO_COUNT} librerias .so extraidas a ${OUTPUT_DIR}/libs/"
    else
        log_error "EXTRACT_FAIL: No se encontraron librerias .so"
    fi

    # ── Binarios ejecutables ──────────────────────────────────────────────
    log_info "Extrayendo binarios..."
    for bin in strinfo scls strace stracer strerr sldebug slconfig; do
        BIN_PATH=$(find "${BUILD_DIR}" -name "${bin}" -type f -perm /111 \
                   -not -path "*/.libs/*" | head -1)
        if [ -n "${BIN_PATH}" ]; then
            cp "${BIN_PATH}" "${OUTPUT_DIR}/bin/"
            log_info "EXTRACT_PASS: binario '${bin}' extraido"
        fi
    done
    BIN_COUNT=$(find "${OUTPUT_DIR}/bin" -type f -perm /111 | wc -l)
    log_info "EXTRACT_PASS: ${BIN_COUNT} binarios extraidos a ${OUTPUT_DIR}/bin/"

    # ── Paquetes DEB (make deb) ───────────────────────────────────────────
    log_info "Generando paquetes DEB (make deb)..."
    make deb 2>&1 || log_warn "make deb fallo (no critico — los artefactos binarios ya estan extraidos)"

    # Buscar .deb generados en el BUILD_DIR y copiar a packages/
    find "${BUILD_DIR}" -name "*.deb" -exec cp {} "${OUTPUT_DIR}/packages/" \; 2>/dev/null || true
    DEB_COUNT=$(find "${OUTPUT_DIR}/packages" -name "*.deb" | wc -l)
    if [ "${DEB_COUNT}" -gt 0 ]; then
        log_info "EXTRACT_PASS: ${DEB_COUNT} paquetes .deb copiados a ${OUTPUT_DIR}/packages/"
    else
        log_warn "EXTRACT_WARN: No se generaron paquetes .deb"
    fi

    # ── Manifest de artefactos ────────────────────────────────────────────
    MANIFEST="${OUTPUT_DIR}/MANIFEST.txt"
    {
        echo "OpenSS7 Build Artifacts — Kernel: ${KERNEL_VERSION} — $(date -u '+%Y-%m-%d %H:%M UTC')"
        echo "=========================================================================="
        echo ""
        echo "--- Kernel Modules (${KO_COUNT}) ---"
        find "${OUTPUT_DIR}/modules" -name "*.ko" | sort | while read -r f; do
            echo "  $(basename "${f}")  $(du -sh "${f}" | cut -f1)"
        done
        echo ""
        echo "--- Shared Libraries (${SO_COUNT}) ---"
        find "${OUTPUT_DIR}/libs" -name "*.so*" | sort | while read -r f; do
            echo "  $(basename "${f}")  $(du -sh "${f}" | cut -f1)"
        done
        echo ""
        echo "--- Binaries (${BIN_COUNT}) ---"
        find "${OUTPUT_DIR}/bin" -type f | sort | while read -r f; do
            echo "  $(basename "${f}")  $(du -sh "${f}" | cut -f1)"
        done
        echo ""
        echo "--- DEB Packages (${DEB_COUNT}) ---"
        find "${OUTPUT_DIR}/packages" -name "*.deb" | sort | while read -r f; do
            echo "  $(basename "${f}")  $(du -sh "${f}" | cut -f1)"
        done
    } > "${MANIFEST}"
    log_info "Manifest generado: ${MANIFEST}"

    # ── Resumen ───────────────────────────────────────────────────────────
    log_info "=== RESUMEN DE EXTRACCION ==="
    log_info "  Modulos .ko : ${KO_COUNT}  → ${OUTPUT_DIR}/modules/"
    log_info "  Libs   .so  : ${SO_COUNT}  → ${OUTPUT_DIR}/libs/"
    log_info "  Binarios    : ${BIN_COUNT}  → ${OUTPUT_DIR}/bin/"
    log_info "  Paquetes DEB: ${DEB_COUNT}  → ${OUTPUT_DIR}/packages/"
    log_info "  Manifest    : ${MANIFEST}"
    log_info "Extraccion completada"
}

case "${ACTION}" in
    build)
        do_build
        ;;
    test)
        do_test
        ;;
    extract)
        do_extract
        ;;
    *)
        log_error "Unknown action: ${ACTION}"
        echo "Usage: docker-build.sh [build|test|extract]"
        exit 1
        ;;
esac
