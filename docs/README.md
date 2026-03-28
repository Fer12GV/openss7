# OpenSS7 Deploy System — Documentación Completa

> **Para estudiantes de Ingeniería en Telecomunicaciones y Sistemas**
> Esta documentación cubre todo lo necesario para entender, replicar y operar el sistema en un entorno local o en producción (VPS).

---

## ¿Qué es esto?

Un sistema de despliegue automatizado para **OpenSS7** — la implementación open-source del stack de protocolos SS7/SIGTRAN para Linux. Permite compilar, instalar y verificar OpenSS7 en cualquier servidor Linux mediante un único CLI en Python.

**Problema que resuelve:** Compilar OpenSS7 manualmente requiere resolver decenas de dependencias del kernel, compatibilidad de compiladores y flags de build — un proceso que puede tomar días. Este sistema lo automatiza completamente en 5 comandos.

---

## Documentos de esta guía

| Archivo | Contenido |
|---------|-----------|
| [01-openss7-y-ss7.md](01-openss7-y-ss7.md) | Qué es SS7, STREAMS y por qué importan en telecomunicaciones |
| [02-arquitectura.md](02-arquitectura.md) | Cómo funciona el sistema internamente: Docker, kernel, CLI |
| [03-guia-local.md](03-guia-local.md) | Guía paso a paso para replicarlo en tu PC local (Ubuntu/Debian) |
| [04-guia-vps.md](04-guia-vps.md) | Guía paso a paso para desplegarlo en un VPS de producción |
| [05-profundidad-tecnica.md](05-profundidad-tecnica.md) | Deep-dive: módulos .ko, CONFIG_MODVERSIONS, inject_modversions |
| [06-diagramas-mermaid.md](06-diagramas-mermaid.md) | Diagramas de flujo, arquitectura y casos reales de telecomunicaciones |

---

## Inicio rápido (resumen ejecutivo)

### Prerrequisitos

```bash
# Ubuntu/Debian
sudo apt install docker.io docker-compose-v2 python3 linux-headers-$(uname -r)
sudo systemctl start docker
sudo usermod -aG docker $USER   # reinicia sesión después
```

### 5 comandos para tener OpenSS7 funcionando

```bash
# 1. Clonar el repositorio
git clone <repositorio> openss7 && cd openss7

# 2. Compilar todo dentro de Docker (~30-60 min la primera vez)
python3 deploy.py build

# 3. Validar que los artefactos son correctos
python3 deploy.py test

# 4. Extraer módulos y binarios al host
python3 deploy.py extract

# 5. Instalar en el kernel del host (requiere root)
sudo python3 deploy.py install

# 6. Verificar que todo carga correctamente
python3 deploy.py verify
```

### Resultado esperado de `verify`

```
[STEP] Verificando instalacion de OpenSS7...
[INFO] CHECK modulo streams cargado            PASS
[INFO] CHECK modulo specfs cargado             PASS
[INFO] CHECK directorio de modulos presente    PASS
[INFO] CHECK binario strinfo funciona          PASS
[INFO] CHECK binario scls funciona             PASS
[INFO] VERIFY_SUMMARY: 5 PASS, 0 FAIL
```

---

## Flujo completo del sistema

```
git clone
  └─> python3 deploy.py build     [Docker  ~30-60 min]
        └─> python3 deploy.py test       [Docker  ~10 seg]
              └─> python3 deploy.py extract   [Docker→Host  ~5 seg]
                    └─> sudo python3 deploy.py install  [Host  ~5 seg]
                          └─> python3 deploy.py verify  [Host  ~2 seg]
                                └─> sudo python3 deploy.py uninstall [opcional]
```

---

## Compatibilidad verificada

| Entorno build (Docker) | Kernel host | Resultado |
|------------------------|-------------|-----------|
| Ubuntu 22.04 (Debian) | 5.15.0-173-generic | **PASS completo** |

---

## Artefactos generados

| Tipo | Cantidad | Destino |
|------|----------|---------|
| Módulos kernel `.ko` | 123 | `/lib/modules/$(uname -r)/extra/openss7/` |
| Librerías `.so` | 35 | `/usr/local/lib/openss7/` |
| Binarios | 5 | `/usr/local/bin/` |

---

## Comandos de referencia rápida

```bash
python3 deploy.py build      # Compilar (Docker)
python3 deploy.py test       # Validar artefactos (Docker)
python3 deploy.py extract    # Extraer al host
sudo python3 deploy.py install    # Instalar módulos en kernel
python3 deploy.py verify          # Verificar instalación
sudo python3 deploy.py uninstall  # Desinstalar limpiamente
```

---

## Niveles de responsabilidad

| Nivel | Qué prueba | Quién |
|-------|-----------|-------|
| 1 — Build | Compilación, .ko, .so, binarios, make check | Este sistema (Docker) |
| 2 — Carga | modprobe, servicios systemd, utilidades | Este sistema (Host) |
| 3 — Protocolos | SS7/SIGTRAN en red de producción real | Cliente / operadora |

---

*Desarrollado como infraestructura de despliegue sobre el proyecto open-source OpenSS7.*
*El código fuente de OpenSS7 (src/, configure.ac, Makefile.am) no fue modificado.*
