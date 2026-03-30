# Skill: /cierre

## Descripcion
Ritual de cierre de sesion. Actualiza las 3 capas de memoria para que la proxima sesion pueda continuar sin perdida de contexto.

## Instrucciones
Cuando el usuario ejecute `/cierre`, sigue estos pasos EN ORDEN:

### Paso 1 — Identificar trabajo realizado
Revisa el historial de la conversacion y determina:
- Que tareas se completaron en esta sesion
- Que archivos se crearon o modificaron
- Que errores se encontraron y como se resolvieron
- Que quedo pendiente

### Paso 2 — Actualizar DEVPLAN.md
- Marca las tareas completadas: `- [ ]` → `- [x]`
- Actualiza el progreso de la fase en la tabla de estado
- Si se completo una fase entera, marca como COMPLETADA
- Si se descubrieron tareas nuevas, agregarlas en la fase correspondiente
- Actualiza "Ultima actualizacion" con la fecha de hoy

### Paso 3 — Actualizar CLAUDE.md
Actualiza la seccion "Estado Actual del Proyecto":
- `Ultima sesion:` → fecha de hoy
- `Ultima tarea completada:` → la ultima tarea que se termino
- `Proxima tarea:` → la siguiente tarea pendiente en DEVPLAN.md
- `Fase actual:` → la fase activa con su estado

### Paso 4 — Actualizar memoria persistente
Si hubo aprendizajes relevantes para futuras sesiones:
- Preferencias del usuario → guardar en memory/
- Decisiones tecnicas no obvias → guardar en memory/
- Errores recurrentes y sus soluciones → guardar en memory/

### Paso 5 — Confirmar cierre
Presenta al usuario:
1. Resumen de lo completado
2. Estado actualizado del proyecto
3. Proximos pasos para la siguiente sesion
