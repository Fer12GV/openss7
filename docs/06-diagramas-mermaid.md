# Diagramas de Flujo y Arquitectura — OpenSS7 Deploy System

> Todos los diagramas están en formato **Mermaid**.
> Para renderizarlos como imagen PNG, puedes copiar el bloque y pegarlo en:
> - **https://mermaid.live** (recomendado, gratuito, sin registro)
> - **https://kroki.io** (alternativa open-source)
> - Extensiones de VSCode: "Mermaid Preview", "Markdown Preview Mermaid Support"
> - GitHub y GitLab renderizan Mermaid automáticamente en archivos .md

---

## Diagrama 1 — Flujo completo del CLI (deploy.py)

> Muestra el recorrido de cada comando desde que el usuario lo ejecuta hasta el resultado final.

```mermaid
flowchart TD
    USER([👤 Usuario / Estudiante / Sysadmin])

    USER --> CMD_BUILD["python3 deploy.py build"]
    USER --> CMD_TEST["python3 deploy.py test"]
    USER --> CMD_EXTRACT["python3 deploy.py extract"]
    USER --> CMD_INSTALL["sudo python3 deploy.py install"]
    USER --> CMD_VERIFY["python3 deploy.py verify"]
    USER --> CMD_UNINSTALL["sudo python3 deploy.py uninstall"]

    CMD_BUILD --> CHK_DOCKER{Docker\ncorriendo?}
    CHK_DOCKER -- No --> ERR_DOCKER["❌ Error:\nsystemctl start docker"]
    CHK_DOCKER -- Sí --> DOCKER_BUILD["Docker: construir imagen\nUbuntu 22.04 + gcc + autotools"]
    DOCKER_BUILD --> AUTOGEN["./autogen.sh\n(genera configure)"]
    AUTOGEN --> CONFIGURE["./configure\n--with-k-release=KERNEL\n--disable-32bit-libs"]
    CONFIGURE --> MAKE["make -j$(nproc)\n~30-60 minutos\n123 .ko / 41 .so / 5 binarios"]
    MAKE --> INJECT["inject_modversions.py\n123 módulos inyectados\nsección __versions OK"]
    INJECT --> BUILD_OK["✅ BUILD completado\nbuild-cache: openss7-build-cache"]

    CMD_TEST --> CHK_BUILD1{Build\nexiste?}
    CHK_BUILD1 -- No --> ERR_BUILD1["❌ Error:\nejecutar build primero"]
    CHK_BUILD1 -- Sí --> MAKE_CHECK["make check\nautotest suite"]
    MAKE_CHECK --> PARSE_LOG["parsear testsuite.log\nTOTAL/PASS/SKIP/FAIL"]
    PARSE_LOG --> VALIDATE["Validar artefactos:\nstreams.ko ✓\nspecfs.ko ✓\nstrinfo ✓\nscls ✓\nvermagic ✓\n.so count ✓\n.ko count ✓"]
    VALIDATE --> TEST_OK["✅ 7/7 PASS\nARTIFACT_SUMMARY: 7 PASS, 0 FAIL"]

    CMD_EXTRACT --> CHK_BUILD2{Build\nexiste?}
    CHK_BUILD2 -- No --> ERR_BUILD2["❌ Error:\nejecutar build primero"]
    CHK_BUILD2 -- Sí --> COPY_KO["build-output/modules/\n123 archivos .ko"]
    COPY_KO --> COPY_SO["build-output/libs/\n35 archivos .so"]
    COPY_SO --> COPY_BIN["build-output/bin/\nstrinfo scls strace strerr slconfig"]
    COPY_BIN --> MANIFEST["MANIFEST.txt\n(inventario con tamaños)"]
    MANIFEST --> EXTRACT_OK["✅ EXTRACT completado"]

    CMD_INSTALL --> CHK_ROOT1{Es\nroot?}
    CHK_ROOT1 -- No --> ERR_ROOT1["❌ Error:\nusar sudo"]
    CHK_ROOT1 -- Sí --> CHK_EXTRACT{Extract\nlisto?}
    CHK_EXTRACT -- No --> ERR_EXTRACT["❌ Error:\nejecutar extract primero"]
    CHK_EXTRACT -- Sí --> INST_KO["/lib/modules/KERNEL/extra/openss7/\n123 .ko copiados"]
    INST_KO --> INST_SO["/usr/local/lib/openss7/\n35 .so copiados"]
    INST_SO --> INST_BIN["/usr/local/bin/\nstrinfo scls strace copiados"]
    INST_BIN --> DEPMOD["depmod -a\n(reconstruir árbol de módulos)"]
    DEPMOD --> MODPROBE_SPECFS["modprobe specfs\n(filesystem STREAMS)"]
    MODPROBE_SPECFS --> MODPROBE_STREAMS["modprobe streams\n(subsistema STREAMS)"]
    MODPROBE_STREAMS --> SYSTEMCTL["systemctl enable/start openss7\n(si unit file existe)"]
    SYSTEMCTL --> INSTALL_OK["✅ INSTALL completado"]

    CMD_VERIFY --> V1["lsmod | grep streams\n→ streams loaded"]
    V1 --> V2["lsmod | grep specfs\n→ specfs loaded"]
    V2 --> V3["ls /lib/modules/KERNEL/extra/openss7/\n→ directorio existe"]
    V3 --> V4["strinfo\n→ responde OK"]
    V4 --> V5["scls\n→ responde OK"]
    V5 --> VERIFY_OK["✅ VERIFY_SUMMARY: 5 PASS, 0 FAIL"]

    CMD_UNINSTALL --> CHK_ROOT2{Es\nroot?}
    CHK_ROOT2 -- No --> ERR_ROOT2["❌ Error:\nusar sudo"]
    CHK_ROOT2 -- Sí --> STOP_SVC["systemctl stop openss7\nsystemctl disable openss7"]
    STOP_SVC --> RMMOD["rmmod streams_sctp\nrmmod streams_ip\nrmmod streams\nrmmod specfs\n(orden correcto)"]
    RMMOD --> DPKG_R["dpkg -r openss7\n(si fue instalado con dpkg)"]
    DPKG_R --> RM_FILES["rm -rf /lib/modules/KERNEL/extra/openss7/\nrm -rf /usr/local/lib/openss7/\nrm /usr/local/bin/strinfo scls strace"]
    RM_FILES --> DEPMOD2["depmod -a\nldconfig"]
    DEPMOD2 --> UNINSTALL_OK["✅ UNINSTALL completado\nSistema en estado limpio"]

    style USER fill:#4a90d9,color:#fff
    style BUILD_OK fill:#27ae60,color:#fff
    style TEST_OK fill:#27ae60,color:#fff
    style EXTRACT_OK fill:#27ae60,color:#fff
    style INSTALL_OK fill:#27ae60,color:#fff
    style VERIFY_OK fill:#27ae60,color:#fff
    style UNINSTALL_OK fill:#27ae60,color:#fff
    style ERR_DOCKER fill:#e74c3c,color:#fff
    style ERR_BUILD1 fill:#e74c3c,color:#fff
    style ERR_BUILD2 fill:#e74c3c,color:#fff
    style ERR_ROOT1 fill:#e74c3c,color:#fff
    style ERR_ROOT2 fill:#e74c3c,color:#fff
    style ERR_EXTRACT fill:#e74c3c,color:#fff
```

