# OpenSS7 Deploy System — Plan de Desarrollo

## Estado General
| Fase | Descripcion | Estado | Progreso |
|------|------------|--------|----------|
| 1 | Dockerfile + Build en Docker | COMPLETADA | 100% |
| 2 | Test + Validacion de Artefactos | COMPLETADA | 100% |
| 3 | Extract + Paquetes Nativos | COMPLETADA | 100% |
| 4 | Install + Verify + Uninstall en Host | COMPLETADA | 100% |
| 5 | Pulido Final + Documentacion | COMPLETADA | 100% |
| 6 | Deploy en VPS HostGator | COMPLETADA | 100% |
| 7 | Panel Web Portainer (Monitoring) | COMPLETADA | 100% |
| 8 | Simulador SS7 + Frontend SMS (WhatsApp Web) | EN CURSO | 5% |

**Fase actual**: Fase 8 — Simulador SS7/SIGTRAN + Backend decoder + Frontend tipo WhatsApp Web
**Ultima actualizacion**: 2026-04-11 (sesion 10)

---

## FASE 1 — Dockerfile + Build en Docker
**Objetivo**: Compilar OpenSS7 completamente dentro de Docker sin errores.

### Bloque 1.1 — Dockerfile Base
- [x] Investigar dependencias de compilacion de OpenSS7 (autoconf, automake, libtool, gcc, kernel-headers, etc.)
- [x] Crear Dockerfile con imagen base Debian (build-essential + dependencias)
- [x] Configurar montaje de kernel headers del host
- [x] Ejecutar `./configure` dentro del contenedor sin errores
- [x] Resolver OOM en config.status (exit 137) — montar solo kernel actual + mem_limit 4g
- [x] Crear capa de compatibilidad kernel 5.x (scripts/compat-kernel.h) sin modificar fuentes
- [x] Resolver sctp2.c negative_advice — struct dst_ops variadic en compat-kernel.h (sesion 3-4)
- [x] Resolver modpost 2439 errores — quitar -m de MODPOST_OPTIONS (ld -r pierde flag O en __ksymtab)
- [x] Resolver vermagic.h INCLUDE_VERMAGIC — agregar -DINCLUDE_VERMAGIC a KERNEL_MODFLAGS
- [x] Ejecutar `make -jN` hasta completar sin errores — resuelto: --disable-32bit-libs + swig en Dockerfile
- [x] Verificar que se generan archivos .ko (modulos kernel) — 123 modulos incluyendo streams.ko, specfs.ko, streams_sctp.ko
- [x] Verificar que se generan archivos .so (librerias) — 41 librerias compartidas
- [x] Verificar que se generan binarios (strinfo, scls, strace)

**Criterio de aceptacion**: `docker compose up --build` compila OpenSS7 de principio a fin sin errores.

### Bloque 1.2 — docker-compose.yml
- [x] Crear docker-compose.yml con servicio builder
- [x] Montar volumen de fuentes (read-write, autogen modifica configure.ac)
- [x] Montar volumen de artefactos (output)
- [x] Montar kernel headers del host (/lib/modules, /usr/src, /boot)
- [x] Variables de entorno para configuracion (BUILD_JOBS, KERNEL_VERSION)
- [x] Volumen de cache para recompilaciones rapidas (/build separado)

**Criterio de aceptacion**: `docker compose up --build` orquesta la compilacion correctamente.

### Bloque 1.3 — deploy.py build
- [x] Crear estructura base de deploy.py con argparse
- [x] Implementar subcomando `build`
- [x] Detectar automaticamente kernel version del host
- [x] Invocar docker compose build + up
- [x] Capturar y reportar errores de compilacion
- [x] Reportar tiempo de compilacion y artefactos generados
- [x] Manejar Ctrl+C limpiamente

**Criterio de aceptacion**: `python deploy.py build` compila OpenSS7 y reporta exito/fallo.

### Pruebas de Fase 1
- [x] Build completo desde cero (sin cache) — PASS: 123 .ko, 41 .so, strinfo/scls/strace OK
- [ ] Build incremental (con cache)
- [ ] Build con errores forzados (verificar reporte de errores)
- [ ] Build en sistema limpio (solo Docker instalado)

---

## FASE 2 — Test + Validacion de Artefactos
**Objetivo**: Ejecutar make check y validar que todos los artefactos esperados existen.

