# Arquitectura SS7 — Visión General y Rol de OpenSS7

## 1. ¿Qué es SS7?

**Signaling System No. 7 (SS7)** es el conjunto de protocolos de señalización utilizado por las redes de telecomunicaciones a nivel mundial desde los años 80. Es el "sistema nervioso" de la red telefónica: no transporta voz ni datos del usuario, sino **mensajes de control** entre los equipos de la red.

SS7 se encarga de:
- Establecer, mantener y terminar llamadas telefónicas
- Entregar mensajes SMS entre operadores
- Roaming entre redes (HLR/VLR queries)
- Portabilidad numérica
- Facturación y tarificación
- Servicios de valor agregado (buzón de voz, desvío de llamadas, etc.)

**Estándares**: ITU-T serie Q.700-Q.799, ANSI T1.110-T1.116, ETSI EN 300 008.


## 2. Componentes de una Red SS7

```
┌─────────────────────────────────────────────────────────────┐
│                     RED SS7 DEL OPERADOR                    │
│                                                             │
│  ┌───────┐     ┌───────┐     ┌───────┐     ┌───────┐      │
│  │  SSP  │─────│  STP  │─────│  STP  │─────│  SSP  │      │
│  │(Central│     │(Transit│     │(Transit│     │(Central│     │
│  │ local) │     │  A)   │     │  B)   │     │ remota)│     │
│  └───┬───┘     └───┬───┘     └───┬───┘     └───┬───┘      │
│      │             │             │             │            │
│      │         ┌───┴───┐         │             │            │
│      │         │  SCP  │         │             │            │
│      │         │(Base de│         │             │            │
│      │         │ datos) │         │             │            │
│      │         └───────┘         │             │            │
│      │                           │             │            │
│  ┌───┴───┐                   ┌───┴───┐     ┌───┴───┐      │
│  │  HLR  │                   │  MSC  │─────│  VLR  │      │
│  │(Home  │                   │(Mobile│     │(Visitor│      │
│  │Loc Reg│                   │Switch)│     │Loc Reg)│      │
│  └───────┘                   └───────┘     └───────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Nodos principales

| Componente | Nombre Completo | Función |
|-----------|----------------|---------|
| **SSP** | Signal Switching Point | Central telefónica que origina/termina llamadas y genera mensajes SS7 |
| **STP** | Signal Transfer Point | Router de señalización — enruta mensajes SS7 entre nodos |
| **SCP** | Signal Control Point | Base de datos de la red (número 800, portabilidad, prepago) |
| **HLR** | Home Location Register | BD maestra de suscriptores — sabe dónde está cada usuario |
| **VLR** | Visitor Location Register | BD temporal de suscriptores en una zona geográfica |
| **MSC** | Mobile Switching Center | Central de conmutación móvil — conecta llamadas GSM |
| **SMSC** | Short Message Service Center | Centro de mensajes — almacena y reenvía SMS |


## 3. Pila de Protocolos SS7

```
         ┌────────────────────────────────────┐
Nivel 7  │  TCAP / MAP / INAP / CAP / ISUP   │  ← Aplicación
         ├────────────────────────────────────┤
Nivel 4  │            SCCP                     │  ← Red (direccionamiento global)
         ├────────────────────────────────────┤
Nivel 3  │            MTP3                     │  ← Red (enrutamiento de mensajes)
         ├────────────────────────────────────┤
Nivel 2  │            MTP2                     │  ← Enlace (control de errores)
         ├────────────────────────────────────┤
Nivel 1  │         MTP1 / SIGTRAN              │  ← Físico / Transporte IP
         └────────────────────────────────────┘