---

## Diagrama 2 — Arquitectura del sistema

> Muestra cómo interactúan Docker, el host Linux y el kernel en tiempo real.

```mermaid
graph TB
    subgraph HOST["🖥️ Host Linux (Ubuntu 22.04)"]
        subgraph KERNEL["⚙️ Kernel Space (ring 0)"]
            KO1["streams.ko\n(subsistema STREAMS)"]
            KO2["specfs.ko\n(filesystem /dev/streams/)"]
            KO3["streams_sctp.ko\n(transporte SIGTRAN)"]
            KO1 --> DEV["/dev/streams/\n(dispositivos STREAMS)"]
        end

        subgraph USERSPACE["🧑‍💻 User Space (ring 3)"]
            STRINFO["strinfo\n(info del subsistema)"]
            SCLS["scls\n(listar streams)"]
            APP["Aplicación SS7/SIGTRAN\n(usa librerías .so)"]
            LIBS["/usr/local/lib/openss7/\nlibstreams.so\nlibsctp.so\n..."]
        end

        STRINFO --> SYSCALL
        SCLS --> SYSCALL
        APP --> LIBS
        LIBS --> SYSCALL["syscall interface"]
        SYSCALL --> KO1
        DEV --> SYSCALL
    end

    subgraph DOCKER["🐳 Docker Container (build time)"]
        subgraph BUILD_ENV["Ubuntu 22.04 + toolchain"]
            GCC["gcc / g++"]
            AUTOTOOLS["autoconf / automake\nautogen.sh → configure → make"]
            MODPOST["modpost.awk\n(post-procesado módulos)"]
            INJECT["inject_modversions.py\n(inyecta __versions)"]
        end

        subgraph SOURCES["📁 Código fuente OpenSS7"]
            SRC["src/ (C source)\nconfigure.ac\nMakefile.am"]
        end

        subgraph OUTPUT["📦 Artefactos generados"]
            KO_OUT["123 archivos .ko"]
            SO_OUT["35 archivos .so"]
            BIN_OUT["5 binarios"]
        end
    end

    subgraph VOLUMES["🔗 Volúmenes Docker montados"]
        V1["/lib/modules/KERNEL/\n(kernel headers del host)"]
        V2["/usr/src/linux-headers\n(fuentes del kernel)"]
        V3["/boot/System.map\n(mapa de símbolos)"]
        V4["openss7-build-cache\n(caché incremental)"]
        V5["./  (código fuente OpenSS7)"]
    end

    subgraph DEPLOYCLI["🐍 deploy.py (Python CLI)"]
        BUILD_CMD["cmd_build()\ndocker compose up"]
        INST_CMD["cmd_install()\nmodprobe + depmod"]
        VERIFY_CMD["cmd_verify()\nlsmod + strinfo"]
    end

    SRC --> AUTOTOOLS
    AUTOTOOLS --> MODPOST
    MODPOST --> KO_OUT
    AUTOTOOLS --> SO_OUT
    AUTOTOOLS --> BIN_OUT
    KO_OUT --> INJECT
    V1 --> AUTOTOOLS
    V3 --> INJECT

    BUILD_CMD --> DOCKER
    INST_CMD --> KO1
    INST_CMD --> KO2
    INST_CMD --> LIBS
    VERIFY_CMD --> KERNEL

    KO_OUT -.->|"deploy.py extract\nbuild-output/"| KO1
    SO_OUT -.->|"deploy.py extract"| LIBS
    BIN_OUT -.->|"deploy.py extract"| STRINFO

    style HOST fill:#f0f8ff,stroke:#2980b9
    style KERNEL fill:#ffe4e1,stroke:#e74c3c
    style DOCKER fill:#e8f8e8,stroke:#27ae60
    style DEPLOYCLI fill:#fff8dc,stroke:#f39c12
    style VOLUMES fill:#f5f5f5,stroke:#95a5a6
```

