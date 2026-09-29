# SpiderToMP3

Aplicación de escritorio para descargar audio de enlaces compatibles con `yt-dlp`.

## Requisitos

- Python 3.12 o superior (la CI comprueba 3.12 y 3.13).
- FFmpeg en el `PATH` para convertir el audio al formato elegido.

## Instalación

```bash
python -m venv .venv
```

En Windows, activa el entorno con `.venv\Scripts\activate`. En Linux o macOS,
usa `source .venv/bin/activate`. Después instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

Los módulos de la aplicación (`controllers/`, `models/`, `services/` y `views/`)
están en la raíz del repositorio. Escribe uno o varios enlaces, elige la carpeta
de salida y el formato, y pulsa **Descargar**.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas simulan `yt-dlp`; no descargan contenido ni necesitan FFmpeg. GitHub
Actions las ejecuta en Linux y Windows con Python 3.12 y 3.13.

## Ejecutables para Windows y Bazzite

Al pasar las pruebas, GitHub Actions genera `SpiderToMP3.exe` para Windows y
`SpiderToMP3-linux-x86_64` para Linux de 64 bits. Abre la ejecución del workflow
**Tests** en la pestaña **Actions** y descarga `SpiderToMP3-Windows-Linux.zip`
desde **Artifacts**. Ese archivo contiene los dos ejecutables.

En Bazzite, extrae el ZIP y ejecuta:

```bash
chmod +x SpiderToMP3-linux-x86_64
./SpiderToMP3-linux-x86_64
```

El binario Linux se construye en Ubuntu 24.04 para equipos x86_64. Ambos
ejecutables incluyen Python y las dependencias de la app, pero necesitan FFmpeg
disponible en el `PATH` del sistema (`command -v ffmpeg` en Bazzite).

## Próximas mejoras

Consulta el [TODO de mejoras](TODO.md) para ver las tareas priorizadas.
