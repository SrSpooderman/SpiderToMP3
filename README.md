# SpiderToMP3

Aplicación de escritorio para descargar audio de enlaces compatibles con `yt-dlp`.
Procesa cada audio de una lista por separado, muestra el estado de la cola y
permite reintentar cada elemento fallido y consultar su error. La descarga se ejecuta en un proceso
separado para poder cancelarla incluso durante una conversión.

## Requisitos

- Python 3.12 o superior (la CI comprueba 3.12 y 3.13).
- FFmpeg en el `PATH` para convertir el audio al formato elegido.

## Instalación

Desde la raíz del repositorio, ejecuta este mismo comando en Bash de Linux o en
Git Bash de Windows:

```bash
source ./setup-env.sh
```

El script crea `.venv`, lo activa en la terminal actual e instala
`requirements.txt`. Si el entorno ya existe, lo activa y solo vuelve a instalar
dependencias cuando cambia ese archivo. Repite el mismo comando al abrir una
terminal nueva. Para salir, ejecuta `deactivate`.

## Uso

```bash
python main.py
```

Para consultar la versión desde el código fuente: `python main.py --version`.
La ventana también la muestra en **Ayuda → Acerca de SpiderToMP3**.

## Enlaces compatibles

Se aceptan enlaces HTTP y HTTPS que `yt-dlp` pueda analizar. Una URL directa a
un archivo WAV público se usa en las pruebas automáticas; también se pueden
probar enlaces públicos de vídeo o listas de YouTube. El soporte de cada sitio
depende de la versión de `yt-dlp` incluida y puede cambiar cuando cambia el
sitio. Si un enlace deja de funcionar, comprueba primero que se abre en el
navegador, que no exige iniciar sesión y que la aplicación está actualizada.

Los enlaces de Spotify se rechazan con un mensaje claro: no contienen el audio
descargable para esta aplicación. Si falta FFmpeg o `ffprobe`, hay que instalarlos
y asegurarse de que ambos aparecen en el `PATH`. Un archivo existente nunca se
sobrescribe automáticamente.

## Actualizaciones

El ejecutable comprueba una vez al día si hay una nueva Release estable y avisa
con la versión y sus notas. También puedes usar **Ayuda → Buscar actualizaciones**.
Solo se instala si pulsas **Actualizar**: la app descarga el archivo de tu sistema,
comprueba su tamaño y su SHA-256 con `SHA256SUMS`, cierra la ventana, sustituye
el ejecutable y abre la nueva versión. Durante la descarga puedes cancelar.
Si hay una conversión en curso, termina o cancélala antes de actualizar.

En Linux se actualiza el ejecutable de `~/.local/bin` instalado por el script,
o el binario portable desde la carpeta donde se ejecutó. En Windows se sustituye
el `.exe` portable en su carpeta. Necesitas permiso de escritura en esa carpeta;
si no lo tienes, descarga la Release e instálala manualmente. Se deja una copia
del ejecutable anterior con el sufijo `.previous` (Windows añade un número).
Al ejecutar desde el código fuente, **Buscar actualizaciones** abre la página de
la Release para que puedas actualizar el repositorio por tu cuenta.

Esta función llega con `v0.2.0`: las versiones anteriores no pueden ofrecer el
aviso y deben actualizarse manualmente la primera vez.

Los módulos de la aplicación (`controllers/`, `models/`, `services/` y `views/`)
están en la raíz del repositorio. Escribe enlaces, elige la carpeta y el formato,
y pulsa **Descargar**. La app analiza los enlaces y muestra una vista previa:
desmarca audios o cambia su orden antes de confirmar. El límite inicial de cada
lista es 200 audios y se puede ajustar en la ventana.

Durante la descarga, la cola muestra el avance por audio, la velocidad y el
tiempo estimado si la fuente los proporciona. La conversión se indica por
separado. Puedes cancelar, reanudar pendientes, reintentar fallidos o el audio
seleccionado, quitar elementos y abrir el archivo o su carpeta al terminar.
También puedes usar **Pegar del portapapeles** (`Ctrl+Mayús+V`) o soltar URLs y archivos
`.txt` en la ventana. La cola se guarda para reanudarla tras un cierre; desmarca
**Guardar historial y sesión** si no quieres conservar enlaces, y usa **Borrar
historial** para eliminar los ya guardados.

**Importar lista** abre archivos `.csv`, `.m3u` y `.m3u8`; **Exportar lista**
guarda la cola con título, URL de origen, estado y ruta local. También se
aceptan M3U corrientes con enlaces web o archivos locales. El CSV usa las
columnas `title,url,status,path`. Una exportación conserva las URLs completas,
así que revísala antes de compartirla.

**Podcast RSS** consulta un feed público y muestra los episodios antes de
añadirlos. Se seleccionan de inicio los que todavía no figuran como procesados.
La aplicación descarga únicamente las URLs de audio que el feed publica como
`enclosure`; recuerda el último episodio completado y otros episodios ya
procesados si está activado **Guardar historial y sesión**. No hay suscripción
ni descarga automática en segundo plano.

En **Duplicados**, **Omitir** es la opción inicial; **Renombrar** crea un nombre
libre y **Preguntar** pide una decisión al detectar un archivo existente en la
vista previa. Si el nombre final cambia después del análisis, la app avisa y no
sobrescribe. **Omitir ID ya descargados** crea un registro opcional en la carpeta
de salida para no repetir audios aunque cambies el patrón de nombre. Los fallos
temporales de red se reintentan con una espera breve; el número de intentos es
configurable.

