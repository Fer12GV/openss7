# OpenSS7 — Panel de Monitoring (Portainer)

## Acceso al Panel Web

| Dato | Valor |
|------|-------|
| **URL** | http://129.121.60.55:9000 |
| **Usuario** | admin |
| **Password** | OpenSS7admin2026! |

## Que puede ver el cliente

Al ingresar al panel, el cliente puede verificar visualmente:

1. **Contenedores activos** — En el menu lateral "Containers":
   - `openss7-runtime` — Stack OpenSS7 desplegado (debe estar en estado **Running**)
   - `openss7-portainer` — El propio panel de monitoring

2. **Imagenes Docker** — En el menu lateral "Images":
   - `openss7-builder:latest` (~992 MB) — Imagen con OpenSS7 compilado
   - `portainer/portainer-ce:latest` (~229 MB) — Imagen del panel

3. **Volumenes** — En el menu lateral "Volumes":
   - `openss7-build-cache` — Cache de compilacion
   - `openss7-portainer-data` — Datos del panel

## Verificacion rapida

El cliente solo necesita confirmar:
- [ ] Abrir http://129.121.60.55:9000 en el navegador
- [ ] Login con las credenciales de arriba
- [ ] Ver que `openss7-runtime` esta en estado **Running** (icono verde)

## Notas

- El panel se reinicia automaticamente si la VPS se reinicia (`restart: unless-stopped`)
- Portainer es de solo lectura para verificacion — no se requiere accion del cliente
- Si el panel no carga, contactar al administrador para verificar el estado del servidor
