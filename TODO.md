# TODO de SpiderToMP3

Punto de partida: `v0.2.1` corrige el icono del menú en Linux y `v0.2.0`
introduce la actualización automática. La app
descarga por lotes, permite cancelar y reintentar fallos, y guarda preferencias.
Aquí van **solo tareas pendientes**, ordenadas por impacto. Cada casilla describe
un resultado comprobable; el spider ya tiene bastante con contar patas.

## P0 · Que la Release funcione fuera de CI

- [ ] **Probar una actualización entre dos Releases.** Tras publicar la primera
  versión con actualizador, comprobar en Windows y Bazzite el aviso, descarga,
  cancelación, reemplazo, reinicio y vuelta a la copia anterior.
- [ ] **Probar el paquete publicado en Bazzite limpio.** Instalar desde la
  Release, abrir desde el menú, convertir un audio público, cancelar una
  conversión y repetir tras reiniciar. Comprobar FFmpeg, Qt/EGL, Wayland y X11;
  documentar dependencias reales y añadir una forma de desinstalar únicamente
  los archivos instalados en `~/.local`.
- [ ] **Probar una conversión real con los binarios de Release.** El smoke test
  actual arranca la GUI y verifica la comunicación con el worker usando un URL
  inválido. Añadir a CI una descarga desde un servidor HTTP local con un WAV de
  prueba, convertirlo y verificar el archivo final en Windows y Linux.
- [ ] **Confirmar el resultado en disco antes de marcar «Completado».**
  `DownloadService` acepta un resultado de `yt-dlp`, pero no comprueba que el
  audio final exista y tenga contenido. Comunicar la ruta final a la interfaz;
  si falla la conversión o falta el archivo, marcar ese elemento como fallido.
- [ ] **Explicar las fuentes de verdad.** Añadir al README una sección «Enlaces
  compatibles» con ejemplos probados, errores habituales y la aclaración de que
  el soporte de sitios depende de `yt-dlp` y puede cambiar. Rechazar enlaces de
  Spotify con un mensaje claro mientras no exista una integración definida.

## P1 · Menos clics y colas más útiles

- [ ] **Vista previa antes de descargar.** Mostrar título, origen, duración y
  número de elementos; permitir elegir cuáles descargar. Para playlists grandes,
  pedir confirmación y aplicar un límite configurable antes de materializar toda
  la lista en memoria (`list(_iter_entries(...))`).
- [ ] **Controlar cada elemento de la cola.** Permitir quitar, reordenar y
  reintentar el elemento seleccionado. Al reintentar fallos, conservar visibles
  los completados y sus archivos; hoy `prepare_download()` borra la cola entera.
- [ ] **Progreso que diga algo útil.** Mostrar progreso por audio, velocidad y
  tiempo estimado cuando `yt-dlp` los proporcione. Distinguir análisis,
  descarga y conversión, y evitar que el 99 % parezca una siesta infinita.
- [ ] **Elegir qué hacer con duplicados.** Ofrecer «omitir», «renombrar» y
  «preguntar» cuando el destino exista; nunca sobrescribir sin consentimiento.
  Añadir un registro opcional por ID de origen para saltar audios ya descargados
  aunque cambie el nombre del archivo. `yt-dlp` ofrece
  [`download_archive`](https://github.com/yt-dlp/yt-dlp#readme) como punto de partida.
- [ ] **Recuperar una sesión interrumpida.** Guardar la cola y sus estados de
  forma local para reanudar pendientes tras un cierre o fallo, sin repetir los
  completados. Dar una opción para no guardar historial y otra para borrarlo.
- [ ] **Pegar y soltar sin pelearse con el formulario.** Añadir «Pegar enlaces»
  desde el portapapeles, arrastrar URL o archivos `.txt` a la ventana y eliminar
  duplicados antes de iniciar la cola.
- [ ] **Acciones al terminar.** Añadir «Abrir archivo», «Abrir carpeta» y
  notificación de escritorio con resumen de completados/fallidos. Mostrar la
  ruta del resultado para poder localizarlo sin buscar a mano.
- [ ] **Errores que se puedan resolver.** Separar fallos de red, enlace no
  admitido, FFmpeg, permisos y archivo existente; ofrecer una acción útil para
  cada caso. Exportar un informe de errores que oculte tokens, cookies y rutas
  personales antes de compartirlo.
- [ ] **Ajustes cómodos.** Ofrecer patrones de nombre predefinidos y una vista
  previa del nombre final; añadir ajustes para tamaño máximo de playlist,
  reintentos y espera entre intentos. Mantener valores seguros por defecto.
- [ ] **Accesibilidad y apariencia.** Añadir atajos de teclado, foco visible,
  lectura clara de estados de la cola y un tema oscuro/alto contraste que respete
  la preferencia del sistema. Probar navegación solo con teclado.

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
- [ ] **Añadir comprobaciones de calidad enfocadas.** Integrar formato/lint y
  análisis de tipos en CI; ampliar pruebas solo alrededor de la cola persistente,
  listas grandes, cancelación y archivos finales cuando esas funciones existan.
- [ ] **Documentar distribución y privacidad.** Añadir licencia, guía breve para
  contribuir, ubicación de preferencias e historial, política de cookies y
  pasos para reportar fallos sin compartir datos sensibles.
