# Reglas de Testing

## Niveles de prueba
1. **Nivel 1 — Build (Docker)**: Compilacion + make check + artefactos generados
2. **Nivel 2 — Carga (Host)**: Modulos cargados + servicios activos + utilidades
3. **Nivel 3 — Protocolos (Cliente)**: NO nos compete

## Pruebas entre fases
- OBLIGATORIO ejecutar pruebas de fase antes de avanzar a la siguiente
- Si hay UN error, se fixea antes de continuar
- No se permite deuda tecnica entre fases

## Validacion de artefactos
- Verificar existencia de .ko, .so y binarios despues del build
- Verificar que los .ko son para el kernel correcto
- Verificar que los paquetes RPM/DEB contienen los archivos esperados

## Reporte de pruebas
- Cada prueba debe reportar PASS o FAIL
- El reporte final tiene exit code 0 (todo bien) o 1 (algo fallo)
- Incluir conteo: X passed, Y failed, Z skipped

## Pruebas de regresion
- Despues de cualquier fix, re-ejecutar TODAS las pruebas de la fase actual
- Un fix no debe romper nada que funcionaba antes
