# OpenSS7 Build Environment
# Compila OpenSS7 dentro de Docker contra los kernel headers del host
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Dependencias de compilacion
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    make \
    # Autotools
    autoconf \
    automake \
    libtool \
    libtool-bin \
    pkg-config \
    # Parser generators
    bison \
    flex \
    # Documentacion
    groff \
    groff-base \
    texinfo \
    texlive-base \
    texlive-latex-base \
    ghostscript \
    # Internacionalizacion
    gettext \
    autopoint \
    # Kernel module build
    kmod \
    # Librerias opcionales
    libpcap-dev \
    libsctp-dev \
    lksctp-tools \
    # Scripting (requerido por build system)
    perl \
    libperl-dev \
    libdate-calc-perl \
    libdate-manip-perl \
    libtimedate-perl \
    gawk \
    # TCL + SWIG (necesario para generar bindings TCL de OpenSS7)
    tcl-dev \
    swig \
    # SNMP
    libsnmp-dev \
    snmp \
    # SSL/Certificates
    openssl \
    ca-certificates \
    # Networking
    net-tools \
    # Utilidades
    git \
    gzip \
    bzip2 \
    xz-utils \
    cpio \
    lsb-release \
    dpkg-dev \
    debhelper \
    fakeroot \
    dh-make \
    # Python3 para inject_modversions.py (post-build step)
    python3 \
    # binutils para objcopy y readelf (inject_modversions.py)
    binutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openss7

# El entrypoint usa el script desde el volumen montado (/opt/openss7/scripts/docker-build.sh)
# para que los cambios al script no requieran reconstruir la imagen Docker.
# COPY es solo fallback de referencia para builds standalone sin volumen.
COPY scripts/docker-build.sh /usr/local/bin/docker-build.sh
RUN chmod +x /usr/local/bin/docker-build.sh

# Usar siempre la version del script desde la fuente montada.
# Se invoca con bash explicitamente para no depender del bit +x en el volumen del host.
ENTRYPOINT ["/bin/bash", "/opt/openss7/scripts/docker-build.sh"]
