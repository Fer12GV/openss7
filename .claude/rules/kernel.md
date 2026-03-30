# Reglas Kernel Modules

## Compilacion
- Los modulos .ko DEBEN compilarse contra los kernel headers del host que los ejecutara
- Montar /lib/modules/$(uname -r) dentro del contenedor Docker
- Verificar que la version del kernel es compatible con OpenSS7

## Carga de modulos
- Usar modprobe (preferido) o insmod para cargar modulos
- Orden de carga importa: streams.ko primero, luego specfs.ko, luego protocolos
- Ejecutar depmod -a despues de instalar modulos nuevos
- Verificar carga con lsmod | grep <modulo>

## Desinstalacion
- Descargar modulos en orden inverso con rmmod
- Nunca forzar descarga (rmmod -f) a menos que sea absolutamente necesario
- Verificar que no hay procesos usando los modulos antes de descargar

## Servicios systemd
- openss7.service y streams.service deben habilitarse con systemctl enable
- Verificar estado con systemctl is-active
- Los servicios dependen de los modulos cargados

## Permisos
- Operaciones de kernel requieren root/sudo
- deploy.py debe verificar permisos al inicio de install/verify/uninstall
- Dar mensaje claro si no hay permisos suficientes
