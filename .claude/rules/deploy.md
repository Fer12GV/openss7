# Reglas de Deploy

## Filosofia
- deploy.py es el UNICO punto de entrada para el usuario
- Cada subcomando es autocontenido y reporta su resultado
- El flujo completo es: build → test → extract → install → verify
- uninstall es independiente (se puede ejecutar en cualquier momento)

## Deteccion automatica
- Detectar distro del host automaticamente (Debian/Ubuntu vs CentOS/Fedora)
- Detectar version del kernel automaticamente
- Detectar numero de CPUs para build paralelo
- Detectar si Docker esta instalado y corriendo

## Manejo de errores
- Verificar pre-condiciones al inicio de cada subcomando
- Si falta Docker → mensaje claro con instrucciones
- Si faltan permisos → mensaje claro pidiendo sudo
- Si no hay build previo → mensaje claro pidiendo ejecutar build primero
- NUNCA continuar silenciosamente despues de un error

## Idempotencia
- `deploy.py build` puede ejecutarse multiples veces sin problemas
- `deploy.py install` sobre una instalacion existente debe actualizar, no duplicar
- `deploy.py uninstall` cuando no esta instalado debe informar, no fallar

## Seguridad
- No ejecutar como root a menos que sea necesario (install/verify/uninstall)
- No modificar archivos del sistema fuera del alcance de OpenSS7
- No dejar procesos huerfanos
- Cleanup automatico de contenedores temporales
