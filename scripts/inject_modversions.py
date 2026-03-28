#!/usr/bin/env python3
"""
Inyecta la seccion __versions en modulos .ko de OpenSS7.

La seccion __versions contiene CRC de cada simbolo importado por el modulo.
Es requerida por kernels compilados con CONFIG_MODVERSIONS=y.
El build de OpenSS7 con modpost.awk no genera esta seccion, por eso la
inyectamos en un paso post-build usando los datos de Module.symvers.

Formato de struct modversion_info (x86_64, kernel 5.x):
  unsigned long crc;    // 8 bytes, little-endian
  char name[56];        // 56 bytes, null-padded (MODULE_NAME_LEN = 64 - sizeof(ulong))
  // Total: 64 bytes por entrada

Uso:
  python3 inject_modversions.py <build_dir> <kernel_version>
"""

import struct
import subprocess
import sys
from pathlib import Path

# Estructura modversion_info en x86_64
CRC_BYTES = 8    # sizeof(unsigned long) en 64-bit
NAME_BYTES = 56  # MAX_PARAM_PREFIX_LEN = 64 - sizeof(unsigned long)
ENTRY_SIZE = CRC_BYTES + NAME_BYTES  # 64 bytes por entrada


def get_undefined_symbols(ko_path: Path) -> list:
    """Retorna lista de simbolos globales importados (GLOBAL UNDEFINED) del .ko."""
    result = subprocess.run(
        ["readelf", "-s", str(ko_path)],
        capture_output=True, text=True
    )
    syms = []
    for line in result.stdout.splitlines():
        parts = line.split()
        # Formato readelf: Num Value Size Type Bind Vis Ndx Name
        if len(parts) >= 8 and parts[4] == "GLOBAL" and parts[6] == "UND":
            name = parts[7]
            # Excluir simbolos de version de gcc y placeholders
            if name and not name.startswith("__gnu_") and "@" not in name:
                syms.append(name)
    return sorted(set(syms))


def has_versions_section(ko_path: Path) -> bool:
    """Verifica si el .ko ya tiene seccion __versions."""
    result = subprocess.run(
        ["readelf", "-S", str(ko_path)],
        capture_output=True, text=True
    )
    return "__versions" in result.stdout


def load_symvers(symvers_files: list) -> dict:
    """Carga archivos Module.symvers en un dict {nombre_simbolo: crc_int}."""
    crc_map = {}
    for path in symvers_files:
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text(errors="replace").splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                crc_str = parts[0].strip()
                sym = parts[1].strip()
                if crc_str.startswith("0x"):
                    try:
                        crc_map[sym] = int(crc_str, 16)
                    except ValueError:
                        pass
    return crc_map


def build_versions_blob(symbols: list, crc_map: dict) -> bytes:
    """Construye el blob binario de la seccion __versions."""
    data = b""
    for sym in symbols:
        if sym not in crc_map:
            continue
        crc = crc_map[sym]
        name_bytes = sym.encode("ascii")
        # Truncar a NAME_BYTES - 1 para garantizar terminador nulo
        if len(name_bytes) >= NAME_BYTES:
            name_bytes = name_bytes[:NAME_BYTES - 1]
        padding = NAME_BYTES - len(name_bytes)
        entry = struct.pack("<Q", crc & 0xFFFFFFFFFFFFFFFF)
        entry += name_bytes + b"\x00" * padding
        assert len(entry) == ENTRY_SIZE, f"Entry size mismatch: {len(entry)} != {ENTRY_SIZE}"
        data += entry
    return data


def inject_section(ko_path: Path, blob: bytes) -> bool:
    """Inyecta el blob como seccion __versions en el .ko usando objcopy."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(blob)
        bin_file = f.name
    try:
        result = subprocess.run([
            "objcopy",
            "--add-section", f"__versions={bin_file}",
            "--set-section-flags", "__versions=alloc,load,readonly,data",
            str(ko_path), str(ko_path),
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  objcopy error: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode == 0
    finally:
        os.unlink(bin_file)


def process_ko(ko_path: Path, crc_map: dict) -> str:
    """Procesa un .ko. Retorna 'skip', 'ok', o 'fail'."""
    if has_versions_section(ko_path):
        return "skip"
    symbols = get_undefined_symbols(ko_path)
    if not symbols:
        return "skip"
    blob = build_versions_blob(symbols, crc_map)
    if not blob:
        return "skip"
    ok = inject_section(ko_path, blob)
    return "ok" if ok else "fail"


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <build_dir> <kernel_version>", file=sys.stderr)
        return 1

    build_dir = Path(sys.argv[1])
    kernel_ver = sys.argv[2]

    kernel_symvers = Path(f"/lib/modules/{kernel_ver}/build/Module.symvers")
    build_symvers = build_dir / "Module.symvers"
    symvers_files = [str(kernel_symvers), str(build_symvers)]

    crc_map = load_symvers(symvers_files)
    if not crc_map:
        print("WARN: No se encontraron datos en Module.symvers", file=sys.stderr)
        return 0
    print(f"Simbolos cargados: {len(crc_map)} (kernel + OpenSS7)")

    ko_files = sorted(build_dir.glob("**/*.ko"))
    if not ko_files:
        print("No se encontraron archivos .ko", file=sys.stderr)
        return 1
    print(f"Procesando {len(ko_files)} modulos .ko...")

    ok_count = skip_count = fail_count = 0
    for ko in ko_files:
        status = process_ko(ko, crc_map)
        if status == "ok":
            ok_count += 1
        elif status == "skip":
            skip_count += 1
        else:
            fail_count += 1
            print(f"  FAIL: {ko.name}")

    print(f"Resultado: {ok_count} inyectados, {skip_count} sin cambios, {fail_count} fallidos")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
