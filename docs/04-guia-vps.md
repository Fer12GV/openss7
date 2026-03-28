# Guía de Despliegue en VPS — Producción

> **Nivel:** Intermedio a Avanzado
> **Objetivo:** Desplegar OpenSS7 en un servidor virtual (VPS) de producción desde cero.
> **Precondición:** Haber completado y validado el despliegue local (guía 03) — o al menos entender el proceso.

---

## ¿Cuándo usar un VPS en lugar de un PC local?

| Escenario | Local | VPS |
|-----------|-------|-----|
| Aprendizaje y laboratorio | ✅ Ideal | Innecesario |
| Interconexión con operadora real | No viable | ✅ Necesario |
| Servicio 24/7 para empresa | No viable | ✅ Necesario |
| IP pública fija para SS7/SIGTRAN | Difícil | ✅ Incluida |
| Pruebas de rendimiento | Limitado | ✅ Hardware dedicado |

---

## Requisitos del VPS

### Hardware mínimo

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 4 GB | 8 GB |
| vCPU | 2 | 4 |
| Disco | 40 GB SSD | 80 GB SSD |
| Ancho de banda | 100 Mbps | 1 Gbps |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Requerimientos de red

- IP pública estática (para interconexión con operadoras)
- Puerto 22/22022 abierto para SSH de administración
- Puertos para SCTP (2905, 2904) si se conecta con red SS7

---

## Fase 1 — Conectar al VPS

```bash
# Desde tu PC local, conectar via SSH
ssh -p 22022 root@<IP_DEL_VPS>

# Ejemplo con el VPS de este proyecto
ssh -p 22022 root@129.121.60.55
# Ingresar la contraseña cuando la pida
```

### Verificar el estado inicial del servidor

```bash
# Una vez conectado al VPS:

# Ver OS y kernel
uname -a
lsb_release -a

# Ver recursos disponibles
free -h
df -h
nproc

# Ver conectividad
ping -c 3 google.com
```

---

## Fase 2 — Preparar el sistema base

### Actualizar el sistema

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# Instalar herramientas básicas
apt install -y \
    curl wget git \
    vim nano \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release
```

### Instalar kernel headers

```bash
# CRÍTICO: los headers deben coincidir con el kernel activo del VPS
apt install -y linux-headers-$(uname -r)

# Verificar
ls /lib/modules/$(uname -r)/build
# Debe mostrar el directorio de headers — si da error, los headers no están
```

> **Problema común en VPS:** Algunos proveedores usan kernels personalizados (como Linode o DigitalOcean) cuyos headers no están disponibles en apt. En ese caso, busca los headers específicos del proveedor o usa el kernel genérico de Ubuntu.

```bash
# Si los headers no están disponibles, instalar kernel genérico y reiniciar
apt install -y linux-image-generic linux-headers-generic
reboot
# Al reconectar, el kernel será el genérico con headers disponibles
```

---

## Fase 3 — Instalar Docker

```bash
# Método oficial de Docker (más actualizado que el de apt)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Verificar instalación
docker --version
# Docker version 24.x.x, build ...

# Iniciar y habilitar Docker
systemctl start docker
systemctl enable docker
systemctl status docker

# Instalar docker compose plugin
apt install -y docker-compose-plugin

# Verificar
docker compose version
# Docker Compose version v2.x.x
```

---

## Fase 4 — Instalar Python 3

```bash
# En Ubuntu 22.04, Python 3 ya viene instalado
python3 --version
# Python 3.10.x

# Si no está:
apt install -y python3

# Verificar
python3 -c "import subprocess, pathlib, argparse; print('OK')"
# OK
```

---

## Fase 5 — Transferir el repositorio al VPS

### Opción A — Git clone (recomendado si el repo es público)

```bash
# En el VPS
cd /opt
git clone <URL_DEL_REPOSITORIO> openss7
cd openss7
```

### Opción B — SCP desde tu PC local

```bash
# Desde TU PC LOCAL (no el VPS)
# Comprimir el proyecto
tar -czf openss7.tar.gz -C ~ openss7 \
    --exclude='openss7/.git' \
    --exclude='openss7/build-output' \
    --exclude='openss7/src/.deps'

# Copiar al VPS
scp -P 22022 openss7.tar.gz root@129.121.60.55:/opt/

# En el VPS: descomprimir
cd /opt
tar -xzf openss7.tar.gz
cd openss7
```

### Opción C — rsync (mejor para actualizaciones posteriores)

```bash
# Desde TU PC LOCAL
rsync -avz --progress \
    --exclude='.git' \
    --exclude='build-output' \
    -e "ssh -p 22022" \
    ~/openss7/ \
    root@129.121.60.55:/opt/openss7/
```

---

## Fase 6 — Configurar variables de entorno

```bash
# En el VPS
cd /opt/openss7

# Crear el .env desde la plantilla
cp .env.example .env

# Editar si es necesario (el build detecta todo automáticamente)
nano .env
```

Contenido típico del `.env` en un VPS:

```bash
# Build
TARGET_DISTRO=debian
KERNEL_VERSION=auto
BUILD_JOBS=auto