En **Preferencias**, puedes activar por separado las etiquetas de título,
artista y álbum que proporcione la fuente, y la portada cuando exista. La
portada se admite en MP3, M4A, Opus y FLAC; WAV no ofrece esa opción. Si el
archivo de origen ya usa el formato de audio elegido, `yt-dlp` conserva el
audio sin reconvertirlo.

En la vista previa, selecciona un audio y usa **Buscar en MusicBrainz** si
quieres completar sus etiquetas. Verás varias grabaciones con artista, álbum
y puntuación, y tendrás que elegir una antes de que se escriban. La consulta
solo se envía al pulsar ese botón; no cambia el nombre del archivo ni busca
otra fuente de audio.

El registro visible, el portapapeles y el informe exportado ocultan parámetros
de URL, credenciales comunes y la ruta de la carpeta personal. Los enlaces
guardados en preferencias siguen siendo completos para permitir reanudar; usa
la opción de historial si no quieres guardarlos. **Limpiar restos** ofrece borrar
solo archivos parciales identificados como nuevos de la sesión y pide confirmación.
Hay temas claro, oscuro y de alto contraste; **Sistema** sigue la preferencia
de apariencia del escritorio.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas unitarias simulan `yt-dlp`. Las pruebas de integración generan un WAV
local y lo convierten con FFmpeg sin acceder a Internet. GitHub Actions ejecuta
las pruebas en Linux y Windows con Python 3.12 y 3.13.

## Versiones y ejecutables

La versión se define una sola vez en `APP_VERSION` de `config.py`. Seguimos
`MAJOR.MINOR.PATCH`: corrección, función compatible y cambio incompatible,
respectivamente. Antes de publicar una versión, añade sus notas a
[CHANGELOG.md](CHANGELOG.md) y crea una etiqueta Git `vX.Y.Z` que coincida con
`APP_VERSION`. El workflow verifica la coincidencia, prueba ambos sistemas y
publica una GitHub Release. Cada publicación se inicia al crear su etiqueta;
el código por sí solo no la publica.

En **Releases** de este repositorio, cada versión tendrá cinco descargas separadas:

- `SpiderToMP3-vX.Y.Z-windows-x86_64.exe` para Windows.
- `SpiderToMP3-vX.Y.Z-linux-x86_64.tar.gz` con el ejecutable e instalador de Linux.
- `SHA256SUMS` para comprobar ambas descargas, el desinstalador y el manifiesto.
- `uninstall-bazzite.sh` para quitar la instalación de usuario en Linux.
- `BUILD-INFO.txt` con tamaños, versiones de dependencias y hashes de los bloqueos usados.

Las compilaciones de ramas y pull requests dejan los ejecutables de prueba en
**Actions → Tests → Artifacts** durante un día. Las versiones para usuarios se
descargan desde **Releases**.

### Bazzite, Ubuntu y Fedora

En Bazzite, Ubuntu (24.04 o posterior) y Fedora para x86_64, extrae el paquete
Linux y ejecuta el mismo instalador para tu usuario:

```bash
tar -xzf SpiderToMP3-vX.Y.Z-linux-x86_64.tar.gz
sh install-bazzite.sh
```

Para desinstalar, descarga `uninstall-bazzite.sh` de la misma Release y ejecuta
`sh uninstall-bazzite.sh`. Solo borra el binario, el lanzador y los iconos que
instala en `~/.local`; conserva las preferencias y los audios descargados.

El nombre `install-bazzite.sh` se conserva para que las versiones anteriores
puedan actualizarse. El script instala un icono PNG para el menú y actualiza
la caché de aplicaciones en KDE cuando está disponible. Si actualizas desde
una versión anterior, la app también corrige el icono al abrirse. Después abre
**SpiderToMP3** desde el menú. También puedes ejecutar el binario
sin instalarlo con `chmod +x SpiderToMP3-linux-x86_64` y
`./SpiderToMP3-linux-x86_64`.
La elección de formato para Bazzite se explica en
[packaging/OPTIONS.md](packaging/OPTIONS.md).

El binario Linux se construye en Ubuntu 24.04 para equipos x86_64; la
compatibilidad con Fedora debe comprobarse en una instalación real. Ambos
ejecutables incluyen Python y las dependencias de la app, pero necesitan FFmpeg
disponible en el `PATH` del sistema (`command -v ffmpeg`).
Comprueba también `command -v ffprobe`. En Bazzite hace falta que ambos comandos
sean visibles para el ejecutable desde la sesión gráfica; la prueba en una
instalación limpia de Bazzite sigue pendiente.

Para volver a una versión anterior, descarga sus archivos desde esa Release y
ejecuta de nuevo el instalador de Linux, o usa su `.exe` en Windows.

La app guarda la carpeta, formato, calidad y hasta 20 enlaces recientes cuando
el historial está activado. Los enlaces deben ser HTTP o HTTPS; se admiten comas
dentro de una URL. El registro de pantalla conserva las últimas 1000 líneas.

## Próximas mejoras

Consulta el [TODO de mejoras](TODO.md) para ver las tareas priorizadas.

Para contribuir o reportar fallos, consulta [CONTRIBUTING.md](CONTRIBUTING.md).
El tratamiento de enlaces e historial se explica en [PRIVACY.md](PRIVACY.md).
El procedimiento para actualizar extractores está en
[docs/yt-dlp-updates.md](docs/yt-dlp-updates.md).
Los bloqueos de dependencias y las compilaciones se describen en
[docs/builds.md](docs/builds.md).
