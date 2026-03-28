# Guía de Instalación Local — Para Estudiantes

> **Nivel:** Principiante a Intermedio
> **Sistema operativo:** Ubuntu 22.04 LTS (recomendado) / Debian 12
> **Tiempo estimado:** 60-90 minutos (la mayor parte es espera del build)
> **Objetivo:** Tener OpenSS7 compilado, instalado y verificado en tu PC local.

---

## Prerrequisitos de hardware

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 6 GB | 8 GB o más |
| CPU | 2 cores | 4+ cores (build paralelo) |
| Disco | 20 GB libres | 30 GB |
| OS | Ubuntu 20.04 | Ubuntu 22.04 LTS |

> **Nota para VMs:** Si usas VirtualBox o VMware, asigna al menos 4 GB de RAM al entorno virtual y habilita la virtualización de hardware (VT-x/AMD-V).

---

## Paso 0 — Verificar el sistema

Antes de comenzar, verifica que tienes lo mínimo necesario:

```bash
# Verificar versión de Ubuntu
lsb_release -a

# Verificar kernel (necesitarás los headers de esta versión)
uname -r
# Ejemplo de salida: 5.15.0-173-generic

# Verificar RAM disponible
free -h

# Verificar espacio en disco
df -h /
```

---

## Paso 1 — Instalar dependencias del sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
sudo apt install -y docker.io

# Instalar docker compose (versión plugin, no el wrapper antiguo)
sudo apt install -y docker-compose-v2

# Instalar Python 3 (probablemente ya está instalado)
sudo apt install -y python3

# Instalar kernel headers (CRÍTICO — debe coincidir exactamente con tu kernel)
sudo apt install -y linux-headers-$(uname -r)

# Instalar git
sudo apt install -y git
```

### Verificar la instalación de Docker

```bash
# Verificar que Docker está corriendo
sudo systemctl status docker

# Si no está corriendo, iniciarlo
sudo systemctl start docker
sudo systemctl enable docker
```

---

## Paso 2 — Configurar permisos de Docker

Por defecto, Docker requiere sudo. Para ejecutar sin sudo (recomendado):

```bash
# Agregar tu usuario al grupo docker
sudo usermod -aG docker $USER

# IMPORTANTE: Cerrar sesión y volver a entrar para que tome efecto
# O ejecutar esto para cambiar el grupo sin reiniciar sesión:
newgrp docker

# Verificar que funciona
docker run hello-world
# Debe mostrar "Hello from Docker!" sin errores
```

---

## Paso 3 — Clonar el repositorio

```bash
# Clonar en tu directorio home (o donde prefieras)
cd ~
git clone <URL_DEL_REPOSITORIO> openss7
cd openss7

# Verificar estructura
ls -la
# Debes ver: deploy.py, Dockerfile, docker-compose.yml, docs/, scripts/, src/
```

---

## Paso 4 — Configurar variables de entorno (opcional)

El sistema detecta automáticamente el kernel y los CPUs, pero puedes personalizar:

```bash
# Copiar la plantilla
cp .env.example .env

