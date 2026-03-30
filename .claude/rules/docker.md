# Reglas Docker

## Build containerizado
- Docker es el UNICO entorno de compilacion. NUNCA compilar OpenSS7 directamente en el host
- El Dockerfile debe ser auto-contenido: instalar TODAS las dependencias necesarias
- `docker compose up --build` debe funcionar en cualquier Linux con Docker instalado

## Volumenes
- Fuentes OpenSS7 montadas como volumen (preferir read-only)
- Kernel headers del host montados desde `/lib/modules/$(uname -r)`
- Directorio de salida para artefactos compilados
- Cache de compilacion para builds incrementales

## Imagen base
- Debian como base primaria (build-essential + dependencias)
- Opcion CentOS como alternativa si el cliente lo requiere
- Pinear version de imagen base para reproducibilidad

## Buenas practicas
- No usar `docker exec` manualmente — todo via deploy.py
- Limpiar contenedores despues del build
- No almacenar secretos en la imagen
- Usar .dockerignore para excluir archivos innecesarios
