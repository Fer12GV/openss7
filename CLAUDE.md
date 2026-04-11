# OpenSS7 — Deploy System — Contexto Persistente

## Alcance del Proyecto
@docs/SCOPE.md

## Plan de Desarrollo Activo
@docs/DEVPLAN.md

## Stack Tecnologico
| Capa | Tecnologia | Notas |
|------|-----------|-------|
| Build System | GNU Autotools | configure.ac + Makefile.am |
| Lenguaje Core | C (kernel modules + userspace) | AGPLv3 |
| Deploy Tool | Python 3.x | deploy.py CLI |
| Contenedor Build | Docker (Debian/CentOS base) | Compilacion aislada |
| Orquestacion | docker-compose | Build environment |
| Paquetes | RPM + DEB | Generados dentro de Docker |
| Kernel Modules | .ko (streams, specfs, sctp, etc.) | Requieren kernel headers del host |
| Servicios | systemd | openss7.service, streams.service |
| Tests | autotest (make check) | Suite de tests del proyecto |

## Estructura del Proyecto (Deploy)
```
openss7/
├── CLAUDE.md                   # Contexto persistente (este archivo)
├── Dockerfile                  # Build environment containerizado
├── docker-compose.yml          # Orquestacion del build
├── deploy.py                   # CLI principal de deploy
├── docs/
│   ├── SCOPE.md                # Alcance y decisiones arquitectonicas
│   ├── DEVPLAN.md              # Plan de desarrollo por fases
│   └── *.pdf                   # Cartas de autorizacion
├── .claude/
│   ├── rules/                  # Reglas por disciplina
│   │   ├── docker.md
│   │   ├── python.md
│   │   ├── kernel.md
│   │   ├── testing.md
│   │   └── deploy.md
│   └── skills/
│       ├── continuar/SKILL.md  # Reanudar sesion
│       └── cierre/SKILL.md     # Cerrar sesion
├── src/                        # Codigo fuente OpenSS7 (NO MODIFICAR)
├── tests/                      # Test suites existentes (NO MODIFICAR)
├── configure.ac                # Autotools config (NO MODIFICAR)
├── Makefile.am                 # Autotools build (NO MODIFICAR)
├── debian/                     # Packaging DEB (NO MODIFICAR)
└── rpm/                        # Packaging RPM (NO MODIFICAR)
```

## Comandos Esenciales
```bash
# === Deploy CLI ===
python deploy.py build          # Compila todo en Docker
python deploy.py test           # Ejecuta make check + valida artefactos
python deploy.py extract        # Extrae paquetes compilados
python deploy.py install        # Instala en el host
python deploy.py verify         # Verifica modulos cargados y servicios activos
python deploy.py uninstall      # Desinstala limpiamente

# === Docker directo ===
docker compose up --build       # Build completo con logs
docker compose up --build -d    # Build en background
docker compose down             # Parar todo
docker compose logs -f builder  # Ver logs del build

# === Verificacion manual ===
lsmod | grep streams            # Verificar modulo cargado
systemctl status openss7        # Estado del servicio
strinfo                         # Info de STREAMS
```

## Reglas SIEMPRE Activas
1. **NO MODIFICAR codigo fuente OpenSS7**: src/, tests/, configure.ac, Makefile.am, debian/, rpm/ son intocables
2. **Solo creamos infraestructura de deploy**: Dockerfile, docker-compose.yml, deploy.py y documentacion
3. **Docker como entorno de build**: NUNCA compilar directamente en el host
4. **Idioma**: español para comunicacion, ingles para codigo, español para comentarios en codigo
5. **Python limpio**: PEP8, type hints, docstrings en español
6. **Idempotente**: `python deploy.py build` debe funcionar en cualquier Linux con Docker
7. **Sin secretos en git**: .env en .gitignore si se necesita
8. **Probar antes de cambiar de fase**: verificar sin errores antes de avanzar
9. **Actualizar 3 capas de memoria**: al finalizar sesion o completar fase.

