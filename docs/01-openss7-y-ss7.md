# OpenSS7 y SS7 — Fundamentos para Telecomunicaciones

> **Nivel:** Introductorio — Ingeniería en Telecomunicaciones / Sistemas
> **Objetivo:** Entender qué es SS7, qué es STREAMS, cómo se relacionan y por qué siguen siendo críticos en las redes modernas.

---

## 1. ¿Qué es SS7?

**SS7 (Signaling System No. 7)** es el protocolo de señalización que usa la red telefónica pública conmutada (PSTN) mundial. Fue diseñado por la ITU-T en los años 70 y sigue siendo el backbone de señalización de voz en todo el mundo.

### ¿Para qué sirve SS7?

Cuando marcas un número de teléfono, SS7 es responsable de:

- **Establecer la llamada** — buscar al destinatario en la red
- **Enrutar la señalización** — decidir por qué camino va la llamada
- **Gestionar el número portado** — localizar un número aunque haya cambiado de operadora
- **SMS tradicionales** — el sistema MAP sobre SS7 transporta SMS entre redes
- **Roaming internacional** — cuando tu teléfono funciona en otro país

```
Tu teléfono → Antena → Central (MSC) → Red SS7 → Central destino → Teléfono destino
                              │                       │
                          Señalización SS7 ←────────►
                         (ruta independiente de la voz)
```

### Capas del protocolo SS7

```
┌─────────────────────────────────────────┐
│  TCAP  MAP  INAP  CAP  (capa aplicación) │  ← Servicios (roaming, SMS, IN)
├─────────────────────────────────────────┤
│              SCCP                        │  ← Routing de señalización
├─────────────────────────────────────────┤
│              MTP3                        │  ← Control de red
├─────────────────────────────────────────┤
│              MTP2                        │  ← Control de enlace
├─────────────────────────────────────────┤
│              MTP1                        │  ← Capa física (E1/T1/IP)
└─────────────────────────────────────────┘
```

---

## 2. ¿Qué es SIGTRAN?

**SIGTRAN** (Signaling Transport) es la adaptación de SS7 para funcionar sobre redes IP. En lugar de usar circuitos E1/T1, transporta la señalización SS7 sobre **SCTP** (Stream Control Transmission Protocol) sobre IP.

```
Red SS7 tradicional:        Red SIGTRAN moderna:
┌─────────┐                 ┌─────────┐
│  MSC A  │════ E1 ════     │  MSC A  │════ IP/SCTP ════
│         │    (64Kbps)     │         │    (cualquier BW)
└─────────┘                 └─────────┘
```

**¿Por qué importa?** Permite que operadoras de VoIP (como empresas de call center o carriers IP) se interconecten con la red SS7 de las operadoras tradicionales.

---

## 3. ¿Qué es UNIX STREAMS?

**STREAMS** es una arquitectura del kernel de UNIX (definida en SVR4) que permite construir pilas de protocolos de comunicación de manera modular.

### La metáfora del tubo

STREAMS funciona exactamente como su nombre indica — una tubería de módulos que procesan los datos:

```
Aplicación de usuario
        │ write() / read()
        ▼
┌───────────────────┐
│  Stream Head      │  ← interfaz con el kernel
├───────────────────┤
│  Módulo 1 (SCCP)  │  ← módulos apilables dinámicamente
├───────────────────┤
│  Módulo 2 (MTP3)  │
├───────────────────┤
│  Módulo 3 (MTP2)  │
├───────────────────┤
│  Driver (MTP1)    │  ← hardware o red IP
└───────────────────┘
        │
    Red física / IP
```

### ¿Por qué STREAMS para SS7 y no sockets BSD?

| Característica | BSD Sockets | UNIX STREAMS |
|---------------|-------------|--------------|
| Arquitectura | Monolítica | Modular (push/pop dinámico) |
| Protocolos apilables | No | Sí — en tiempo de ejecución |
| Origen | BSD Unix | AT&T UNIX System V |
| Uso en SS7 | Limitado | Nativo (diseñado para ello) |

STREAMS permite cargar `push("sccp")` dinámicamente sobre un stream existente — crítico para la arquitectura en capas de SS7.

