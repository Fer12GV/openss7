# Profundidad Técnica — Módulos de Kernel y el Problema modversions

> **Nivel:** Avanzado
> **Objetivo:** Entender por qué los módulos de kernel de OpenSS7 requieren un post-procesado especial, cómo funciona la verificación de símbolos en Linux, y cómo se resolvió el problema.

---

## 1. ¿Qué es un módulo de kernel (.ko)?

Un archivo `.ko` (Kernel Object) es código C compilado que puede cargarse dinámicamente en el kernel de Linux en tiempo de ejecución. A diferencia de una librería `.so` (que corre en espacio de usuario), un `.ko` corre **dentro del kernel** con acceso total al hardware.

```
Espacio de usuario (userspace):
  aplicación → glibc → syscall → kernel

Espacio de kernel (kernelspace):
  streams.ko → llama directamente a funciones del kernel
              → accede directamente a memoria del kernel
              → no hay capa de protección entre medio
```

### ¿Por qué son peligrosos?

Un módulo mal escrito puede:
- Provocar un kernel panic (equivalente al "pantalla azul" en Linux)
- Corromper memoria del kernel
- Abrir vulnerabilidades de seguridad

Por eso Linux tiene mecanismos de verificación antes de cargar un módulo.

---

## 2. El sistema de verificación de módulos en Linux

### 2.1 vermagic — Compatibilidad de versión

Cada módulo .ko tiene una cadena `vermagic` que debe coincidir exactamente con el kernel:

```bash
modinfo streams.ko | grep vermagic
# vermagic: 5.15.0-173-generic SMP mod_unload modversions
```

El kernel rechaza el módulo si el vermagic no coincide. Esto evita cargar un módulo compilado para un kernel diferente.

### 2.2 CONFIG_MODVERSIONS — Verificación de símbolos (el problema central)

Cuando el kernel está compilado con `CONFIG_MODVERSIONS=y` (el caso en Ubuntu/Debian), el kernel verifica que **cada símbolo que el módulo usa existe en el kernel con exactamente la misma firma**.

¿Cómo funciona?

```
Durante la compilación del kernel:
  función kmalloc() → CRC calculado = 0xABCD1234

Durante la compilación del módulo:
  módulo usa kmalloc → guarda CRC = 0xABCD1234 en __versions

Al cargar el módulo:
  kernel verifica: CRC en __versions == CRC del kernel actual
  ✅ Match → módulo cargado
  ❌ No match → ERROR: Exec format error
```

### 2.3 La sección `__versions`

Cada módulo .ko debe tener una sección ELF llamada `__versions` que contiene una tabla de estructuras:

```c
// Definición en include/linux/module.h
struct modversion_info {
    unsigned long crc;    // CRC del símbolo (8 bytes en sistemas 64-bit)
    char name[MODULE_NAME_LEN]; // nombre del símbolo (56 bytes)
};
// Total: 64 bytes por símbolo
```

Ejemplo de contenido de `__versions`:

```
CRC (8 bytes)     | Nombre del símbolo (56 bytes)
0xABCD1234 00..  | kmalloc\0\0\0\0...
0x5678EFAB 00..  | kfree\0\0\0\0...
0x1234CDEF 00..  | printk\0\0\0\0...
... (un entry por cada símbolo del kernel que usa el módulo)
```

---

## 3. El problema en OpenSS7

### 3.1 ¿Por qué OpenSS7 no genera `__versions`?

OpenSS7 usa su propio sistema de post-procesado llamado `modpost.awk` en lugar del `modpost` estándar del kernel.

El `modpost` estándar del kernel genera `__versions` cuando se compila con el flag `-m`. El de OpenSS7 fue modificado y no lo hace.

**¿Por qué no simplemente agregar `-m`?**

Cuando se intentó añadir `-m` a `MODPOST_OPTIONS`, el build fallaba con **2439 errores** como este:

```
ld -r: error: output sections stripped: __ksymtab_*
```

Causa: `ld -r` (enlazado relocatable) pierde la flag `O` en las secciones `__ksymtab_*` cuando se procesa con `-m`. Es un bug de interacción entre el modpost de OpenSS7 y el linker.

### 3.2 Resultado: módulos sin `__versions`

```bash
# Verificar con readelf
readelf -S build-output/modules/streams.ko | grep __versions
# (sin output = sección no existe)

# Al intentar cargarlo:
modprobe streams
# modprobe: ERROR: could not insert 'streams': Exec format error
```

El kernel Ubuntu rechaza el módulo porque `CONFIG_MODVERSIONS=y` y no hay sección `__versions`.

---

## 4. La solución: inject_modversions.py

### 4.1 Concepto

En lugar de modificar el sistema de build de OpenSS7, se inyecta la sección `__versions` en cada .ko **después** de que el build termina, como un paso de post-procesado.