## Niveles de Prueba
| Nivel | Que prueba | Responsabilidad |
|-------|-----------|-----------------|
| 1 - Build | Compilacion, modulos .ko, librerias .so, binarios, make check, paquetes RPM/DEB | **Nosotros (Docker)** |
| 2 - Carga | modprobe/insmod modulos, systemd services, utilidades responden | **Nosotros (Host)** |
| 3 - Protocolos | Funcionalidad SS7/SIGTRAN en red real | **Cliente** |

## Variables de Entorno (si se necesitan)
Archivo `.env` en la raiz del proyecto (no commitear). Ver `.env.example` como plantilla.
```
# Build
TARGET_DISTRO=debian           # debian | centos | fedora
KERNEL_VERSION=auto            # auto-detect o version especifica
BUILD_JOBS=auto                # Numero de jobs paralelos (auto = nproc)

# Install
INSTALL_PREFIX=/usr/local      # Prefijo de instalacion

# VPS Produccion (HostGator)
VPS_HOST=129.121.60.55
VPS_PORT=22022
VPS_USER=root
VPS_PASSWORD=                  # Completar en .env antes de Fase 6
```

## VPS de Produccion
- **Proveedor**: HostGator VPS (Linux)
- **Acceso**: `ssh -p 22022 root@129.121.60.55`
- **Estado**: PRODUCCION — OpenSS7 instalado y verificado (Fase 6 completada 2026-03-30)
- **Kernel VPS**: 5.15.0-173-generic (identico al local)

## Estado Actual del Proyecto
<!-- Actualiza esto al final de cada sesion con /cierre -->
Ultima sesion: 2026-04-11 (sesion 10)
Ultima tarea completada: Diagnostico completo VPS + documento tecnico entregable para Telefonica (docs/09-requerimiento-tecnico-sms-ss7.md, commit fe31c725f) + 3 capas de memoria actualizadas para Fase 8.
Proxima tarea: Fase 8 Bloque 8.1 — Diagnostico adicional VPS (apt history para Asterisk, modinfo SIGTRAN, chan_ss7). Luego 8.2 (reparar strinfo/scls, cargar modulos SIGTRAN). Luego 8.3-8.7 (backend+simulator+UI).
Rama activa: master
Fase actual: Fase 8 EN CURSO (5%)

**Contexto Fase 8 — Simulador SS7 + Frontend SMS tipo WhatsApp Web**:
- Disparador: carta autorizacion Telefonica Colombia (docs/Carta Movistar 1.pdf), firmada 30-marzo-2026
- Estrategia: simulador primero, transicion a datos reales despues cambiando 5 parametros de config
- Decoder real con libreria pycrate (NUNCA mocks ni placeholders — ver memoria feedback_decoder_pycrate.md)
- Arquitectura: 3 contenedores nuevos (openss7-backend FastAPI+pycrate, openss7-simulator pycrate encoder, openss7-ui nginx WhatsApp-like) + los existentes (runtime, portainer)
- Autorizaciones del usuario: Fase A (diagnostico adicional), Fase B (reparar strinfo/scls + cargar modulos SIGTRAN M3UA/SCTP), Fase C (construir simulador+backend+UI) — TODAS AUTORIZADAS
- Hallazgos VPS (2026-04-11): Asterisk 18.10.0 instalado por otro ingeniero del equipo (OK, no cuestionar), strinfo/scls ROTOS (wrappers libtool buscan .libs/ inexistente), modulos SIGTRAN disponibles sin cargar, puerto SCTP 2905 NO escuchando
- Red corporativa usuario: Cliente (VLAN 10.57.20.0/24) -> Switch (10.57.1.2/24) -> Fortinet -> Internet -> VPS (129.121.60.55:22022). IP publica al salir: 190.254.131.168
- NO construir interceptor de terceros. Prueba con movil propio consentido del equipo.
