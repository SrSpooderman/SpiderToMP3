# Compilaciones reproducibles

`requirements.txt` contiene las dependencias directas de ejecución y
`requirements-build.txt` solo PyInstaller. Los archivos de `locks/` fijan
también las dependencias transitivas y sus hashes para Windows x86_64 y Linux
x86_64. La CI usa Python 3.12 y 3.13 en las pruebas, y 3.13 al compilar.

Para regenerar los seis bloqueos tras cambiar una dependencia:

```bash
python -m pip install -r requirements-dev.txt
python -m scripts.lock_dependencies
```

Revisa el diff de cada bloqueo. La CI instala con `pip --require-hashes`, por
lo que rechaza versiones o artefactos que no coincidan. Las compilaciones
publicadas incluyen `BUILD-INFO.txt`, con las versiones bloqueadas, el SHA-256
de cada bloqueo de compilación y el tamaño de ambos ejecutables. Compara esos
tamaños entre Releases antes de optimizar PyInstaller.

El bloqueo Linux usa `manylinux_2_34`, requerido por los wheels actuales de
PySide6; los ejecutables se construyen en Ubuntu 24.04. Una actualización de
PySide6 o del sistema base debe comprobarse de nuevo en una instalación real.