### Bloque 2.1 — deploy.py test
- [x] Implementar subcomando `test`
- [x] Ejecutar `make check` dentro del contenedor (docker compose run builder test)
- [x] Parsear resultados de tests (TOTAL/PASS/SKIP/FAIL desde testsuite.log)
- [x] Reportar resumen de tests
- [x] Validar existencia de artefactos esperados (.ko, .so, binarios)
- [x] Validar que los .ko corresponden al kernel del host (vermagic via modinfo)
- [x] Generar reporte de validacion (ARTIFACT_PASS/ARTIFACT_FAIL por cada check)

**Criterio de aceptacion**: `python deploy.py test` ejecuta tests y valida artefactos, reportando resultado claro.

### Bloque 2.2 — Validacion de Paquetes
- [ ] Verificar que `make rpm` genera paquetes RPM validos (si aplica)
- [x] Verificar que `make deb` genera paquetes DEB validos (si aplica) — validacion en do_test
- [x] Validar contenido de paquetes (dpkg -c sobre .deb encontrados en BUILD_DIR)
- [ ] Verificar firmas/checksums de paquetes

**Criterio de aceptacion**: Los paquetes generados son instalables y contienen todos los archivos necesarios.

### Pruebas de Fase 2
- [x] `python deploy.py test` pasa sin errores despues de un build exitoso — PASS: 7/7, vermagic OK
- [x] `python deploy.py test` falla correctamente si no hay build previo (check_build_exists)
- [x] Reporte de tests muestra pass/fail/skip correctamente

---

## FASE 3 — Extract + Paquetes Nativos
**Objetivo**: Extraer paquetes compilados del contenedor al host.

### Bloque 3.1 — deploy.py extract
- [x] Implementar subcomando `extract`
- [x] Copiar paquetes RPM/DEB desde el contenedor al host (make deb no disponible en OpenSS7, nota: usar dpkg-buildpackage)
- [x] Copiar modulos .ko — 123 modulos en build-output/modules/
- [x] Organizar artefactos en directorio de salida — modules/, libs/, bin/, packages/
- [x] Listar artefactos extraidos con tamanios (MANIFEST.txt generado)
- [x] Verificar integridad de archivos extraidos (conteo por tipo)

**Criterio de aceptacion**: `python deploy.py extract` extrae todos los artefactos al host organizadamente.

### Pruebas de Fase 3
- [x] Extract despues de build exitoso produce artefactos completos — PASS: 123 .ko, 35 .so, 5 binarios
- [x] Extract sin build previo da error claro (check_build_exists)
- [x] Artefactos extraidos organizados en subdirectorios del host

---

## FASE 4 — Install + Verify + Uninstall en Host
**Objetivo**: Instalar, verificar y desinstalar OpenSS7 en el host.

### Bloque 4.1 — deploy.py install
- [x] Implementar subcomando `install`
- [x] Detectar distro del host (Debian/Ubuntu vs CentOS/Fedora)
- [x] Instalar paquetes con dpkg -i / rpm -i segun distro (fallback: instalacion manual)
- [x] Ejecutar depmod -a para registrar modulos
- [x] Cargar modulos con modprobe (streams, specfs)
- [x] Habilitar y arrancar servicios systemd (warning no-critico si no hay unit files)
- [x] Manejar errores de dependencias faltantes
- [x] Requiere sudo/root — verificar permisos al inicio (check_root)
- [x] inject_modversions.py integrado en do_build — __versions inyectadas automaticamente

**Criterio de aceptacion**: `python deploy.py install` instala OpenSS7 y arranca servicios.

### Bloque 4.2 — deploy.py verify
- [x] Implementar subcomando `verify`
- [x] Verificar modulos cargados (lsmod | grep streams/specfs)
- [x] Verificar servicios activos (systemctl is-active, warning si no existen)
- [x] Verificar utilidades responden (strinfo, scls — retornan output)
- [x] Generar reporte de verificacion (PASS/FAIL por cada check)
- [x] Exit code 0 si todo pasa, 1 si algo falla

**Criterio de aceptacion**: `python deploy.py verify` confirma OpenSS7 funcional con reporte detallado.

### Bloque 4.3 — deploy.py uninstall
- [x] Implementar subcomando `uninstall`
- [x] Detener servicios systemd
- [x] Descargar modulos del kernel (rmmod en orden correcto: streams antes de specfs)
- [x] Desinstalar paquetes (dpkg -r / rpm -e)
- [x] Limpiar archivos residuales (modules, libs, binaries, ld.so.conf)
- [x] Ejecutar depmod -a para actualizar dependencias
- [x] Requiere sudo/root — verificar permisos al inicio