# Ver el archivo (no es necesario editarlo para un build básico)
cat .env.example
```

El `.env` permite ajustar:
- `BUILD_JOBS=auto` — número de compilaciones paralelas (auto = usa todos los cores)
- `KERNEL_VERSION=auto` — versión del kernel (auto = usa el kernel activo)

---

## Paso 5 — Compilar OpenSS7 (build)

```bash
# Ejecutar el build
python3 deploy.py build
```

### ¿Qué verás?

```
[STEP] Detectando version del kernel del host...
[INFO] Kernel detectado: 5.15.0-173-generic
[STEP] Iniciando build de OpenSS7 en Docker...
[INFO] Construyendo imagen Docker...
[INFO] Ejecutando compilacion...
[INFO] configure: checking for kernel headers... ok
[INFO] make -j8
... (mucho output de compilación ~20-40 minutos) ...
[INFO] Inyectando seccion __versions en modulos .ko...
[INFO] 123 modulos inyectados, 0 fallos
[INFO] BUILD completado en 2341 segundos
[INFO] Modulos .ko: 123
[INFO] Librerias .so: 41
[INFO] Binarios: 5
```

**Este paso toma entre 30 y 60 minutos la primera vez.** En builds posteriores (con caché) toma menos de 2 minutos.

> **¿Qué hace el build por dentro?**
> 1. Construye la imagen Docker (instala gcc, autotools, etc.)
> 2. Ejecuta `./autogen.sh` (genera configure a partir de configure.ac)
> 3. Ejecuta `./configure` con los parámetros del kernel
> 4. Ejecuta `make -j$(nproc)` (compila todo en paralelo)
> 5. Ejecuta `inject_modversions.py` (inyecta CRCs de símbolos del kernel)

---

## Paso 6 — Validar artefactos (test)

```bash
python3 deploy.py test
```

### Resultado esperado

```
[STEP] Ejecutando tests en contenedor Docker...
[INFO] make check: ejecutando suite de tests...
[INFO] PASS: 42 tests, 0 failures
[INFO] Validando artefactos...
[INFO] ARTIFACT_PASS streams.ko encontrado
[INFO] ARTIFACT_PASS specfs.ko encontrado
[INFO] ARTIFACT_PASS strinfo encontrado
[INFO] ARTIFACT_PASS scls encontrado
[INFO] ARTIFACT_PASS vermagic coincide con kernel host
[INFO] ARTIFACT_PASS .so librerias encontradas
[INFO] ARTIFACT_PASS conteo .ko: 123
[INFO] ARTIFACT_SUMMARY: 7 PASS, 0 FAIL
```

Si ves `0 FAIL`, todo está correcto y puedes continuar.

---

## Paso 7 — Extraer artefactos al host

```bash
python3 deploy.py extract
```

### Resultado esperado

```
[STEP] Extrayendo artefactos del contenedor al host...
[INFO] EXTRACT_PASS modulos .ko: 123
[INFO] EXTRACT_PASS librerias .so: 35
[INFO] EXTRACT_PASS binarios: 5
[INFO] MANIFEST.txt generado
[INFO] Artefactos en: ./build-output/
```

### Verificar manualmente

```bash
ls build-output/
# modules/  libs/  bin/  MANIFEST.txt

ls build-output/modules/ | head -10
# streams.ko  specfs.ko  streams_sctp.ko  ...

ls build-output/bin/
# strinfo  scls  strace  strerr  slconfig
```

---

## Paso 8 — Instalar en el kernel del host

```bash
# REQUIERE ROOT
sudo python3 deploy.py install
```

### ¿Qué hace este paso?

1. Copia los 123 `.ko` a `/lib/modules/$(uname -r)/extra/openss7/`
2. Copia las `.so` a `/usr/local/lib/openss7/`
3. Copia los binarios a `/usr/local/bin/`
4. Ejecuta `depmod -a` (actualiza la base de datos de módulos del kernel)
5. Ejecuta `modprobe specfs` (carga el filesystem de STREAMS)
6. Ejecuta `modprobe streams` (carga el subsistema STREAMS)

### Resultado esperado

```
[STEP] Instalando OpenSS7 en el host...
[INFO] Copiando modulos a /lib/modules/5.15.0-173-generic/extra/openss7/
[INFO] Copiando librerias a /usr/local/lib/openss7/
[INFO] Copiando binarios a /usr/local/bin/
[INFO] Ejecutando depmod -a...
[INFO] Cargando modulo specfs...
[INFO] Cargando modulo streams...
[INFO] INSTALL completado
```

---

## Paso 9 — Verificar la instalación

```bash
python3 deploy.py verify
```

### Resultado esperado (todo funcionando)

```
[STEP] Verificando instalacion de OpenSS7...
[INFO] CHECK modulo streams cargado            PASS
[INFO] CHECK modulo specfs cargado             PASS
[INFO] CHECK directorio de modulos presente    PASS
[INFO] CHECK binario strinfo funciona          PASS
[INFO] CHECK binario scls funciona             PASS
[INFO] VERIFY_SUMMARY: 5 PASS, 0 FAIL
```

### Verificación manual adicional

```bash
# Ver módulos STREAMS cargados en el kernel
lsmod | grep -E "streams|specfs"
# streams               229376  0
# specfs                 65536  1 streams