---

## Diagrama 3 — Proceso interno del build (detalle técnico)

> Para estudiantes avanzados: qué ocurre dentro del contenedor Docker durante la compilación.

```mermaid
sequenceDiagram
    participant DEV as 👤 Developer
    participant PY as deploy.py
    participant DC as docker compose
    participant CTR as Container
    participant MAKE as GNU Make
    participant INJ as inject_modversions.py

    DEV->>PY: python3 deploy.py build
    PY->>PY: detectar kernel (uname -r)
    PY->>PY: detectar CPUs (nproc)
    PY->>DC: docker compose up --build
    DC->>CTR: crear contenedor Ubuntu 22.04

    Note over CTR: Fase 1: Configuración
    CTR->>CTR: git config safe.directory
    CTR->>CTR: cd /opt/openss7
    CTR->>CTR: ./autogen.sh
    CTR->>CTR: ./configure --with-k-release=KERNEL<br/>--disable-java --disable-32bit-libs<br/>KERNEL_MODFLAGS="-DINCLUDE_VERMAGIC"

    Note over CTR,MAKE: Fase 2: Compilación (~30-60 min)
    CTR->>MAKE: make -j8
    MAKE->>MAKE: compilar src/modules/*.c → *.ko
    MAKE->>MAKE: compilar src/lib/*.c → *.so
    MAKE->>MAKE: compilar src/util/*.c → binarios
    MAKE->>MAKE: modpost.awk (sin -m → sin __versions)
    MAKE-->>CTR: 123 .ko (sin __versions), 41 .so, 5 binarios

    Note over CTR,INJ: Fase 3: Post-procesado (crítico)
    CTR->>INJ: python3 inject_modversions.py BUILD_DIR KERNEL
    INJ->>INJ: leer Module.symvers del kernel host
    loop Para cada .ko (123 módulos)
        INJ->>INJ: readelf -s → símbolos GLOBAL+UND
        INJ->>INJ: buscar CRCs en Module.symvers
        INJ->>INJ: construir blob: CRC(8B) + nombre(56B) × N
        INJ->>INJ: objcopy --add-section __versions=blob
    end
    INJ-->>CTR: 123 módulos con __versions inyectado

    CTR-->>DC: exit 0 (éxito)
    DC-->>PY: build completado
    PY->>DEV: ✅ BUILD completado — 123 .ko, 41 .so, 5 binarios
```

