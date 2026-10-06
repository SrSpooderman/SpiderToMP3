# Actualizar yt-dlp

`yt-dlp` se fija en `requirements.txt` y se incluye en cada ejecutable. Cambiar
el paquete del sistema no actualiza SpiderToMP3 instalado: hay que publicar una
nueva versión de la aplicación.

## Antes de cambiar la versión

1. Revisa las [notas de yt-dlp](https://github.com/yt-dlp/yt-dlp/releases) y
   los problemas conocidos de los extractores que usan los usuarios.
2. Prepara enlaces de prueba públicos y con permiso de descarga para un audio
   directo, un vídeo y una lista. No guardes en el repositorio enlaces con
   tokens, cookies ni contenido privado.
3. En un entorno aparte con la versión candidata, prueba cada enlace con
   `python -m yt_dlp --simulate --verbose URL`. Comprueba título, duración,
   lista y formato de audio. Si falla, compara con la versión fijada actual.
4. Cambia la versión en `requirements.txt`, instala las dependencias y ejecuta
   `python -m unittest discover -s tests -v`. Prueba además una conversión
   manual de un audio público en Windows y Linux/Bazzite, incluidos cancelar
   y reintentar.
5. Construye ambos ejecutables mediante Actions y repite la prueba con los
   artefactos, ya que cada uno lleva su propia copia de `yt-dlp`. Registra la
   versión de `yt-dlp` y de FFmpeg en las notas de Release.

## Cuando deja de funcionar un enlace

Comprueba primero si abre en el navegador y si exige inicio de sesión. Consulta
la versión de SpiderToMP3 y la versión de `yt-dlp` indicada por
`requirements.txt` para esa Release. Reproduce el fallo con
`python -m yt_dlp --simulate --verbose URL` en un entorno aparte y compara con
una versión reciente de `yt-dlp`. La [FAQ de yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
advierte que un sitio listado puede cambiar o dejar de funcionar. Antes de
compartir la salida `--verbose`, elimina URLs privadas, credenciales y rutas
personales.