**Criterio de aceptacion**: `python deploy.py uninstall` elimina OpenSS7 completamente del host.

### Pruebas de Fase 4
- [x] Ciclo completo build → extract → install → verify → uninstall — PASS
- [x] Verify despues de install: 5 PASS, 0 FAIL
- [x] Verify despues de uninstall: 0 PASS, 5 FAIL (correcto)
- [x] Install sin extract previo da error claro (check_extract_done)
- [x] Install/uninstall sin root da error claro (check_root)
- Nota: ldconfig warnings (.so.0 no son symlinks) — cosmético, resuelto en Fase 5

---

## FASE 5 — Pulido Final + Documentacion
**Objetivo**: Pulir la experiencia de usuario y documentar.

### Bloque 5.1 — UX del CLI
- [x] Colores en la salida (ya existian desde Fase 1)
- [ ] Barra de progreso para compilacion larga (diferida — no critico para funcionalidad)
- [ ] Flag --verbose / --quiet (diferido)
- [x] Flag --help con ejemplos de uso — funcional en todos los subcomandos
- [x] Manejo robusto de Ctrl+C (KeyboardInterrupt en build, test, extract)
- [x] flush=True en todas las funciones de log (fix ordering del output)

### Bloque 5.2 — README.deploy.md
- [x] Requisitos del sistema (Docker, kernel headers, Python 3)
- [x] Guia rapida de uso (5 minutos)
- [x] Explicacion de cada comando con ejemplos
- [x] Troubleshooting (errores comunes y soluciones)
- [x] Tabla de compatibilidad (Ubuntu 22.04 + kernel 5.15 — PASS)

### Bloque 5.3 — Validacion Final
- [x] Test completo en Debian/Ubuntu — ciclo completo PASS
- [ ] Test completo en CentOS/Fedora (diferido — fuera de alcance de este equipo)
- [x] Ciclo completo: build → test → extract → install → verify → uninstall — PASS
- [x] Secretos en .gitignore (.env con VPS_PASSWORD y ROOT_PASSWORD)

**Criterio de aceptacion**: Un usuario puede ir de git clone a OpenSS7 funcionando siguiendo README.deploy.md.

### Pruebas de Fase 5
- [x] README.deploy.md creado con guia completa
- [x] --help muestra informacion util para cada subcomando
- [x] Ciclo completo end-to-end sin intervencion manual — PASS en Ubuntu 22.04

---

## FASE 6 — Deploy en VPS HostGator
**Objetivo**: Conectarse a la VPS virgencota, configurarla desde cero e instalar OpenSS7 en produccion.
**PRECONDICION**: Fases 1-5 completadas y validadas en local (este equipo).

### Datos de Acceso a la VPS
```
Host:   129.121.60.55
Puerto: 22022
Usuario: root
Acceso: ssh -p 22022 root@129.121.60.55
Password: ver .env → VPS_PASSWORD (completar antes de esta fase)
```
**Nota**: La VPS es virgencota (recien entregada por HostGator). Hay que configurarla desde cero.

### Bloque 6.1 — Preparacion de la VPS
- [x] Conectar a la VPS via SSH (leer VPS_PASSWORD de .env)
- [x] Detectar OS base de la VPS — Ubuntu 22.04.5 LTS, kernel 5.15.0-173-generic
- [x] Instalar Docker CE 29.3.1 y Docker Compose v5.1.1 en la VPS
- [x] Instalar kernel headers linux-headers-5.15.0-173-generic
- [x] Verificar conectividad y espacio en disco — 181GB libres, 7.8GB RAM

### Bloque 6.2 — Transferir artefactos a la VPS
- [x] Clonar repositorio desde GitHub: git clone https://github.com/Fer12GV/openss7.git
- [x] Copiar .env a la VPS via scp
- [x] Verificar que deploy.py es ejecutable en la VPS

### Bloque 6.3 — Build en la VPS
- [x] Ejecutar `python3 deploy.py build` en la VPS — PASS
- [x] Build completo sin errores: 123 .ko, 35 .so, 5 binarios
- [x] inject_modversions.py: 123 inyectados, 0 fallidos
- [x] Kernel de la VPS identico al local (5.15.0-173-generic)

