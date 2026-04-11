# Skill: /continuar

## Descripcion
Reanuda el trabajo del proyecto OpenSS7 Deploy System desde donde quedo la ultima sesion.

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
- Fase 6: scripts/deploy-vps.sh, deploy.py (VPS remote)
- Fase 7: docker-compose.yml (servicio portainer), docs/07-portainer-acceso.md
- Fase 8: backend/, simulator/, frontend/, docs/09-requerimiento-tecnico-sms-ss7.md, docs/10-fase8-simulador.md

Si los archivos existen, leelos para entender el estado actual del codigo.

**IMPORTANTE para Fase 8**: Antes de tocar nada, leer TODAS estas memorias (contienen el contexto critico para continuar sin ambiguedad):
- memory/project_estado.md (estado sesion 10)
- memory/project_fase8_simulador.md (arquitectura simulador + decoder + UI)
- memory/project_vps_state.md (estado real VPS, Asterisk instalado, strinfo/scls rotos)
- memory/reference_ss7_parametros.md (parametros pendientes de Telefonica)
- memory/feedback_decoder_pycrate.md (decoder real con pycrate, nunca mocks)

### Paso 5 — Resumir y confirmar
Presenta al usuario:
1. **Fase actual** y progreso
2. **Ultima tarea completada**
3. **Proxima tarea** a ejecutar
4. **Archivos** que se van a crear/modificar

Pregunta: "Continuo con [proxima tarea]? O prefieres ajustar el plan?"

### Paso 6 — Ejecutar
Una vez confirmado, ejecuta la proxima tarea. Al completarla:
- Marca la tarea como completada en el DEVPLAN.md
- Si hay pruebas de fase pendientes, ejecutalas
- Si toda la fase esta completa, actualiza el estado en DEVPLAN.md y CLAUDE.md
