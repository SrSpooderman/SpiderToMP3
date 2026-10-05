# TODO de SpiderToMP3

Punto de partida: el código de `v0.3.0` añade vista previa, una cola persistente,
control de duplicados, progreso detallado, privacidad y pruebas reales de los
ejecutables. Todavía debe publicarse y probarse como Release.
Aquí van **solo tareas pendientes**, ordenadas por impacto. Cada casilla describe
un resultado comprobable; el spider ya tiene bastante con contar patas.

## P0 · Que la Release funcione fuera de CI

- [ ] **Probar una actualización entre dos Releases.** Tras publicar la primera
  Release `v0.3.0`, comprobar en Windows y Bazzite el aviso desde `v0.2.0`, la
  descarga, cancelación, reemplazo y reinicio. Forzar también una versión nueva
  que no arranque y confirmar que se restaura `.previous` y aparece el aviso.
- [ ] **Validar `v0.3.0` publicada en instalaciones limpias.** En Bazzite,
  instalar desde la Release, abrir desde el menú en Wayland y X11, convertir un
  audio público, cancelar, reiniciar y ejecutar `uninstall-bazzite.sh`. Repetir
  conversión, cancelación y actualización con el `.exe` publicado en Windows.
  La compilación local de Linux ya superó estas pruebas en Bazzite; falta validar
  los artefactos generados por GitHub Actions y un sistema sin datos previos.

## P2 · Integraciones y formatos con sentido

- [ ] **Metadatos y portada opcionales.** Añadir etiquetas de título, artista,
  álbum y portada cuando la fuente las proporcione; probar MP3, M4A, Opus y
  FLAC por separado. Permitir conservar el audio original si ya tiene el códec
  deseado para evitar reconversiones innecesarias. `yt-dlp` documenta
  [metadatos y miniaturas](https://github.com/yt-dlp/yt-dlp#readme).
- [ ] **Enriquecimiento con MusicBrainz, solo bajo elección del usuario.** Buscar
  coincidencias de grabación para completar etiquetas, mostrar opciones antes
  de escribirlas y respetar su [identificación y límite de llamadas](https://musicbrainz.org/doc/MusicBrainz_API).
- [ ] **Podcasts por RSS.** Importar un feed público, previsualizar episodios,
  elegir nuevos y recordar el último episodio procesado. Descargar únicamente
  los archivos publicados por el feed; la suscripción automática sería un ajuste
  separado y desactivado por defecto.
- [ ] **Intercambiar listas con otros programas.** Importar y exportar `.m3u` y
  CSV con título, URL de origen, estado y ruta local. Aceptar archivos de texto
  sin exigir que el usuario pegue cada enlace a mano.
- [ ] **Evaluar Spotify sin prometer audio descargable.** La [Web API](https://developer.spotify.com/documentation/web-api)
  da acceso a metadatos bajo sus requisitos actuales, y el flujo adecuado para
  una app de escritorio es [OAuth con PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow),
  sin secreto incrustado. Revisar permisos, alcance de playlists y política
  vigente antes de implementar cualquier consulta. No convertir pistas de
  Spotify en búsquedas para descargar audio de otro sitio: Spotify
  [prohíbe facilitar descargas de su contenido](https://developer.spotify.com/documentation/web-api/reference/get-playlists-items).
- [ ] **Autenticación de sitios compatibles, opcional.** Estudiar la lectura
  temporal de [cookies del navegador](https://github.com/yt-dlp/yt-dlp#readme)
  para enlaces que requieran sesión, con consentimiento explícito, sin copiarlas
  a preferencias ni incluirlas en registros. Probarlo en Windows y Bazzite.
- [ ] **Distribución más natural en Bazzite.** Preparar un Flatpak de prueba con
  acceso acotado a carpetas elegidas y FFmpeg disponible dentro del sandbox.
  Validar la experiencia antes de considerar Flathub; [Bazzite recomienda
  Flatpak para aplicaciones gráficas](https://docs.bazzite.gg/Installing_and_Managing_Software/Flatpak/).
- [ ] **Instalador de Windows opcional.** Añadir accesos directos y desinstalación
  sin perder la descarga `.exe` portable. Comprobar qué datos quedan al
  desinstalar y documentarlo.

## P3 · Mantenimiento que evita futuras sorpresas

- [ ] **Reducir ejecuciones duplicadas de Actions.** Ejecutar `push` para `main`
  y etiquetas `v*`, y `pull_request` para PR; añadir `concurrency` para cancelar
  trabajos obsoletos de la misma rama sin cancelar una Release en curso.
- [ ] **Agrupar actualizaciones pequeñas de Dependabot.** Juntar parches y
  versiones menores por ecosistema; dejar las mayores separadas para revisar
  cambios de compatibilidad y compilación de cada plataforma.
- [ ] **Hacer reproducibles las compilaciones.** Separar dependencias directas de
  las transitivas, generar bloqueos verificables por plataforma y conservar en
  la Release información sobre las versiones usadas. Medir también el tamaño de
  los binarios antes de optimizarlos.
- [ ] **Planificar la actualización de `yt-dlp`.** Está fijado en
  `requirements.txt` y empaquetado dentro de cada ejecutable, así que los
  cambios de los sitios requieren una nueva Release. Documentar cómo probar
  extractores antes de subir la versión y cómo diagnosticar cuándo un enlace
  deja de funcionar por una versión antigua.
- [ ] **Añadir comprobaciones de calidad enfocadas.** Integrar formato/lint y
  análisis de tipos en CI; ampliar pruebas solo alrededor de la cola persistente,
  listas grandes, cancelación y archivos finales cuando esas funciones existan.
- [ ] **Documentar distribución y privacidad.** Añadir licencia, guía breve para
  contribuir, ubicación de preferencias e historial, política de cookies y
  pasos para reportar fallos sin compartir datos sensibles.