# Ver información del subsistema STREAMS
strinfo

# Listar streams disponibles
scls

# Ver que los módulos están en el kernel
modinfo streams | grep -E "filename|vermagic|description"
```

---

## Paso 10 — Desinstalar (cuando quieras)

```bash
sudo python3 deploy.py uninstall
```

El sistema descarga los módulos del kernel, elimina todos los archivos instalados y ejecuta `depmod -a`. El sistema vuelve exactamente al estado anterior.

---

## Troubleshooting — Problemas comunes

### Error: `Cannot connect to the Docker daemon`

```bash
# Docker no está corriendo
sudo systemctl start docker

# O tu usuario no está en el grupo docker
sudo usermod -aG docker $USER
newgrp docker
```

### Error: `kernel headers not found`

```bash
# Instalar headers para tu kernel exacto
sudo apt install linux-headers-$(uname -r)

# Verificar que existen
ls /lib/modules/$(uname -r)/build
# Debe mostrar el directorio de headers
```

### Error: `Exec format error` al hacer modprobe

Significa que el .ko no tiene la sección `__versions`. Solución:

```bash
# El build debe haber fallado en inject_modversions — rebuildar
python3 deploy.py build
python3 deploy.py extract
sudo python3 deploy.py install
```

Para diagnosticar:
```bash
# Ver si el módulo tiene la sección __versions
readelf -S build-output/modules/streams.ko | grep __versions
# Si no aparece nada, falta la sección
```

### El build falla con `exit code 137` (OOM)

Docker se quedó sin memoria. Soluciones:

```bash
# Opción 1: cerrar aplicaciones pesadas y reintentar
python3 deploy.py build

# Opción 2: reducir jobs paralelos en .env
echo "BUILD_JOBS=2" >> .env
python3 deploy.py build
```

### Build lento / congelado

El build de OpenSS7 compila miles de archivos C. Es normal que tarde. No canceles con Ctrl+C a menos que lleve más de 90 minutos sin mostrar output.

```bash
# Ver progreso del build en otra terminal
docker logs -f openss7-builder-1
```

### `ldconfig: libXXX.so.0 is not a symlink`

Advertencia cosmética — las librerías funcionan correctamente. OpenSS7 no genera symlinks versionados. No afecta la funcionalidad.

---

## Flujo de verificación completo (resumen)

```bash
# Ejecutar todo en secuencia
python3 deploy.py build   && \
python3 deploy.py test    && \
python3 deploy.py extract && \
sudo python3 deploy.py install && \
python3 deploy.py verify
```

Si todos los comandos retornan exit code 0, OpenSS7 está completamente funcional.

---

## ¿Qué hacer después?

1. **Explorar el subsistema STREAMS:**
   ```bash
   ls /dev/streams/    # Dispositivos STREAMS disponibles
   strinfo             # Información del subsistema
   ```

2. **Cargar módulos de protocolo SS7:**
   ```bash
   sudo modprobe streams_sctp   # Soporte SCTP para SIGTRAN
   lsmod | grep streams
   ```

3. **Estudiar la documentación de OpenSS7:**
   ```bash
   man strinfo
   man scls
   ```

4. **Ir a la guía de VPS** si quieres desplegarlo en producción → [04-guia-vps.md](04-guia-vps.md)

---

*Siguiente: [Guía de despliegue en VPS →](04-guia-vps.md)*