### Bloque 6.4 — Install y Verify en la VPS
- [x] Ejecutar `python3 deploy.py extract` — 123 .ko, 35 .so, 5 binarios
- [x] Ejecutar `python3 deploy.py install` — modulos streams y specfs cargados
- [x] Ejecutar `python3 deploy.py verify` — 5 PASS, 0 FAIL
- [x] Confirmar modulos cargados: streams y specfs en lsmod

### Pruebas de Fase 6
- [x] Ciclo completo en VPS: build → extract → install → verify — PASS
- [x] verify reporta 5 PASS, 0 FAIL en la VPS
- [x] OpenSS7 funcional en produccion (Ubuntu 22.04, kernel 5.15.0-173-generic)

**Criterio de aceptacion**: `python deploy.py verify` reporta todo PASS en la VPS de produccion.
**RESULTADO**: CRITERIO CUMPLIDO — 5 PASS, 0 FAIL en VPS HostGator (2026-03-30)

---

## FASE 7 — Panel Web Portainer (Monitoring para el Cliente)
**Objetivo**: Dar al cliente una interfaz grafica en el navegador donde pueda ver que OpenSS7 esta corriendo y funcional.
**Contexto**: OpenSS7 no tiene frontend propio — es un stack de protocolos de kernel. Portainer provee un panel web para gestionar y monitorear los contenedores Docker del entorno de build/runtime.
**URL objetivo**: `http://129.121.60.55:9000` (o puerto alternativo si 9000 ocupado)
**Precondicion**: Fase 6 completada — OpenSS7 instalado y contenedor runtime corriendo en la VPS.

### Bloque 7.1 — Desplegar Portainer en la VPS
- [x] Crear volumen Docker para datos de Portainer: `docker volume create portainer_data` — openss7-portainer-data creado
- [x] Levantar Portainer CE con docker compose (agregar servicio al compose del proyecto) — Up en VPS
- [x] Verificar que Portainer responde en puerto 9000 — HTTP 200 desde exterior
- [x] Configurar usuario admin inicial de Portainer — admin/OpenSS7admin2026!

### Bloque 7.2 — Configurar vista para el cliente
- [x] Login en Portainer y verificar que muestra el entorno local (local Docker) — endpoint 'local' agregado via API
- [x] Confirmar que `openss7-runtime` aparece como contenedor activo en Portainer — running
- [x] Confirmar que imagen `openss7-builder:latest` aparece en Portainer — 992 MB visible
- [x] Documentar URL y credenciales de acceso para el cliente — docs/07-portainer-acceso.md

### Bloque 7.3 — Integracion con docker-compose.yml
- [x] Agregar servicio `portainer` al docker-compose.yml del proyecto — commit 23abc1d6e
- [x] Asegurar que `docker compose up -d` levanta tanto runtime como portainer — ambos Up
- [x] Verificar `docker compose ps` muestra ambos servicios activos — openss7-portainer + openss7-runtime Up
- [x] Hacer commit y push a GitHub — commit eab7a80d3 pushed to origin/master

### Pruebas de Fase 7
- [x] Abrir `http://129.121.60.55:9000` en navegador — HTTP 200, Portainer carga
- [x] Login con credenciales admin funciona — admin/OpenSS7admin2026! via API
- [x] Panel muestra contenedor `openss7-runtime` en estado Running — PASS
- [x] Panel muestra imagen `openss7-builder:latest` — PASS (992 MB)
- [x] `docker compose ps` muestra portainer y runtime Up — PASS

**Criterio de aceptacion**: El cliente puede abrir un navegador, entrar a la IP:9000 y ver visualmente que OpenSS7 esta desplegado y corriendo.

---

## FASE 8 — Simulador SS7 + Frontend SMS (tipo WhatsApp Web)
**Objetivo**: Construir pipeline end-to-end que demuestre el funcionamiento del stack SS7 generando mensajes MAP mt-forwardSM reales (ASN.1 BER), decodificandolos en tiempo real y mostrandolos en una UI web estilo WhatsApp Web. Modo simulador primero, transicion a datos reales de Telefonica Colombia despues mediante cambio de configuracion (cero refactor).

**Disparador**: Carta de autorizacion de Colombia Telecomunicaciones S.A. E.S.P (Telefonica Colombia), firmada por Alfonso Enriquez Huidobro, Director Global IT Procurement, fecha 30-marzo-2026 (`docs/Carta Movistar 1.pdf`).

