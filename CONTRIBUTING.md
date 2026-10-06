# Contribuir a SpiderToMP3

## Preparar el entorno

Usa Python 3.12 o 3.13, FFmpeg y ffprobe en el `PATH`. En Linux o Git Bash:

```bash
source ./setup-env.sh
python -m pip install -r requirements-dev.txt
python -m ruff format --check .
python -m ruff check .
python -m mypy --follow-imports=skip services/privacy.py services/url_parser.py services/error_help.py
python -m unittest discover -s tests -v
```

Los cambios en la interfaz se pueden revisar con `QT_QPA_PLATFORM=offscreen`
en sistemas sin pantalla. Antes de proponer una Release, comprueba también los
ejecutables de Windows y Linux generados por Actions.

## Proponer un cambio

Abre un issue o un pull request que explique el problema, cómo reproducirlo y
qué comprobaste. Incluye capturas si afectan a la interfaz. Para fallos de una
fuente, indica el sitio, el tipo de enlace y la versión de `yt-dlp`; evita pegar
URLs con tokens, cookies, datos de sesión o rutas personales. Revisa también
el informe exportado antes de adjuntarlo: el filtro automático no sustituye a
una revisión humana.

La versión se define en `config.py` y las notas públicas en `CHANGELOG.md`.
No crees una etiqueta `vX.Y.Z` hasta que ambas coincidan y la versión esté
lista para publicar.
