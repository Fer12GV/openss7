# Arquitectura del Sistema de Despliegue

> **Nivel:** Intermedio
> **Objetivo:** Comprender cómo están organizados todos los componentes del sistema y por qué se tomaron las decisiones de diseño que se tomaron.

---

## 1. Visión general

El sistema tiene tres capas bien diferenciadas:

```
┌─────────────────────────────────────────────────────────┐
│                   CAPA 1: CONTROL                        │
│                   deploy.py (CLI Python)                 │
│   build │ test │ extract │ install │ verify │ uninstall  │
└──────────────────────────┬──────────────────────────────┘
                           │ subprocess / docker compose
           ┌───────────────┴───────────────┐
           ▼                               ▼
┌──────────────────┐             ┌──────────────────────┐
│  CAPA 2: BUILD   │             │   CAPA 3: RUNTIME    │
│  Docker Container │             │   Host Linux         │
│                  │             │                      │
│  autotools build │             │  kernel modules (.ko)│
│  make -j$(nproc) │             │  systemd services    │
│  inject_modver.. │             │  /dev/streams/       │
│  123 .ko output  │             │  strinfo / scls      │
└──────────────────┘             └──────────────────────┘
```

**Regla fundamental:** El build ocurre en Docker, pero los módulos de kernel se cargan en el host real. Nunca al revés.

---

## 2. Componentes del sistema

### 2.1 deploy.py — El orquestador

Un único archivo Python (~500 líneas) con 6 subcomandos. Sin dependencias externas — solo Python stdlib.

```
deploy.py
├── cmd_build()       → docker compose up --build
├── cmd_test()        → docker compose run --rm builder test
├── cmd_extract()     → docker compose run --rm builder extract
├── cmd_install()     → modprobe + depmod + systemctl (en host)
├── cmd_verify()      → lsmod + systemctl + binarios
└── cmd_uninstall()   → rmmod + cleanup + depmod
```

**¿Por qué un solo archivo?** Facilita la distribución — un sysadmin puede copiar deploy.py a cualquier servidor con Python 3 y funciona sin instalar nada.

### 2.2 Dockerfile — El entorno de build

Basado en Ubuntu 22.04 con todas las dependencias de compilación. La imagen incluye:

```dockerfile
# Dependencias esenciales
build-essential autoconf automake libtool gcc g++
bison flex texinfo doxygen swig
libpcap-dev libsctp-dev libperl-dev
# Para post-procesado de módulos
python3 binutils (objcopy, readelf)
```

El Dockerfile **no compila** — solo instala herramientas. La compilación ocurre cuando se ejecuta el contenedor.

### 2.3 docker-compose.yml — La orquestación

Define cómo montar el entorno de build:

```yaml
volumes:
  - .:/opt/openss7           # código fuente (lectura/escritura)
  - /lib/modules/X.Y.Z:/lib/modules/X.Y.Z  # headers del kernel host
  - /usr/src:/usr/src        # fuentes del kernel host
  - /boot:/boot              # System.map, config del kernel
  - openss7-build-cache:/build  # caché para builds incrementales
```

**El montaje de kernel headers es crítico:** Los módulos .ko deben compilarse contra exactamente el mismo kernel que los va a cargar. Si el host tiene kernel 5.15.0-173, los headers montados son de 5.15.0-173.

### 2.4 docker-build.sh — El script de build dentro del contenedor

Ejecutado como entrypoint del contenedor. Contiene las funciones:

```bash
do_build()     # ./configure + make + inject_modversions
do_test()      # make check + validación de artefactos
do_extract()   # organizar output en modules/ libs/ bin/
```

### 2.5 scripts/compat-kernel.h — Capa de compatibilidad

Header creado para resolver 30+ incompatibilidades del código C de OpenSS7 con kernels Linux 5.x. Incluido automáticamente durante la compilación via `CFLAGS`. No modifica el código fuente de OpenSS7.

Ejemplos de fixes incluidos:

```c
// Kernel 5.14+: __state en lugar de state
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5,14,0)
#define set_task_state(tsk, state_value) \
    WRITE_ONCE((tsk)->__state, (state_value))
#endif

// Kernel 5.10+: get_fs/set_fs eliminados
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5,10,0)
static inline mm_segment_t get_fs(void) { return KERNEL_DS; }
static inline void set_fs(mm_segment_t seg) { (void)seg; }
#endif
```

### 2.6 scripts/inject_modversions.py — El fix clave

Script Python que inyecta la sección `__versions` en los módulos .ko después del build. Ver explicación completa en [05-profundidad-tecnica.md](05-profundidad-tecnica.md).

---

## 3. Flujo de datos detallado

### Fase build

