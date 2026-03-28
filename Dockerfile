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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openss7

# El script de build se ejecuta como entrypoint
COPY scripts/docker-build.sh /usr/local/bin/docker-build.sh
RUN chmod +x /usr/local/bin/docker-build.sh

ENTRYPOINT ["/usr/local/bin/docker-build.sh"]
