# OpenSS7 Deploy System — Alcance del Proyecto

## Descripcion
Sistema de despliegue containerizado para OpenSS7, un stack de protocolos STREAMS para Linux.
El objetivo es proporcionar un CLI (`deploy.py`) que automatice completamente la compilacion,
pruebas, extraccion de paquetes, instalacion, verificacion y desinstalacion de OpenSS7.

## Problema que Resuelve
OpenSS7 es un proyecto C legacy con un sistema de build complejo (GNU Autotools) que requiere
dependencias especificas del sistema operativo y kernel headers. Compilar manualmente es propenso
a errores y dificil de reproducir. Este sistema:

1. **Aisla la compilacion** en Docker (reproducible, sin contaminar el host)
2. **Automatiza todo el ciclo** desde build hasta verificacion
3. **Genera paquetes nativos** (RPM/DEB) para instalacion limpia
4. **Verifica la instalacion** confirmando modulos cargados y servicios activos

## Arquitectura

```
┌─────────────────────────────────────────────┐
│                  deploy.py                   │
│          (CLI Python - orquestador)          │
├─────────┬─────────┬─────────┬───────────────┤
│  build  │  test   │ extract │ install/verify │
├─────────┴─────────┴─────────┴───────────────┤
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │           Docker Container             │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  1. ./configure --prefix=...     │  │  │
│  │  │  2. make -jN                     │  │  │
│  │  │  3. make check                   │  │  │
│  │  │  4. make rpm / make deb          │  │  │
│  │  └──────────────────────────────────┘  │  │
│  │  Artefactos: .ko .so binarios RPM/DEB  │  │
│  └────────────────────────────────────────┘  │
│                                              │
├──────────────────────────────────────────────┤
│              Host Linux                      │
│  ┌──────────────────────────────────────┐    │
│  │  dpkg -i / rpm -i (paquetes)        │    │
│  │  modprobe streams, specfs, sctp     │    │
│  │  systemctl start openss7            │    │
│  │  strinfo / scls / strace (verify)   │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

## Modulos Principales

### 1. deploy.py — CLI Orquestador
- Punto de entrada unico con subcomandos (build, test, extract, install, verify, uninstall)
- Usa subprocess para interactuar con Docker y comandos del host
- Reporta progreso y errores de forma clara
- Sin dependencias externas mas alla de la stdlib de Python

### 2. Dockerfile — Entorno de Build
- Imagen base con todas las dependencias de compilacion
- Soporte para Debian y CentOS como base
- Kernel headers del host montados como volumen
- Multi-stage si es necesario para optimizar tamanio

### 3. docker-compose.yml — Orquestacion
- Servicio de build con volumenes para fuentes y artefactos
- Configuracion via variables de entorno
- Volumenes persistentes para cache de compilacion

## Decisiones Arquitectonicas

| Decision | Justificacion |
|----------|--------------|
| Docker para build, NO para runtime | Los modulos de kernel deben cargarse en el host real |
| Python stdlib only para deploy.py | Minimizar dependencias, funcionar en cualquier sistema |
| Paquetes nativos (RPM/DEB) | Instalacion/desinstalacion limpia via package manager |
| Kernel headers del host montados | Los modulos deben compilar contra el kernel que los ejecutara |
| Sin configuracion de protocolos | Responsabilidad del cliente, fuera del alcance |

## Lo que Entregamos
- Software compilado correctamente
- Paquetes nativos instalables (RPM/DEB)
- Modulos de kernel cargados
- Servicios systemd activos
- Utilidades operativas verificadas

## Lo que NO Incluimos
- Soporte para kernels no-Linux
- Modificaciones al codigo fuente de OpenSS7