---

## Diagrama 4 — Caso real: Empresa de telecomunicaciones

> Flujo de implementación en una empresa real que necesita conectarse a la red SS7 de una operadora. Experiencia desde la perspectiva del ingeniero y del usuario final.

```mermaid
graph TB
    subgraph OPERADORA["📡 Red SS7 — Operadora Telefónica"]
        STP["STP\n(Signal Transfer Point)\nPunto de enrutamiento SS7"]
        PSTN["PSTN\nRed Telefónica Pública"]
        SS7NET["Red SS7 Nacional\n(MTP2/MTP3/SCCP/TCAP)"]
        STP --- SS7NET
        PSTN --- SS7NET
    end

    subgraph EMPRESA["🏢 Empresa / Call Center / Carrier IP"]
        subgraph SERVIDOR["🖥️ Servidor Linux de Señalización"]
            OS["Ubuntu 22.04 LTS"]
            OS --> STREAMS_SVC["streams.ko\nspecfs.ko\n(OpenSS7 instalado via deploy.py)"]
            STREAMS_SVC --> M3UA["streams_m3ua.ko\n(M3UA: MTP3 sobre SCTP/IP)"]
            STREAMS_SVC --> SCCP_MOD["streams_sccp.ko\n(SCCP: routing de mensajes)"]
            STREAMS_SVC --> TCAP_MOD["streams_tcap.ko\n(TCAP: transacciones)"]
        end

        subgraph PBX["📞 PBX / Call Manager"]
            ASTERISK["Asterisk / FreeSWITCH\n(SIP interno)"]
            IVR["IVR\n(menú de voz)"]
            AGENTS["Agentes\n(teléfonos IP)"]
        end

        subgraph APPS["💻 Aplicaciones de Negocio"]
            BILLING["Sistema de Facturación\n(TCAP/MAP)"]
            PORTAB["Portabilidad Numérica\n(SCCP/TCAP)"]
            SMS_GW["Gateway SMS\n(MAP)"]
        end

        ASTERISK <-->|"SIP"| STREAMS_SVC
        BILLING --> TCAP_MOD
        PORTAB --> SCCP_MOD
        SMS_GW --> TCAP_MOD
    end

    subgraph USUARIO_EXTERNO["📱 Usuario externo"]
        CELULAR["Teléfono móvil\n(cualquier operadora)"]
    end

    subgraph EMPLEADO["👤 Empleado en oficina"]
        IP_PHONE["Teléfono IP\nde escritorio"]
        PC["PC con softphone"]
    end

    CELULAR -->|"Llamada entrante"| OPERADORA
    SS7NET <-->|"E1 / IP + SCTP\nSIGTRAN"| M3UA
    PBX <-->|"SIP / RTP"| IP_PHONE
    PBX <-->|"SIP / RTP"| PC
    AGENTS --> IP_PHONE

    style OPERADORA fill:#ffe4e1,stroke:#e74c3c
    style EMPRESA fill:#e8f8e8,stroke:#27ae60
    style SERVIDOR fill:#e8f4fd,stroke:#2980b9
    style USUARIO_EXTERNO fill:#fff8dc,stroke:#f39c12
    style EMPLEADO fill:#f0fff0,stroke:#27ae60
```

---