```
deploy.py build
    │
    ├─ detecta kernel: uname -r → "5.15.0-173-generic"
    ├─ detecta CPUs: nproc → 8
    │
    └─ docker compose up --build
            │
            ▼
        Contenedor Ubuntu 22.04
            │
            ├─ git config safe.directory (permisos)
            ├─ cd /opt/openss7
            ├─ ./autogen.sh
            ├─ ./configure
            │     --disable-java
            │     --disable-32bit-libs
            │     --with-k-release=5.15.0-173-generic
            │     KERNEL_MODFLAGS="-DMODULE -DINCLUDE_VERMAGIC"
            │
            ├─ make -j8
            │     compila 123 .ko, 41 .so, 5 binarios
            │
            └─ inject_modversions.py
                  lee Module.symvers del kernel
                  inyecta __versions en cada .ko
                  resultado: 123 inyectados, 0 fallos
```

### Fase install

```
deploy.py install
    │
    ├─ check_root() → debe ser root
    ├─ check_extract_done() → build-output/modules/*.ko debe existir
    │
    ├─ copia .ko → /lib/modules/5.15.0-173/extra/openss7/
    ├─ copia .so → /usr/local/lib/openss7/
    ├─ copia binarios → /usr/local/bin/
    │
    ├─ ldconfig -n /usr/local/lib/openss7
    ├─ ldconfig (global)
    ├─ depmod -a (reconstruye árbol de dependencias de módulos)
    │
    ├─ modprobe specfs
    ├─ modprobe streams
    │
    └─ systemctl enable/start openss7 (si existe unit file)
```

---

## 4. Decisiones de diseño

### ¿Por qué no compilar directamente en el host?

1. **Reproducibilidad** — el entorno de build es 100% definido en el Dockerfile
2. **Aislamiento** — no contamina el host con dependencias de compilación
3. **Portabilidad** — funciona en cualquier distribución que tenga Docker
4. **Reversibilidad** — si el build falla, no hay efectos secundarios en el host

### ¿Por qué no instalar los módulos dentro del contenedor?

Los módulos `.ko` son código que corre dentro del **kernel del sistema operativo**. El contenedor Docker no tiene acceso al kernel del host — comparte el mismo kernel pero no puede cargarlo módulos. La carga con `modprobe` debe hacerse en el host real.

### ¿Por qué Python stdlib y sin dependencias?

Un servidor de producción en una operadora puede estar completamente aislado de internet. Si deploy.py requiriera `pip install requests`, fallaría. Con solo stdlib de Python 3, funciona en cualquier Linux moderno sin instalar nada adicional.

### ¿Por qué inject_modversions.py en lugar de arreglar el build?

El build original de OpenSS7 usa `modpost.awk` propio sin el flag `-m` (que generaría `__versions`). Agregar `-m` causaba 2439 errores de enlazado por un bug de `ld -r` con la tabla de símbolos del kernel. La solución más segura fue post-procesar los .ko sin tocar el sistema de build de OpenSS7.

---

## 5. Estructura de directorios

```
openss7/
├── deploy.py                   # CLI principal — modificado por este proyecto
├── Dockerfile                  # Entorno de build — creado por este proyecto
├── docker-compose.yml          # Orquestación — creado por este proyecto
├── .env                        # Variables secretas (no en git)
├── .env.example                # Plantilla pública
├── .dockerignore               # Exclusiones de imagen Docker
├── .gitignore                  # Exclusiones de git
│
├── scripts/                    # Scripts de build
│   ├── docker-build.sh         # Entrypoint del contenedor
│   ├── compat-kernel.h         # Capa de compatibilidad kernel 5.x
│   └── inject_modversions.py   # Inyección post-build de __versions
│
├── docs/                       # Documentación (este directorio)
│   ├── README.md
│   ├── 01-openss7-y-ss7.md
│   ├── 02-arquitectura.md      ← estás aquí
│   ├── 03-guia-local.md
│   ├── 04-guia-vps.md
│   ├── 05-profundidad-tecnica.md
│   └── 06-diagramas-mermaid.md
│
├── build-output/               # Artefactos extraídos (generado por extract)
│   ├── modules/                # 123 archivos .ko
│   ├── libs/                   # 35 librerías .so
│   ├── bin/                    # strinfo, scls, strace, strerr, slconfig
│   ├── packages/               # .deb/.rpm si se generaron
│   └── MANIFEST.txt            # Inventario con tamaños
│
└── src/                        # Código fuente OpenSS7 ← NO MODIFICAR
    configure.ac                # Build system ← NO MODIFICAR
    Makefile.am                 # Build rules ← NO MODIFICAR
```

---

## 6. Seguridad y permisos

| Operación | Requiere root | Razón |
|-----------|---------------|-------|
| build | No | Docker maneja sus propios permisos |
| test | No | Solo lectura dentro del contenedor |
| extract | No | Escribe en build-output/ local |
| install | **Sí** | Escribe en /lib/modules/ y ejecuta modprobe |
| verify | No | Solo lectura de lsmod y binarios |
| uninstall | **Sí** | Ejecuta rmmod y limpia /lib/modules/ |

**El usuario debe estar en el grupo `docker`** para ejecutar build/test/extract sin sudo.

---

*Siguiente: [Guía de instalación local →](03-guia-local.md)*
