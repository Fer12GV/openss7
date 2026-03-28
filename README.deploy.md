# OpenSS7 Deploy System

Sistema de despliegue containerizado para OpenSS7 (UNIX STREAMS para Linux).
Automatiza compilacion, pruebas, extraccion, instalacion y verificacion en un solo CLI.

## Requisitos del sistema

| Requisito | Version minima | Verificar |
|-----------|---------------|-----------|
| Python 3 | 3.6+ | `python3 --version` |
| Docker | 20.10+ | `docker --version` |
| docker compose | 2.0+ | `docker compose version` |
| Kernel headers | igual al kernel activo | `ls /lib/modules/$(uname -r)/build` |
| RAM | 4 GB libre para Docker | |

**Instalar kernel headers** (si faltan):
```bash
# Ubuntu/Debian
sudo apt install linux-headers-$(uname -r)

# CentOS/Fedora
sudo yum install kernel-devel-$(uname -r)
```

## Guia rapida (5 minutos)

```bash
# 1. Clonar y entrar al repositorio
git clone <repositorio> openss7
cd openss7

# 2. Compilar todo en Docker (30-60 min la primera vez)
python3 deploy.py build

# 3. Ejecutar tests y validar artefactos
python3 deploy.py test

# 4. Extraer artefactos del contenedor al host
python3 deploy.py extract

# 5. Instalar en el host (requiere root)
sudo python3 deploy.py install

# 6. Verificar instalacion
python3 deploy.py verify

# 7. Desinstalar (si es necesario)
sudo python3 deploy.py uninstall
```

## Referencia de comandos

### `python3 deploy.py build`
Compila OpenSS7 completamente dentro de Docker.

- Detecta automaticamente: version del kernel, numero de CPUs
- Monta los kernel headers del host para compilar los `.ko` para el kernel activo
- Genera: 123 modulos `.ko`, 35 librerias `.so`, 5 binarios
- Inyecta automaticamente la seccion `__versions` en los `.ko` (requerida en kernels con CONFIG_MODVERSIONS=y)
- Tiempo estimado: 30-60 min (primera vez), 5-10 s (incremental)

**Pre-condiciones:**
- Docker instalado y corriendo
- Kernel headers disponibles en `/lib/modules/$(uname -r)/build`

### `python3 deploy.py test`
Ejecuta `make check` dentro del contenedor y valida artefactos.

- Corre el suite de tests de OpenSS7 (autotest)
- Valida presencia de modulos criticos: `streams.ko`, `specfs.ko`
- Valida binarios: `strinfo`, `scls`
- Verifica que el `vermagic` de `streams.ko` coincide con el kernel del host
- Reporta: `ARTIFACT_SUMMARY: N PASS, M FAIL`
- Exit 0 = todo OK, Exit 1 = algo fallo

**Pre-condiciones:** Build completado (`python3 deploy.py build`)

### `python3 deploy.py extract`
Extrae artefactos del contenedor Docker al directorio `build-output/`.

Estructura de salida:
```
build-output/
├── modules/    # 123 modulos .ko
├── libs/       # 35 librerias .so
├── bin/        # 5 binarios (strinfo, scls, strace, strerr, slconfig)
├── packages/   # .deb / .rpm (si se generaron)
└── MANIFEST.txt
```

**Pre-condiciones:** Build completado

### `sudo python3 deploy.py install`
Instala OpenSS7 en el host desde `build-output/`.

- Detecta distro: instala via `dpkg -i` (Debian/Ubuntu) o `rpm -i` (CentOS/Fedora)
- Si no hay paquetes: instalacion manual en `/lib/modules/$(uname -r)/extra/openss7/`
- Ejecuta `depmod -a` y carga `streams` + `specfs` con `modprobe`
- Habilita servicios systemd si existen unit files
- **Requiere root** (`sudo`)

**Pre-condiciones:** Extract completado (`python3 deploy.py extract`)

### `python3 deploy.py verify`
Verifica que OpenSS7 esta correctamente instalado y operativo.

Checks realizados:
- `streams` y `specfs` visibles en `lsmod`
- Servicios `openss7`/`streams` activos (si existen unit files)
- Binarios `strinfo` y `scls` ejecutables
- Directorio de modulos presente en `/lib/modules/$(uname -r)/extra/openss7/`

Reporta PASS/FAIL por cada check. Exit 0 = todo OK.

### `sudo python3 deploy.py uninstall`
Desinstala OpenSS7 completamente del host.

- Detiene y deshabilita servicios systemd
- Descarga modulos: `streams_sctp`, `streams_ip`, `streams`, `specfs` (en ese orden)
- Elimina paquetes (`dpkg -r` / `rpm -e`) si fueron instalados
- Elimina archivos: `/lib/modules/$(uname -r)/extra/openss7/`, `/usr/local/lib/openss7/`, binarios en `/usr/local/bin/`
- Ejecuta `depmod -a` y `ldconfig`
- **Requiere root** (`sudo`)

## Troubleshooting

### `Exec format error` al cargar modulos
El modulo fue compilado sin la seccion `__versions`. Soluciones:
```bash
# Re-compilar (inject_modversions se ejecuta automaticamente)
python3 deploy.py build
python3 deploy.py extract
sudo python3 deploy.py install
```

### `Kernel headers no encontrados`
```bash
sudo apt install linux-headers-$(uname -r)
```

### `Docker no esta corriendo`
```bash
sudo systemctl start docker
```

### `Build falla con OOM (exit 137)`
El build necesita al menos 4 GB de RAM libre. Docker esta configurado con `mem_limit: 4g`.

### `ldconfig: libXXX.so.0 no es un enlace simbolico`
Advertencia cosmética — las librerias instaladas son archivos directos. No afecta el funcionamiento.

### `make deb fallo`
OpenSS7 no soporta `make deb` directamente. Los artefactos binarios se extraen igualmente en `build-output/modules/`, `build-output/libs/` y `build-output/bin/`.

## Compatibilidad probada

| Distro build (Docker) | Kernel host | Estado |
|-----------------------|-------------|--------|
| Ubuntu 22.04 | 5.15.0-173-generic | PASS |

## Niveles de prueba

| Nivel | Que prueba | Responsabilidad |
|-------|-----------|-----------------|
| 1 — Build | Compilacion, modulos .ko, librerias .so, binarios | **Este sistema (Docker)** |
| 2 — Carga | modprobe, servicios systemd, binarios responden | **Este sistema (Host)** |
| 3 — Protocolos | Funcionalidad SS7/SIGTRAN en red real | **Cliente** |

## Flujo completo

```
git clone
    └─> python3 deploy.py build     [Docker]  ~30 min
           └─> python3 deploy.py test      [Docker]  ~10 seg
                  └─> python3 deploy.py extract   [Docker→Host]  ~5 seg
                         └─> sudo python3 deploy.py install   [Host]  ~5 seg
                                └─> python3 deploy.py verify  [Host]  ~2 seg
                                       └─> sudo python3 deploy.py uninstall [Host]
```