```

### Descripción de cada capa

- **MTP1 (Message Transfer Part 1)**: Capa física. Tradicionalmente enlaces E1/T1 a 64 kbps por timeslot. En redes modernas, reemplazado por **SIGTRAN** sobre IP.
- **MTP2**: Control de enlace — detección de errores, retransmisión, alineación.
- **MTP3**: Enrutamiento de mensajes entre nodos SS7 usando **Point Codes** (direcciones únicas por nodo).
- **SCCP (Signaling Connection Control Part)**: Direccionamiento global usando **Global Titles** (números de teléfono como direcciones).
- **TCAP (Transaction Capabilities Application Part)**: Diálogos transaccionales entre nodos.
- **MAP (Mobile Application Part)**: Protocolo entre HLR, VLR, MSC para gestión de suscriptores GSM.
- **ISUP (ISDN User Part)**: Establecimiento y liberación de circuitos de voz.
- **CAP (CAMEL Application Part)**: Servicios inteligentes (prepago, roaming).


## 4. SIGTRAN — SS7 sobre IP

Las redes modernas ya no usan enlaces E1/T1 dedicados. **SIGTRAN** permite transportar señalización SS7 sobre redes IP usando **SCTP** como protocolo de transporte (en lugar de TCP/UDP).

```
  SS7 Tradicional              SS7 sobre IP (SIGTRAN)
  ┌──────────┐                 ┌──────────┐
  │ MAP/ISUP │                 │ MAP/ISUP │
  │   TCAP   │                 │   TCAP   │
  │   SCCP   │                 │   SCCP   │
  │   MTP3   │                 │   M3UA   │  ← Adaptación MTP3 a IP
  │   MTP2   │                 │   SCTP   │  ← Transporte confiable
  │   MTP1   │                 │    IP    │  ← Red IP estándar
  │  (E1/T1) │                 │ Ethernet │
  └──────────┘                 └──────────┘
```

### Protocolos de adaptación SIGTRAN
| Protocolo | Función | RFC |
|-----------|---------|-----|
| **M3UA** | MTP3 User Adaptation | RFC 4666 |
| **M2UA** | MTP2 User Adaptation | RFC 3331 |
| **M2PA** | MTP2 Peer-to-Peer Adaptation | RFC 4165 |
| **SUA** | SCCP User Adaptation | RFC 3868 |
| **IUA** | ISDN User Adaptation | RFC 4233 |


## 5. ¿Dónde Encaja OpenSS7?

OpenSS7 es una **implementación en software** de la pila completa SS7 + SIGTRAN para Linux. Proporciona:

```
┌──────────────────────────────────────────────────┐
│                  Lo que OpenSS7 da                │
│                                                   │
│  ✅ Módulos kernel: STREAMS subsystem             │
│  ✅ Protocolo SCTP (kernel module)                │
│  ✅ MTP2, MTP3, SCCP, TCAP, ISUP, MAP            │
│  ✅ SIGTRAN: M2UA, M3UA, SUA, IUA, M2PA          │
│  ✅ Librerías userspace (.so) y utilidades CLI    │
│  ✅ APIs: TPI, NPI, XTI/TLI para aplicaciones    │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│              Lo que OpenSS7 NO da                 │
│                                                   │
│  ❌ Conexión física a la red del operador         │
│  ❌ Point Code asignado por el regulador          │
│  ❌ Acuerdo de interconexión con el operador      │
│  ❌ Hardware de señalización (tarjetas E1/T1)     │
│  ❌ Aplicaciones de usuario final (SMS, voz)      │
│  ❌ Interfaz gráfica de ningún tipo               │
└──────────────────────────────────────────────────┘
```

**OpenSS7 es la pila de protocolos, no la red ni las aplicaciones.**


## 6. ¿Qué Se Necesita Además del Software?

Para conectar un nodo SS7 a una red de operador real, se requiere **mucho más** que solo el software:

### 6.1 — Requisitos de red y regulatorios

| Requisito | Descripción | Quién lo provee |
|-----------|-------------|-----------------|
| **Point Code (PC)** | Dirección única en la red SS7 nacional | Regulador de telecomunicaciones del país |
| **Acuerdo de interconexión** | Contrato legal con el operador para intercambiar señalización | Operador (Movistar, Claro, etc.) |
| **Global Title (GT)** | Rango de números asignados para direccionamiento SCCP | Operador / Regulador |
| **Licencia de operador** | Habilitación legal para operar como nodo SS7 | Ente regulador nacional |

### 6.2 — Requisitos de hardware

| Componente | Función | Ejemplos |
|-----------|---------|----------|
| **Tarjeta E1/T1** (si SS7 tradicional) | Interfaz física de señalización | Sangoma A101/A102, Digium TE110P |
| **Servidor dedicado** | Ejecuta la pila SS7 | Cualquier server Linux con los módulos OpenSS7 |
| **Conectividad IP dedicada** (si SIGTRAN) | Enlace IP punto a punto con el operador | VPN, MPLS, o enlace dedicado |
| **Firewall SS7/SIGTRAN** | Filtra mensajes maliciosos | Cellusys, Mobileum, Evolved Intelligence |

### 6.3 — Requisitos de configuración

Para que OpenSS7 funcione como nodo SS7, necesita configuración de:

1. **Point Code local** — identidad del nodo en la red
2. **Point Codes remotos** — nodos con los que se comunica (STPs, HLR, MSC)
3. **Linksets** — grupos de enlaces hacia cada nodo adyacente
4. **Rutas** — tabla de enrutamiento SS7 (a qué enlace enviar cada mensaje)
5. **Global Titles** — traducción de números de teléfono a direcciones SS7
6. **Aplicación** — software custom que use las APIs de OpenSS7 (TPI/NPI/XTI)

**Estos archivos de configuración son responsabilidad del operador/integrador que despliega el nodo.**


## 7. Diagrama: Flujo de un SMS en la Red

Para contexto general, así viaja un SMS entre dos teléfonos:

```
  Teléfono A                                                    Teléfono B
  (origen)                                                      (destino)
      │                                                             ▲
      │ Radio (GSM/LTE)                                             │ Radio
      ▼                                                             │
  ┌───────┐    SS7/MAP     ┌────────┐    SS7/MAP     ┌───────┐    │
  │ MSC-A │───────────────▶│  SMSC  │───────────────▶│ MSC-B │────┘
  │       │  MO-ForwardSM  │        │  MT-ForwardSM  │       │
  └───┬───┘                └────┬───┘                └───┬───┘
      │                        │                        │
      │    SS7/MAP             │   SS7/MAP              │
      │  SendRoutingInfo       │  SendRoutingInfo       │
      │       │                ▼                        │
      │       │           ┌────────┐                    │
      │       └──────────▶│  HLR   │◀───────────────────┘
      │                   │        │
      │                   └────────┘
      │
  Flujo simplificado:
  1. MSC-A recibe SMS del teléfono A por radio
  2. MSC-A envía MO-ForwardSM al SMSC via SS7/MAP
  3. SMSC consulta al HLR: ¿dónde está el teléfono B? (SendRoutingInfoForSM)
  4. HLR responde con la dirección del MSC-B
  5. SMSC envía MT-ForwardSM al MSC-B via SS7/MAP
  6. MSC-B entrega el SMS al teléfono B por radio
