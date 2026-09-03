# SpiderToMP3

Aplicacion de escritorio para convertir enlaces compatibles con `yt-dlp` a audio.
Ahora esta separada en capas para que sea facil anadir historial, perfiles,
empaquetado, tests o nuevas fuentes.

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Para exportar a `mp3`, `wav` o `flac`, instala FFmpeg y asegurate de que
`ffmpeg` esta disponible en el `PATH`.

## Uso

```bash
python -m spidertomp3
```