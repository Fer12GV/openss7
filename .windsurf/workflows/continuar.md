---
description: Reanudar el desarrollo de OpenSS7 Deploy System desde donde quedó la última sesión
---

# Workflow: Continuar Desarrollo

Este workflow permite a cualquier modelo en WindSurf retomar el trabajo del proyecto OpenSS7 desde donde quedó la última sesión, con contexto completo.

## Pasos a seguir

### 1. Leer contexto persistente principal
- Leer `CLAUDE.md` en la raíz del proyecto para obtener:
  - Stack tecnológico
  - Comandos esenciales
  - Reglas SIEMPRE activas
  - Estado actual del proyecto
  - VPS de producción

### 2. Revisar plan de desarrollo activo
- Leer `docs/DEVPLAN.md` para identificar:
  - Tabla de estado de fases (buscar la primera fase NO marcada como COMPLETADA)
  - Tareas pendientes en la fase actual (marcadas con `- [ ]`)
  - Último bloque de tareas en progreso
  - Criterios de aceptación de la fase

### 3. Revisar alcance y decisiones arquitectónicas
- Leer `docs/SCOPE.md` para refrescar:
  - Alcance del proyecto (solo deploy, NO protocolos)
  - Arquitectura del sistema
  - Decisiones arquitectónicas clave
  - Lo que entregamos vs lo que NO incluimos

### 4. Recuperar memorias persistentes de WindSurf
Las memorias persistentes ya están cargadas automáticamente en el contexto de WindSurf. Verificar que incluyen:
- Reglas de deploy, docker, kernel, python, testing
- Feedbacks de issues resueltos (compat header, modversions, etc.)
- Estado del proyecto y VPS
- Perfil del usuario Fernando

### 5. Verificar archivos relevantes para la fase actual
Según la fase identificada en DEVPLAN.md, localizar los archivos clave:

**Fase 1-3 (Build/Test/Extract):**
- `Dockerfile`
- `docker-compose.yml`
- `deploy.py` (subcomandos build, test, extract)
- `scripts/docker-build.sh`
- `scripts/compat-kernel.h`

**Fase 4 (Install/Verify/Uninstall):**
- `deploy.py` (subcomandos install, verify, uninstall)
- `scripts/inject_modversions.py`

**Fase 5 (Pulido):**
- `README.deploy.md`
- `deploy.py` (flags --help, manejo de errores)

**Fase 6 (VPS):**
- Acceso SSH a VPS (credenciales en `.env`)
- Repo en `/root/openss7` en la VPS

**Fase 7 (Portainer):**
- `docker-compose.yml` (servicio portainer)
- Configuración de Portainer en VPS

### 6. Resumir y confirmar con el usuario
Presentar al usuario:
1. **Fase actual** y su progreso (ej: "Fase 7 — Portainer, 0%")
2. **Última tarea completada** (desde CLAUDE.md)
3. **Próxima tarea** a ejecutar (primera `- [ ]` en DEVPLAN.md de la fase actual)
4. **Archivos** que se van a crear/modificar
5. **Contexto técnico** relevante (ej: errores resueltos previamente)

Preguntar: "¿Continúo con [próxima tarea]? ¿O prefieres ajustar el plan?"

### 7. Ejecutar la próxima tarea
Una vez confirmado por el usuario:
- Ejecutar la tarea siguiendo las reglas del proyecto
- Al completarla, marcar como completada en DEVPLAN.md: `- [ ]` → `- [x]`
- Si hay pruebas de fase pendientes, ejecutarlas antes de avanzar
- Si toda la fase está completa, actualizar:
  - Tabla de estado en DEVPLAN.md
  - Sección "Estado Actual" en CLAUDE.md
  - Crear memoria persistente si hay aprendizajes nuevos

## Reglas importantes al continuar

1. **NO avanzar de fase si hay errores** — fixear primero
2. **Actualizar las 3 capas de memoria** al completar cada fase
3. **NO modificar src/, tests/, configure.ac** — solo infraestructura de deploy
4. **Verificar precondiciones** antes de cada comando (Docker instalado, permisos root si aplica)
5. **Seguir convención tmux en VPS** si trabajas en producción

## Notas técnicas clave

- OpenSS7 se compila SOLO en Docker, nunca directamente en el host
- Los módulos .ko deben compilarse contra el kernel que los ejecutará
- `scripts/compat-kernel.h` contiene 14 fixes de compatibilidad para kernel 5.x+
- `scripts/inject_modversions.py` inyecta sección `__versions` post-build (CONFIG_MODVERSIONS=y)
- VPS: Ubuntu 22.04.5 LTS, kernel 5.15.0-173-generic, IP 129.121.60.55:22022
