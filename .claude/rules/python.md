# Reglas Python (deploy.py)

## Estilo
- PEP 8 estricto
- Type hints en todas las funciones (parametros y retorno)
- Docstrings en español (PEP 257)
- Comentarios en español
- Nombres de variables/funciones en ingles

## Dependencias
- SOLO standard library de Python 3 (subprocess, argparse, pathlib, shutil, os, sys, json)
- CERO dependencias externas — deploy.py debe funcionar en cualquier sistema con Python 3
- No usar requirements.txt para deploy.py (no hay dependencias)

## Estructura de deploy.py
- Un solo archivo deploy.py (no crear paquetes ni modulos separados)
- Subcomandos via argparse: build, test, extract, install, verify, uninstall
- Funciones claras por subcomando
- Exit codes: 0 = exito, 1 = error
- Capturar subprocess errors y mostrar mensajes claros

## Ejecucion de comandos
- Usar subprocess.run() con check=True para comandos criticos
- Capturar stdout/stderr para logging
- Timeout razonable para operaciones largas (build puede tomar 30+ min)
- Manejar Ctrl+C (KeyboardInterrupt) limpiamente