```
Build normal de OpenSS7:
  make → streams.ko (sin __versions)

Post-procesado (nuevo):
  inject_modversions.py → streams.ko (con __versions inyectado)
```

### 4.2 Fuente de verdad: Module.symvers

El kernel de Linux, al compilarse, genera `Module.symvers` — un archivo que lista todos los símbolos exportados con sus CRCs:

```
# Formato de Module.symvers
# CRC          símbolo               módulo               tipo_export
0xabcd1234   kmalloc               vmlinux              EXPORT_SYMBOL
0x5678abcd   kfree                 vmlinux              EXPORT_SYMBOL
0x12345678   alloc_skb             net/core/skbuff      EXPORT_SYMBOL
...
```

Este archivo vive en `/lib/modules/$(uname -r)/build/Module.symvers` y es la fuente de CRCs exactos del kernel activo.

### 4.3 Algoritmo de inject_modversions.py

```python
# Pseudocódigo del algoritmo

Para cada archivo .ko en el directorio de build:

    1. VERIFICAR si ya tiene __versions (evitar doble inyección)
       readelf -S module.ko | grep __versions
       Si existe → skip

    2. EXTRAER símbolos undefined del módulo
       readelf -s module.ko
       Filtrar: GLOBAL + UND (símbolos que usa pero no define)
       Resultado: lista de nombres ["kmalloc", "kfree", "printk", ...]

    3. BUSCAR CRCs para cada símbolo
       Leer /lib/modules/KERNEL/build/Module.symvers
       Leer build_dir/Module.symvers (símbolos de otros módulos OpenSS7)
       Construir diccionario: {"kmalloc": 0xABCD1234, ...}

    4. CONSTRUIR blob binario
       Para cada símbolo con CRC encontrado:
           entry = struct.pack('<Q', crc)           # 8 bytes, little-endian
           entry += name.encode('ascii')            # bytes del nombre
           entry += b'\x00' * (56 - len(name))     # padding a 56 bytes
           blob += entry                            # 64 bytes por entrada

    5. INYECTAR con objcopy
       Escribir blob en archivo temporal (/tmp/versions_XXXX.bin)
       Ejecutar:
           objcopy
               --add-section __versions=/tmp/versions_XXXX.bin
               --set-section-flags __versions=alloc,load,readonly,data
               module.ko
```

### 4.4 Código real (fragmento principal)

```python
def _build_versions_blob(
    symbols: List[str],
    crc_map: Dict[str, int]
) -> bytes:
    """
    Construye el blob binario para la seccion __versions.
    Formato: struct modversion_info[] — 64 bytes por entrada.
    """
    CRC_BYTES = 8      # unsigned long en 64-bit
    NAME_BYTES = 56    # MODULE_NAME_LEN
    ENTRY_SIZE = 64    # CRC_BYTES + NAME_BYTES

    blob = b""
    for sym in symbols:
        if sym not in crc_map:
            continue  # símbolo sin CRC conocido — lo omitimos
        crc = crc_map[sym]
        name_bytes = sym.encode("ascii", errors="replace")
        # Truncar si es más largo que NAME_BYTES - 1 (dejar espacio para \0)
        name_bytes = name_bytes[: NAME_BYTES - 1]
        # Padding con ceros hasta NAME_BYTES
        name_bytes = name_bytes.ljust(NAME_BYTES, b"\x00")
        # CRC en little-endian, 8 bytes
        entry = struct.pack("<Q", crc & 0xFFFFFFFFFFFFFFFF) + name_bytes
        assert len(entry) == ENTRY_SIZE
        blob += entry
    return blob
```

### 4.5 La inyección con objcopy

`objcopy` es la herramienta de GNU binutils para manipular archivos objeto ELF:

```bash
# Lo que ejecuta el script
objcopy \
    --add-section __versions=/tmp/versions_abcd.bin \
    --set-section-flags __versions=alloc,load,readonly,data \
    streams.ko

# Verificar que se inyectó correctamente
readelf -S streams.ko | grep __versions
# [ 7] __versions   PROGBITS  0000..  alloc,readonly
```

### 4.6 Resultados

```
Módulos procesados: 123
Módulos inyectados: 123
Módulos omitidos (ya tenían __versions): 0
Fallos: 0

Antes: modprobe streams → Exec format error
Después: modprobe streams → streams loaded (verified)
```

---

## 5. Verificación del proceso completo

### Antes de inject_modversions

```bash
# El módulo no tiene __versions
readelf -S streams.ko | grep __versions
# (sin output)

# El kernel rechaza el módulo
modprobe streams
# modprobe: ERROR: could not insert 'streams': Exec format error

# dmesg muestra el error del kernel
dmesg | tail -5
# [12345.678] streams: disagrees about version of symbol module_layout
```

### Después de inject_modversions