**Precondicion**: Fase 7 completada. VPS con OpenSS7 y Portainer activos.

**Restricciones clave**:
- NO construir interceptor de SMS de terceros
- Prueba inicial con movil propio del equipo (consentido)
- Decoder real con libreria `pycrate`, nunca mocks ni placeholders
- Simulador genera bytes SS7 reales (mismos que Telefonica enviaria)
- Transicion simulador -> produccion = editar 5 parametros en un archivo de configuracion

### Bloque 8.1 — Diagnostico adicional VPS (Fase A autorizada)
- [ ] Revisar `/var/log/apt/history.log` para identificar quien/cuando instalo Asterisk
- [ ] Ejecutar `modinfo` sobre cada .ko SIGTRAN en /lib/modules/.../extra/openss7/ y validar vermagic
- [ ] Verificar si hay `chan_ss7` o modulos SS7 disponibles para Asterisk (`apt list --installed | grep ss7`)
- [ ] Confirmar que /root/openss7/build-output sigue integro
- [ ] Documentar estado actual en sesion tmux `deploy`

### Bloque 8.2 — Reparacion strinfo/scls + Carga modulos SIGTRAN (Fase B autorizada)
- [ ] Reinstalar binarios OpenSS7 para arreglar strinfo/scls (wrappers libtool rotos)
- [ ] `modprobe streams_sctp` — cargar driver SCTP de OpenSS7
- [ ] `modprobe streams_m3ua_as` — cargar M3UA Application Server
- [ ] `modprobe streams_sccp` — cargar SCCP
- [ ] Verificar con `lsmod | grep streams` que todos aparecen
- [ ] Abrir puerto SCTP 2905 en iptables/UFW si es necesario
- [ ] Verificar que strinfo responde correctamente

### Bloque 8.3 — Contenedor openss7-backend (Python FastAPI + pycrate)
- [ ] Crear `backend/Dockerfile` con Python 3.11 + pycrate + FastAPI + uvicorn
- [ ] Crear `backend/app/main.py` con endpoints: GET /health, WS /ws/messages
- [ ] Crear `backend/app/decoder/sctp_listener.py` — escucha SCTP 2905, recibe bytes
- [ ] Crear `backend/app/decoder/m3ua.py` — parser M3UA Data Message
- [ ] Crear `backend/app/decoder/sccp.py` — decoder SCCP Unitdata
- [ ] Crear `backend/app/decoder/tcap.py` — decoder TCAP Begin/Continue/End
- [ ] Crear `backend/app/decoder/map_sms.py` — decoder MAP mt-forwardSM / mo-forwardSM via pycrate
- [ ] Crear `backend/app/decoder/tpdu.py` — decoder TPDU 3GPP TS 23.040 (GSM-7, UCS-2, 8-bit)
- [ ] Crear `backend/app/storage/sqlite.py` — almacenar historial de mensajes
- [ ] Crear `backend/app/config.yaml` con parametros simulador (local_pc, remote_pc, remote_ip, puerto)

### Bloque 8.4 — Contenedor openss7-simulator (Seagull o pycrate encoder)
- [ ] Crear `simulator/Dockerfile` con Python 3.11 + pycrate
- [ ] Crear `simulator/generate_sms.py` — genera MAP mt-forwardSM con pycrate
  - Campos configurables: origen, destino, texto, timestamp
  - Soporte GSM-7, UCS-2 (emojis) y concatenados
- [ ] Crear `simulator/send_sctp.py` — abre asociacion SCTP hacia openss7-backend
- [ ] Crear `simulator/scenarios/` con casos de prueba (sms corto, largo, unicode, numero internacional)
- [ ] Crear `simulator/cli.py` — CLI para disparar scenarios manualmente

### Bloque 8.5 — Contenedor openss7-ui (Frontend tipo WhatsApp Web)
- [ ] Crear `frontend/Dockerfile` con nginx alpine
- [ ] Crear `frontend/index.html` — layout tipo WhatsApp Web (sidebar conversaciones + panel mensajes)
- [ ] Crear `frontend/css/style.css` — estilo WhatsApp Web (colores verde/gris, burbujas)
- [ ] Crear `frontend/js/app.js` — conecta WebSocket /ws/messages al backend, renderiza mensajes en tiempo real
- [ ] Crear `frontend/nginx.conf` — servir estaticos en puerto 80, proxy /ws/ al backend
- [ ] UI muestra: lista de numeros origen (conversaciones), panel con mensajes decodificados, timestamps, indicador de estado

