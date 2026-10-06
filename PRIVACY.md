# Privacidad y datos locales

SpiderToMP3 procesa los enlaces que añades con `yt-dlp` y descarga el audio
en la carpeta que eliges. La comprobación de actualizaciones consulta la
última Release pública de GitHub una vez al día, o cuando usas la opción de
Ayuda. Las descargas contactan con los sitios de origen de los enlaces.

La aplicación guarda preferencias mediante `QSettings`. En Linux suelen estar
en `~/.config/SpiderToMP3/SpiderToMP3.conf`; en Windows, en la configuración
del usuario administrada por Qt. Si **Guardar historial y sesión** está activo,
se conservan hasta 20 enlaces recientes y la cola para reanudarla. Esos
enlaces se guardan completos, incluidos sus parámetros. Puedes desactivar la
opción y usar **Borrar historial** para eliminar recientes y cola guardada.
Los archivos de audio descargados no se borran al limpiar el historial ni al
desinstalar la aplicación.

El registro visible, el texto copiado y el informe exportado ocultan parámetros
de URL, credenciales habituales y la ruta de la carpeta personal. El filtro no
garantiza que cualquier dato sensible quede oculto; revisa un informe antes
de compartirlo. La aplicación no ofrece actualmente autenticación mediante
cookies del navegador y no las copia a preferencias. El archivo opcional
`.spidertomp3-archive.txt` en la carpeta de salida guarda identificadores de
origen para evitar descargas repetidas.

Las listas CSV y M3U exportadas son archivos de intercambio y conservan las
URLs de origen completas, incluidos sus parámetros. Guárdalas y compártelas
solo cuando sepas que esos enlaces no contienen datos privados.

Al importar un podcast RSS, la aplicación consulta el feed que indiques. Si
guardas historial y sesión, conserva su dirección, los identificadores de
episodios completados y las URLs pendientes para reconocer episodios nuevos.
**Borrar historial** también elimina estos datos.

**Buscar en MusicBrainz** envía a MusicBrainz el título y el artista que
aceptes en la vista previa. La consulta solo ocurre cuando pulsas ese botón.
La coincidencia elegida se usa para etiquetar el audio y no se guarda como
preferencia permanente.