```bash
# El módulo tiene __versions
readelf -S streams.ko | grep __versions
# [  7] __versions  PROGBITS  ...  alloc,readonly

# Ver cuántos símbolos tiene registrados
readelf -S streams.ko | grep -A1 __versions
# Size: 0x1000 (= 64 bytes × 64 símbolos = 64 entradas)

# El kernel acepta el módulo
modprobe streams
# (sin output = éxito)

# Verificar que está cargado
lsmod | grep streams
# streams               229376  0
```

---

## 6. Otros problemas técnicos resueltos

### 6.1 compat-kernel.h — Compatibilidad con kernel 5.x

OpenSS7 fue escrito para kernels Linux 2.6/3.x. Con kernels 5.x, más de 30 APIs del kernel cambiaron. En lugar de modificar el código fuente de OpenSS7 (que va contra las reglas del proyecto), se creó `scripts/compat-kernel.h` que se incluye automáticamente via `CFLAGS=-include compat-kernel.h`.

Ejemplos de cambios del kernel que requirieron compatibilidad:

| API | Versión donde cambió | Fix en compat-kernel.h |
|-----|---------------------|----------------------|
| `f_dentry` → `f_path.dentry` | Kernel 4.x | `#define f_dentry f_path.dentry` |
| `set_task_state()` usa `__state` | Kernel 5.14 | Macro con WRITE_ONCE |
| `get_fs()/set_fs()` eliminados | Kernel 5.10 | Stubs no-op |
| `getnstimeofday()` → `ktime_get_real_ts64()` | Kernel 5.6 | Wrapper compat |
| `proc_create_data()` → `proc_ops` | Kernel 5.6 | `#ifdef` guarded |
| `dst_ops.negative_advice` nueva firma | Kernel 5.15 | Struct variadic |
| `csum_and_copy_from_user()` 5→3 args | Kernel 5.10 | Wrapper con args |
| `net_device.queue_lock` eliminado | Kernel 5.x | `addr_list_lock` |

### 6.2 OOM durante ./configure

El proceso `config.status` de OpenSS7 intenta montar todo `/lib/modules/` en el contenedor. Con un host moderno que tiene cientos de módulos, esto causa un OOM (Out Of Memory) con exit code 137.

**Fix:** Montar solo el directorio del kernel activo:

```yaml
# docker-compose.yml — CORRECTO
volumes:
  - /lib/modules/${KERNEL_VERSION}:/lib/modules/${KERNEL_VERSION}
  # NO: - /lib/modules:/lib/modules  ← monta todo, causa OOM
```

### 6.3 vermagic y INCLUDE_VERMAGIC

OpenSS7 genera su propio `vermagic.h`. Para que el vermagic coincida con el del kernel, se agregó:

```bash
KERNEL_MODFLAGS="-DMODULE -DINCLUDE_VERMAGIC"
```

Esto le dice al compilador que incluya la información de vermagic del kernel real en lugar de la de OpenSS7.

---

## 7. Herramientas esenciales para diagnóstico

```bash
# Ver todas las secciones ELF de un módulo
readelf -S module.ko

# Ver todos los símbolos del módulo (importados y exportados)
readelf -s module.ko | grep -E "GLOBAL|UND"

# Ver información del módulo (vermagic, dependencias, parámetros)
modinfo module.ko

# Ver símbolos que exporta el kernel activo
cat /lib/modules/$(uname -r)/build/Module.symvers | grep kmalloc | head -3

# Ver por qué falló la carga de un módulo
dmesg | tail -20

# Ver dependencias de un módulo
modinfo -F depends module.ko

# Ver si un módulo ya está cargado
lsmod | grep nombre_modulo

# Verificar integridad de módulos instalados
depmod -a --verbose 2>&1 | grep streams
```

---

## 8. Estructura ELF de un módulo .ko

```
streams.ko (formato ELF de 64-bit)
├── .text          — código ejecutable del módulo
├── .data          — variables inicializadas
├── .bss           — variables no inicializadas
├── .rodata        — constantes y strings
├── __versions     — tabla de CRCs de símbolos ← INYECTADO
├── __ksymtab      — símbolos que este módulo exporta
├── __kcrctab      — CRCs de los símbolos que exporta
├── .modinfo       — metadata (vermagic, author, license, etc.)
└── .gnu.linkonce.this_module — estructura module del kernel
```

---

## 9. Por qué este fix es elegante

La alternativa habitual sería:
1. Modificar el código fuente de OpenSS7 → **prohibido** (regla del proyecto)
2. Recompilar el kernel sin `CONFIG_MODVERSIONS` → **imposible** en producción
3. Usar `insmod --force` → **peligroso** y no funciona con dependencias

La solución de inject_modversions.py:
- No toca el código fuente de OpenSS7
- No requiere recompilar el kernel
- Es reproducible y automatizada
- Usa las fuentes de verdad oficiales (Module.symvers del kernel)
- 123 módulos procesados sin un solo fallo

---

*Siguiente: [Diagramas Mermaid — Flujos y arquitectura →](06-diagramas-mermaid.md)*