## Diagrama 5 — Experiencia de usuario: llamada a través de OpenSS7

> Traza el recorrido completo de una llamada desde que un cliente llama a una empresa hasta que el agente responde, mostrando qué hace OpenSS7 en cada paso.

```mermaid
sequenceDiagram
    participant CLIENT as 📱 Cliente<br/>(teléfono móvil)
    participant OPER as 📡 Operadora<br/>(red SS7)
    participant GW as 🖥️ Servidor<br/>OpenSS7 (Linux)
    participant PBX as 📞 PBX<br/>(Asterisk)
    participant AGENT as 👤 Agente<br/>(teléfono IP)

    Note over CLIENT,AGENT: Flujo de una llamada entrante al call center

    CLIENT->>OPER: Marca +57 1 234 5678 (número del call center)
    OPER->>OPER: SS7 MTP3: enrutar hacia destino
    OPER->>OPER: SCCP: identificar Point Code destino
    OPER->>OPER: ISUP: IAM (Initial Address Message) → configurar circuito

    OPER->>GW: SIGTRAN M3UA sobre SCTP/IP<br/>IAM con número llamado y llamante

    Note over GW: OpenSS7 procesa el mensaje
    GW->>GW: streams_m3ua.ko: desencapsular M3UA
    GW->>GW: streams_sccp.ko: resolver routing SCCP
    GW->>GW: streams_isup.ko: procesar ISUP IAM
    GW->>GW: Consultar portabilidad numérica (TCAP HLR)

    GW->>OPER: TCAP SRI (Send Routing Info)
    OPER-->>GW: TCAP SRI-ACK + info de enrutamiento

    GW->>PBX: SIP INVITE (llamada entrante)
    PBX->>PBX: Evaluar dialplan
    PBX->>PBX: IVR: "Bienvenido, marque 1 para ventas..."
    PBX->>CLIENT: SIP 183 Progress → Audio IVR
    CLIENT->>PBX: DTMF "1" (usuario marca ventas)

    PBX->>PBX: Cola de agentes disponibles
    PBX->>AGENT: SIP INVITE (llamada a agente)
    AGENT-->>PBX: SIP 200 OK (agente responde)
    PBX-->>GW: SIP 200 OK (llamada conectada)

    GW->>OPER: ISUP ANM (Answer Message)
    OPER-->>CLIENT: Llamada conectada ✅

    Note over CLIENT,AGENT: Conversación en curso (RTP audio)
    CLIENT<-->AGENT: 🎤 Conversación de voz (RTP)

    Note over CLIENT,AGENT: Fin de llamada
    AGENT->>PBX: Cuelga (SIP BYE)
    PBX->>GW: SIP BYE
    GW->>OPER: ISUP REL (Release)
    OPER-->>GW: ISUP RLC (Release Complete)
    OPER->>CLIENT: Llamada terminada

    Note over GW: OpenSS7 registra CDR (Call Detail Record)
    GW->>GW: Generar registro de facturación
```

---

## Diagrama 6 — Ciclo de vida del deploy (vista de proyecto)

> Para coordinadores de proyecto o estudiantes de gestión de TI: cómo se ve el despliegue como proceso de proyecto.

```mermaid
gantt
    title Despliegue OpenSS7 — Línea de tiempo típica
    dateFormat HH:mm
    axisFormat %H:%M

    section Preparación (una vez)
    Instalar Docker y dependencias     :prep1, 00:00, 15m
    Clonar repositorio                 :prep2, after prep1, 5m
    Verificar kernel headers           :prep3, after prep2, 5m

    section Build (primera vez)
    docker compose build (imagen)      :build1, after prep3, 10m
    ./configure dentro del contenedor  :build2, after build1, 5m
    make -j$(nproc) compilar todo      :crit, build3, after build2, 40m
    inject_modversions.py              :build4, after build3, 2m

    section Build (con caché)
    Rebuild incremental                :cache1, after build4, 2m

    section Validación
    make check (tests)                 :test1, after build4, 10m
    Validar 7 artefactos               :test2, after test1, 2m

    section Deploy en host
    Extract artefactos                 :ext1, after test2, 1m
    Install (modprobe)                 :inst1, after ext1, 1m
    Verify (5 checks)                  :ver1, after inst1, 1m

    section Producción
    Deploy en VPS                      :vps1, after ver1, 60m
    Verify en VPS                      :vps2, after vps1, 5m
```