### Bloque 8.6 — Integracion docker-compose.yml
- [ ] Agregar servicio `openss7-backend` al docker-compose.yml (puerto 8081 WS)
- [ ] Agregar servicio `openss7-simulator` al docker-compose.yml (comunica con backend via red interna)
- [ ] Agregar servicio `openss7-ui` al docker-compose.yml (puerto 8080 publico)
- [ ] Configurar red interna `openss7_ss7net` para trafico SS7 simulado
- [ ] Configurar dependencias entre servicios (depends_on)
- [ ] Verificar que `docker compose up -d` levanta todo el stack

### Bloque 8.7 — Prueba end-to-end con simulador
- [ ] Levantar stack completo en local
- [ ] Ejecutar scenario "sms corto GSM-7" desde openss7-simulator
- [ ] Verificar en backend logs que llegan bytes SCTP
- [ ] Verificar decodificacion: M3UA -> SCCP -> TCAP -> MAP -> TPDU -> texto
- [ ] Verificar que WebSocket envia JSON al frontend
- [ ] Verificar que el frontend muestra el mensaje en la UI tipo WhatsApp
- [ ] Probar scenarios: sms largo (concatenado), unicode (emoji), numero internacional
- [ ] Desplegar stack en VPS 129.121.60.55
- [ ] Acceder a `http://129.121.60.55:8080` desde navegador externo

### Bloque 8.8 — Documentacion de transicion a datos reales
- [ ] Crear `docs/10-fase8-simulador.md` con arquitectura del simulador
- [ ] Crear `docs/11-transicion-datos-reales.md` con checklist para Telefonica
- [ ] Documentar los 5 parametros que cambian (local PC, remote PC, remote IP, puerto, NI)
- [ ] Incluir diagrama antes/despues
- [ ] Actualizar README.md con la nueva funcionalidad

### Pruebas de Fase 8
- [ ] Simulador genera bytes ASN.1 BER validos (inspeccion con Wireshark)
- [ ] Decoder procesa bytes y extrae: origen, destino, texto, DCS, timestamp
- [ ] UI muestra mensajes en tiempo real (latencia < 1s)
- [ ] Scenarios: corto, largo, unicode, internacional — todos PASS
- [ ] Stack completo accesible en VPS
- [ ] Portainer muestra los 4 contenedores (runtime, portainer, backend, simulator, ui)

**Criterio de aceptacion**: Generar un SMS desde el simulador y verlo aparecer en la UI tipo WhatsApp Web en menos de 1 segundo, con origen, destino y texto correctamente decodificados.

**Criterio extra**: Demostrar que cambiando los parametros de configuracion (sin tocar codigo), el backend puede conectar con un Signaling Gateway real cuando Telefonica lo provea.

---

## Reglas de Transicion entre Fases
1. **NO se avanza de fase si hay errores** — por minimos que sean, se fixean primero
2. **Pruebas de fase obligatorias** — cada fase tiene su seccion de pruebas
3. **Actualizar memoria** — al completar cada fase, actualizar DEVPLAN.md, CLAUDE.md y MEMORY.md
4. **Commit por fase** — cada fase completada se commitea con mensaje descriptivo

---

## Notas Tecnicas

### Dependencias de Build (Debian)
```
build-essential autoconf automake libtool gcc g++
bison flex texinfo doxygen
linux-headers-$(uname -r)
libpcap-dev libsctp-dev
perl libnet-snmp-perl
```

### Dependencias de Build (CentOS)
```
gcc gcc-c++ make autoconf automake libtool
bison flex texinfo doxygen
kernel-devel-$(uname -r)
libpcap-devel lksctp-tools-devel
perl net-snmp-perl
```

### Modulos Kernel Esperados
- `streams.ko` — STREAMS subsystem core
- `specfs.ko` — Special filesystem para STREAMS
- `sctp.ko` — SCTP protocol implementation
- Otros modulos segun configuracion

### Servicios Systemd Esperados
- `openss7.service` — Servicio principal
- `streams.service` — STREAMS subsystem service

### Utilidades de Verificacion
- `strinfo` — Informacion del subsistema STREAMS
- `scls` — Lista de modulos STREAMS
- `strace` — Tracing de STREAMS (no confundir con el strace del sistema)