# VPS (solo para referencia)
VPS_HOST=129.121.60.55
VPS_PORT=22022
VPS_USER=root
```

---

## Fase 7 — Build en el VPS

```bash
# En el VPS, dentro de /opt/openss7
python3 deploy.py build
```

> **Tiempo estimado:** 30-60 minutos en primera ejecución.
> El VPS compilará los módulos contra **su propio kernel** — que puede ser diferente al de tu PC local. El sistema detecta esto automáticamente.

### Monitorear el progreso

Si quieres ver el progreso en detalle en otra sesión SSH:

```bash
# En una segunda ventana SSH
docker logs -f openss7-builder-1
```

### Resultado esperado

```
[INFO] Kernel detectado: 5.15.0-91-generic   ← kernel del VPS
[INFO] BUILD completado en XXXX segundos
[INFO] Modulos .ko: 123
[INFO] Librerias .so: 41
```

---

## Fase 8 — Test, Extract, Install y Verify

```bash
# Validar artefactos
python3 deploy.py test

# Extraer al host del VPS
python3 deploy.py extract

# Instalar en el kernel del VPS
python3 deploy.py install

# Verificar
python3 deploy.py verify
```

### Resultado final esperado

```
[INFO] VERIFY_SUMMARY: 5 PASS, 0 FAIL
```

---

## Fase 9 — Configuración post-instalación para producción

### Verificar que los módulos cargan automáticamente al reiniciar

```bash
# Crear archivo de módulos para carga automática
echo "specfs" >> /etc/modules
echo "streams" >> /etc/modules

# Verificar
cat /etc/modules
```

### Habilitar servicios systemd (si existen)

```bash
systemctl enable openss7 2>/dev/null && \
systemctl start openss7 2>/dev/null || \
echo "No hay unit files de systemd — OK para esta instalacion"
```

### Verificar que persiste después de reinicio

```bash
# Reiniciar el VPS
reboot

# Reconectar
ssh -p 22022 root@129.121.60.55

# Verificar que los módulos cargaron automáticamente
lsmod | grep streams
strinfo
```

---

## Fase 10 — Hardening básico del VPS

Una vez instalado OpenSS7, asegurar el servidor:

```bash
# Cambiar puerto SSH si aún no está cambiado
# (el VPS de este proyecto ya usa 22022)
grep "Port" /etc/ssh/sshd_config

# Deshabilitar login con contraseña (usar SSH keys)
# PRECAUCIÓN: asegúrate de tener una SSH key cargada antes
# sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
# systemctl reload sshd

# Configurar firewall básico
ufw allow 22022/tcp    # SSH
ufw allow 2905/tcp     # SIGTRAN M3UA (si aplica)
ufw allow 2905/udp
ufw allow 2904/tcp     # SIGTRAN M2UA (si aplica)
ufw enable
```

---

## Diferencias entre build local y build en VPS

| Aspecto | Local (tu PC) | VPS (producción) |
|---------|---------------|------------------|
| Kernel | 5.15.0-173-generic | Puede ser diferente |
| .ko generados | Para tu kernel | Para el kernel del VPS |
| IP pública | No/dinámica | Sí, estática |
| Disponibilidad | Solo cuando la PC enciende | 24/7 |
| Capacidad protocolar | Laboratorio | Producción real |

**Los .ko compilados en local NO son intercambiables con los del VPS** si tienen kernels diferentes. Siempre compilar en el entorno donde se van a cargar.

---

## Troubleshooting VPS

### El kernel del VPS no tiene headers disponibles

```bash
# Verificar kernel actual
uname -r

# Buscar headers disponibles
apt search linux-headers | grep $(uname -r | cut -d- -f1-2)

# Si no hay match exacto, cambiar al kernel genérico
apt install -y linux-image-generic linux-headers-generic
# Ver cuál se instaló
dpkg -l | grep linux-image

# Reboot al nuevo kernel
reboot
```

### Docker no instala con get-docker.sh (VPS restringido)

```bash
# Método alternativo — desde repositorio oficial
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### Build falla por falta de espacio en disco

```bash
# Ver uso de disco
df -h

# Limpiar imágenes Docker no usadas
docker system prune -a

# Si el VPS tiene poco disco, limpiar logs del sistema
journalctl --vacuum-size=100M
```

### Módulos no cargan después de reboot

```bash
# Verificar que depmod se ejecutó
depmod -a

# Verificar que los archivos están en su lugar
ls /lib/modules/$(uname -r)/extra/openss7/

# Intentar cargar manualmente con verbose
modprobe --verbose specfs
modprobe --verbose streams
```

---

## Lista de verificación final — VPS listo para producción

```
[ ] VPS con Ubuntu 22.04 LTS
[ ] Sistema actualizado (apt upgrade)
[ ] Kernel headers instalados
[ ] Docker instalado y corriendo
[ ] Repositorio clonado/transferido
[ ] python3 deploy.py build       → PASS
[ ] python3 deploy.py test        → 7/7 PASS
[ ] python3 deploy.py extract     → 123 .ko extraídos
[ ] python3 deploy.py install     → módulos cargados
[ ] python3 deploy.py verify      → 5/5 PASS
[ ] lsmod | grep streams          → aparecen streams y specfs
[ ] strinfo                       → responde sin error
[ ] Módulos en /etc/modules       → carga automática en reboot
[ ] Firewall configurado (ufw)
[ ] Reboot de prueba → módulos cargan automáticamente
```

---

*Siguiente: [Profundidad técnica — módulos de kernel y modversions →](05-profundidad-tecnica.md)*