---

## Diagrama 7 — Arquitectura de red SS7 completa

> Mapa de los nodos de una red SS7 típica y dónde encaja OpenSS7.

```mermaid
graph TB
    subgraph MOBILE["Red Móvil (GSM/UMTS)"]
        MS["MS\n(Mobile Station\nTeléfono móvil)"]
        BTS["BTS/NodeB\n(Antena)"]
        BSC["BSC/RNC\n(Controlador de radio)"]
        MSC_A["MSC-A\n(Mobile Switching Center)\nCentral visitada"]
        HLR["HLR\n(Home Location Register)\nBD de abonados"]
        VLR["VLR\n(Visitor Location Register)\nRegistro temporal)"]
        MS --> BTS --> BSC --> MSC_A
        MSC_A --> VLR
    end

    subgraph SS7CORE["Red de Señalización SS7"]
        STP1["STP\n(Signal Transfer Point\nEnrutador SS7)"]
        STP2["STP\n(redundante)"]
        SCP["SCP\n(Service Control Point)\nLógica de servicios"]
        STP1 <--> STP2
        STP1 --> SCP
        STP2 --> SCP
    end

    subgraph FIXED["Red Fija (PSTN)"]
        SSP1["SSP/TDX\n(Switching Point\nCentral local)"]
        SSP2["SSP/TDX\n(Central destino)"]
        SSP1 <-->|"circuitos de voz"| SSP2
    end

    subgraph VOIP["Red IP / VoIP"]
        GW_SIGTRAN["🖥️ Servidor OpenSS7\n(streams.ko + SIGTRAN)\nGateway SS7↔IP"]
        SOFTSWITCH["Softswitch\n(Media Gateway Controller)"]
        IP_NET["Red IP\n(SCTP/IP)"]
        GW_SIGTRAN <-->|"SIP"| SOFTSWITCH
        SOFTSWITCH <--> IP_NET
    end

    subgraph EMPRESA_NET["Empresa / Call Center"]
        PBX_E["PBX IP\n(Asterisk)"]
        IP_NET_E["LAN de la empresa"]
        PHONES["Teléfonos IP\ny softphones"]
        IP_NET_E --> PBX_E
        PHONES --> IP_NET_E
    end

    MSC_A <-->|"SS7 MAP"| HLR
    MSC_A <-->|"SS7 MTP"| STP1
    SSP1 <-->|"SS7 MTP"| STP1
    SSP2 <-->|"SS7 MTP"| STP2

    GW_SIGTRAN <-->|"SIGTRAN M3UA/SCTP"| STP1
    GW_SIGTRAN <-->|"SIP/RTP"| PBX_E
    PBX_E --> PHONES

    style GW_SIGTRAN fill:#27ae60,color:#fff,stroke:#1e8449
    style SS7CORE fill:#ffe4e1,stroke:#e74c3c
    style MOBILE fill:#e8f4fd,stroke:#2980b9
    style FIXED fill:#fef9e7,stroke:#f39c12
    style VOIP fill:#e8f8e8,stroke:#27ae60
    style EMPRESA_NET fill:#f5f5f5,stroke:#95a5a6
```

---

## Cómo usar estos diagramas

### En mermaid.live (más fácil)

1. Abrir **https://mermaid.live**
2. Borrar el ejemplo que aparece en el editor izquierdo
3. Copiar el contenido del bloque ` ```mermaid ` (sin las comillas de markdown)
4. El diagrama aparece instantáneamente a la derecha
5. Botón **"PNG"** para descargar como imagen

### En GitHub / GitLab

Los archivos `.md` con bloques ` ```mermaid ` se renderizan automáticamente en la vista web del repositorio. No necesitas hacer nada.

### En VSCode

Instalar la extensión **"Markdown Preview Mermaid Support"** y usar `Ctrl+Shift+V` para preview.

### Exportar a PNG en alta resolución

Para presentaciones:
1. Ir a **https://mermaid.live**
2. Pegar el diagrama
3. Click en **Actions** → **PNG** → ajustar escala a 2x o 3x
4. Descargar

---

*Volver al índice: [README.md](README.md)*
