---
description: Ritual de cierre de sesión - actualizar las 3 capas de memoria para continuidad
---

# Workflow: Cierre de Sesión

Este workflow actualiza las **3 capas de memoria** al finalizar una sesión de trabajo, garantizando que la próxima sesión pueda continuar sin pérdida de contexto.

## Las 3 Capas de Memoria

1. **CLAUDE.md** — Estado actual del proyecto (sección "Estado Actual")
2. **docs/DEVPLAN.md** — Tareas completadas y pendientes (checkboxes `- [x]` / `- [ ]`)
3. **Memorias WindSurf** — Memorias persistentes accesibles en futuras conversaciones

## Pasos del ritual de cierre

### Paso 1 — Identificar trabajo realizado en esta sesión
Revisar el historial de la conversación y determinar:
- **¿Qué tareas se completaron?** (listar con checkbox completado)
- **¿Qué archivos se crearon o modificaron?** (listar rutas absolutas)
- **¿Qué errores se encontraron y cómo se resolvieron?** (describir fix aplicado)
- **¿Qué quedó pendiente?** (próxima tarea a ejecutar)
- **¿Se completó una fase entera?** (verificar criterio de aceptación)

### Paso 2 — Actualizar docs/DEVPLAN.md
Aplicar estos cambios en orden:

1. **Marcar tareas completadas:**
   ```diff
   - - [ ] Implementar subcomando test
   + - [x] Implementar subcomando test
   ```

2. **Actualizar progreso de la fase en la tabla:**
   ```diff
   - | 2 | Test + Validacion | EN CURSO | 50% |
   + | 2 | Test + Validacion | COMPLETADA | 100% |
   ```

3. **Si se completó una fase entera:**
   - Marcar como COMPLETADA en la tabla
   - Verificar que todas las tareas tienen `[x]`
   - Verificar que las "Pruebas de Fase" pasaron

4. **Si se descubrieron tareas nuevas:**
   - Agregarlas en la fase correspondiente con `- [ ]`
   - Actualizar el conteo de progreso

5. **Actualizar campo "Ultima actualizacion":**
   ```diff
   - **Ultima actualizacion**: 2026-03-29 (sesion 7)
   + **Ultima actualizacion**: 2026-03-30 (sesion 8)
   ```

### Paso 3 — Actualizar CLAUDE.md
Actualizar la sección "Estado Actual del Proyecto" (líneas ~116-122):

```markdown
## Estado Actual del Proyecto
<!-- Actualiza esto al final de cada sesion con workflow /cierre -->
Ultima sesion: 2026-03-30 (sesion 8)
Ultima tarea completada: [DESCRIPCION_DE_LA_ULTIMA_TAREA_COMPLETADA]
Proxima tarea: [PRIMERA_TAREA_PENDIENTE_EN_DEVPLAN]
Rama activa: master
Fase actual: Fase [N] [ESTADO] — [NOMBRE_FASE]
```

**Campos a actualizar:**
- `Ultima sesion:` → fecha de hoy + número de sesión
- `Ultima tarea completada:` → descripción concisa de lo último que se terminó
- `Proxima tarea:` → la siguiente tarea `- [ ]` en DEVPLAN.md
- `Fase actual:` → formato "Fase N ESTADO — Nombre" (ej: "Fase 7 EN CURSO — Portainer")

### Paso 4 — Actualizar/Crear memorias persistentes de WindSurf
Si hubo **aprendizajes relevantes** para futuras sesiones, crear o actualizar memorias:

**Crear memoria nueva si:**
- Se resolvió un error técnico no trivial (ej: nuevo issue de kernel)
- Se tomó una decisión arquitectónica importante
- El usuario expresó una preferencia explícita

**Actualizar memoria existente si:**
- El estado del proyecto cambió significativamente
- Una fase se completó
- Se agregó funcionalidad a un componente ya documentado

**Tipos de memoria a considerar:**
- **Feedback técnico:** Issues resueltos, workarounds, fixes aplicados
- **Estado del proyecto:** Progreso de fases, artefactos generados
- **Decisiones de diseño:** Cambios arquitectónicos, trade-offs
- **Preferencias del usuario:** Nuevas reglas o convenciones acordadas

**Usar la herramienta `create_memory`:**
```
Title: [Tipo]: [Descripción breve]
Content: [Contexto completo con Why/How to apply]
Tags: ["openss7", "categoria", "tipo"]
Action: create o update
```

### Paso 5 — Confirmar cierre con el usuario
Presentar un resumen estructurado:

```markdown
## Resumen de la Sesión

### ✅ Completado en esta sesión
- [Tarea 1 completada con detalles]
- [Tarea 2 completada con detalles]
- [Archivos creados/modificados]

### 📊 Estado Actualizado del Proyecto
- **Fase actual:** Fase N — [Nombre] ([X]% completado)
- **Última tarea completada:** [Descripción]
- **Próxima tarea:** [Descripción de la siguiente tarea pendiente]

### 🔄 Memoria actualizada
- CLAUDE.md ✓
- docs/DEVPLAN.md ✓
- Memorias WindSurf ✓ ([N] memorias creadas/actualizadas)

### ➡️ Próximos pasos para la siguiente sesión
1. [Primera tarea pendiente]
2. [Segunda tarea pendiente si aplica]
3. [Pruebas de fase si aplica]
```

### Paso 6 — Commit (opcional, si hay cambios significativos)
Si se completó una fase o hay cambios importantes:
```bash
git add CLAUDE.md docs/DEVPLAN.md [archivos_modificados]
git commit -m "Fase [N] completada: [descripción breve]"
git push origin master
```

## Reglas críticas del cierre

1. **NUNCA omitir la actualización de las 3 capas** — es el objetivo principal del workflow
2. **SIEMPRE verificar que DEVPLAN.md y CLAUDE.md están sincronizados** — el estado debe coincidir
3. **NO dejar tareas marcadas como completadas si tienen errores** — fixear primero
4. **Actualizar memorias WindSurf SOLO si hay valor agregado** — no crear memorias redundantes
5. **El resumen debe ser conciso pero completo** — el próximo modelo debe poder continuar sin preguntar

## Ejemplo de cierre completo

**Escenario:** Se completó Fase 2 (Test + Validación)

**Cambios aplicados:**
- ✅ DEVPLAN.md: Fase 2 marcada como COMPLETADA 100%
- ✅ DEVPLAN.md: 5 tareas marcadas con `[x]`
- ✅ CLAUDE.md: "Ultima tarea completada: Fase 2 COMPLETADA..."
- ✅ CLAUDE.md: "Proxima tarea: FASE 3 — Bloque 3.1 deploy.py extract"
- ✅ Memoria WindSurf: Actualizada "Proyecto: Estado Actual" con progreso de Fase 2

**Resumen presentado al usuario:**
```
## Resumen de la Sesión

### ✅ Completado
- Implementado subcomando `test` en deploy.py
- Ejecutado make check: 42 PASS, 0 FAIL
- Validación de artefactos: 7/7 PASS
- FASE 2 COMPLETADA 100%

### 📊 Estado Actualizado
- Fase actual: Fase 3 EN CURSO — Extract + Paquetes Nativos (0%)
- Próxima tarea: Implementar subcomando `extract`

### 🔄 Memoria actualizada
- CLAUDE.md ✓
- docs/DEVPLAN.md ✓
- Memorias WindSurf ✓ (1 actualizada: Estado del Proyecto)

### ➡️ Próximos pasos
1. Implementar `deploy.py extract`
2. Copiar .ko, .so, binarios al host
3. Generar MANIFEST.txt
```
