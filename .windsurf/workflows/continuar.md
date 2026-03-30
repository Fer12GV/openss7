---
description: Reanuda el trabajo del proyecto OpenSS7 Deploy System desde donde quedo la ultima sesion
---

# Workflow: Continuar Desarrollo

Este workflow permite retomar el trabajo del proyecto OpenSS7 desde donde quedó la última sesión, con contexto completo de las **3 capas de memoria**.

## Instrucciones

Cuando el usuario ejecute `/continuar`, sigue estos pasos EN ORDEN:

### Paso 1 — Leer contexto persistente
Lee `CLAUDE.md` en la raiz del proyecto. Ahi esta el stack, reglas y estado actual.

### Paso 2 — Revisar plan de desarrollo
Lee `docs/DEVPLAN.md`. Busca la fase actual (la primera que NO este marcada como COMPLETADA en la tabla de estado).
Identifica las tareas pendientes (marcadas con `- [ ]`).

### Paso 3 — Revisar alcance
Lee `docs/SCOPE.md` para refrescar el alcance y decisiones arquitectonicas.

### Paso 4 — Verificar archivos relevantes
Usa Glob para localizar los archivos de la fase actual:
- Fase 1: Dockerfile, docker-compose.yml, deploy.py
- Fase 2-3: deploy.py (subcomandos test/extract)
- Fase 4: deploy.py (subcomandos install/verify/uninstall)
- Fase 5: README.deploy.md, deploy.py (flags UX)
- Fase 6-7: VPS deployment y Portainer

Si los archivos existen, leelos para entender el estado actual del codigo.

### Paso 5 — Identificar PRIMERA tarea pendiente
Busca en DEVPLAN.md la PRIMERA tarea marcada con `- [ ]` en la fase actual.
IMPORTANTE: Una tarea solo esta completada si tiene `- [x]` en DEVPLAN.md.
NO importa si el codigo ya existe — sigue el DEVPLAN.md como fuente de verdad.

### Paso 6 — Resumir y confirmar
Presenta al usuario:
1. **Fase actual** y progreso (de la tabla en DEVPLAN.md)
2. **Ultima tarea completada** (ultima `- [x]` antes de la primera `- [ ]`)
3. **Proxima tarea** a ejecutar (primera `- [ ]` encontrada)
4. **Contexto tecnico** relevante (VPS, archivos, comandos)

Pregunta: "Continuo ejecutando: [proxima tarea]?"

### Paso 7 — Ejecutar la tarea
Una vez confirmado:
1. Ejecuta la tarea EXACTAMENTE como esta descrita en DEVPLAN.md
2. Al completarla exitosamente, marca como `- [x]` en DEVPLAN.md
3. Si hay pruebas de fase pendientes, ejecutalas
4. Si toda la fase esta completa, actualiza estado en DEVPLAN.md y CLAUDE.md
5. Recomienda ejecutar `/cierre` si se completo una fase o bloque importante