```

**Nota**: Cada flecha "SS7/MAP" implica un diálogo completo TCAP/SCCP/MTP3 entre los nodos. OpenSS7 implementa todas estas capas de protocolo.


## 8. Resumen Ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿OpenSS7 solo basta? | **No.** Es solo la pila de protocolos (software). |
| ¿Se necesita hardware adicional? | **Sí.** Tarjetas E1/T1 o enlace IP dedicado al operador. |
| ¿Se necesita autorización del operador? | **Sí.** Acuerdo de interconexión + Point Code asignado. |
| ¿Se necesita licencia regulatoria? | **Sí.** Licencia de operador de telecomunicaciones. |
| ¿Se necesita desarrollo adicional? | **Sí.** Aplicaciones custom usando las APIs de OpenSS7 (TPI/NPI/XTI). |
| ¿OpenSS7 tiene interfaz gráfica? | **No.** Es un stack de kernel + librerías C. Cualquier UI debe desarrollarse aparte. |
| ¿Qué entrega este proyecto? | Infraestructura de deploy: OpenSS7 compilado, instalado y verificado. |
| ¿Quién configura los protocolos? | El operador/integrador de telecomunicaciones con acceso a la red SS7. |


## 9. Referencias

- ITU-T Q.700 — Introduction to CCITT Signalling System No. 7
- ITU-T Q.711-Q.716 — SCCP (Signalling Connection Control Part)
- ITU-T Q.771-Q.775 — TCAP (Transaction Capabilities Application Part)
- 3GPP TS 29.002 — MAP (Mobile Application Part)
- RFC 4960 — SCTP (Stream Control Transmission Protocol)
- RFC 4666 — M3UA (MTP3 User Adaptation Layer)
- RFC 3868 — SUA (SCCP User Adaptation Layer)
- GSMA IR.82 — SS7 Security Guidelines
- OpenSS7 Project Documentation — http://www.openss7.org/