---

## 4. ¿Qué es OpenSS7?

**OpenSS7** es la implementación open-source (AGPLv3) del stack STREAMS + SS7 + SIGTRAN para Linux. Implementa:

- El subsistema STREAMS en el kernel de Linux (`streams.ko`, `specfs.ko`)
- Los protocolos SS7: MTP2, MTP3, SCCP, TCAP (`streams_mtp2.ko`, etc.)
- Los adaptadores SIGTRAN: M2UA, M3UA, SUA (`streams_m2ua.ko`, etc.)
- Las librerías de usuario para configurar y operar el stack

### Módulos principales instalados

```
streams.ko     — Núcleo del subsistema STREAMS en el kernel
specfs.ko      — Filesystem especial para devices STREAMS (/dev/streams/)
streams_sctp.ko — Implementación SCTP para transporte SIGTRAN
streams_mtp.ko  — Message Transfer Part (capa 2/3 de SS7)
streams_sccp.ko — Signaling Connection Control Part
streams_tcap.ko — Transaction Capabilities Application Part
streams_m2ua.ko — MTP2 User Adaptation (SIGTRAN)
streams_m3ua.ko — MTP3 User Adaptation (SIGTRAN)
```

---

## 5. ¿Por qué sigue siendo relevante hoy?

### En 2024, SS7 sigue siendo usado para:

1. **Interconexión entre operadoras** — todas las operadoras del mundo tienen un punto de señalización SS7
2. **Portabilidad numérica** — cuando cambias de operadora, SS7 redirige tus llamadas
3. **Roaming 2G/3G** — las redes más antiguas siguen usando SS7 puro
4. **Legacy billing** — muchos sistemas de facturación siguen integrados via TCAP/MAP
5. **Pasarelas VoIP ↔ PSTN** — los carriers IP necesitan un gateway SS7

### Caso de uso real: empresa con central telefónica IP

```
Oficina empresa
┌─────────────────────────────────────────────┐
│  Teléfonos IP  ──→  PBX Asterisk/FreeSWITCH │
│                           │                  │
│                    SIGTRAN/SIP               │
│                           │                  │
│                    Servidor Linux            │
│                    + OpenSS7                 │
│                    (streams.ko cargado)      │
└─────────────────────┬───────────────────────┘
                       │ E1/IP con SCTP
                       ▼
              ┌─────────────────┐
              │  Gateway SS7    │
              │  de la operadora│
              └────────┬────────┘
                       │ SS7/MTP
                       ▼
              Red SS7 nacional
              (cualquier número)
```

---

## 6. Glosario esencial

| Término | Significado |
|---------|-------------|
| **PSTN** | Public Switched Telephone Network — la red telefónica pública |
| **MSC** | Mobile Switching Center — central de conmutación móvil |
| **STP** | Signal Transfer Point — punto de transferencia de señalización |
| **SSP** | Service Switching Point — punto de conmutación de servicios |
| **MTP** | Message Transfer Part — capas físicas de SS7 (1, 2, 3) |
| **SCCP** | Signaling Connection Control Part — routing de mensajes SS7 |
| **TCAP** | Transaction Capabilities Application Part — transacciones SS7 |
| **MAP** | Mobile Application Part — protocolo de aplicación para redes móviles |
| **SCTP** | Stream Control Transmission Protocol — transporte para SIGTRAN |
| **M2UA/M3UA** | Adaptadores SIGTRAN para llevar MTP2/MTP3 sobre SCTP/IP |
| **PC** | Point Code — dirección de un nodo en la red SS7 |
| **GT** | Global Title — número telefónico en formato E.164 |

---

## 7. Lectura adicional recomendada

- **ITU-T Q.700 series** — Especificaciones oficiales de SS7
- **RFC 4666** — M3UA (MTP3 User Adaptation Layer)
- **RFC 2960** — SCTP (Stream Control Transmission Protocol)
- **ETSI EN 300 008** — SS7 para redes europeas
- Libro: *"SS7 Telecommunications Protocols"* — Travis Russell

---

*Siguiente: [Arquitectura del sistema de despliegue →](02-arquitectura.md)*
