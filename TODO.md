# TODO: próximos capítulos del spider

P0 y P1 están implementados. La primera Release aún espera su etiqueta Git;
los asuntos de P2 siguen en la cola, tomando café.

## P0 · Versiones con nombre y apellidos

- [x] **Una sola versión oficial.** Empezar, por ejemplo, en `0.1.0` y guardar
  el número en un único sitio (`APP_VERSION` en `config.py`, o metadatos del
  proyecto si se empaqueta como paquete Python). Mostrarlo en «Acerca de» y con
  `--version`; incorporarlo también a los nombres de los ejecutables. Nada de
  tres versiones distintas fingiendo ser la misma aplicación.
- [x] **Seguir SemVer sin invocar magia negra.** Usar `MAJOR.MINOR.PATCH`:
  corrección compatible → PATCH; función compatible → MINOR; cambio incompatible
  → MAJOR. Durante el desarrollo inicial, usar `0.x.y`. Crear la etiqueta Git
  `vX.Y.Z` para cada versión y comprobar en CI que coincide con `APP_VERSION`.
- [x] **Anotar qué cambió.** Mantener notas breves por versión (`CHANGELOG.md` o
  notas automáticas revisadas) y marcar versiones de prueba como *prerelease*.

## P0 · Releases, cada sistema con su maleta

- [x] **Publicar al crear una etiqueta `vX.Y.Z`.** Ejecutar pruebas y compilación
  de Windows y Linux; si todo pasa, crear una única GitHub Release para esa
  versión. Los Artifacts del workflow servirán para pasar archivos entre jobs;
  la descarga pública y duradera estará en Releases. Dar permiso de escritura
  al contenido solo al job que publica.
- [x] **Separar las descargas.** Adjuntar a la misma Release
  `SpiderToMP3-vX.Y.Z-windows-x86_64.exe` y
  `SpiderToMP3-vX.Y.Z-linux-x86_64.tar.gz`. El paquete Linux debe incluir el
  ejecutable, el instalador de Bazzite, el icono y el archivo `.desktop`.
  Adjuntar `SHA256SUMS` para verificar cada descarga. Adiós al ZIP mezclado:
  cada pingüino y cada ventana en su propia maleta.
- [x] **Comprobar antes de abrir la maleta.** Probar el arranque de ambos binarios,
  `--version`, la comunicación con el proceso de descarga y la instalación del
  paquete Linux; verificar nombres y sumas antes de publicar la Release.
- [x] **Actualizar las instrucciones.** Explicar en el README cómo descargar la
  versión correcta desde Releases, instalarla en Bazzite y volver a una versión
  anterior si una araña decide aprender a bailar claqué.

## P1 · Menos sorpresas durante la descarga

- [x] **Reintento de verdad individual.** Conservar el identificador de cada
  audio para reintentar solo el elemento fallido, incluso si venía de una lista;
  mostrar la causa del fallo junto al elemento.
- [x] **Evitar pisar canciones homónimas.** Revisar el patrón de nombre por
  defecto y las colisiones entre audios con el mismo título; avisar antes de
  sobrescribir archivos existentes.
- [x] **Enlaces menos caprichosos.** Validar los enlaces antes de iniciar el
  proceso y aceptar comas que formen parte de una URL sin partirla en dos.
- [x] **Registro útil, memoria tranquila.** Limitar el tamaño del registro en
  pantalla y ofrecer una forma de copiar o guardar los detalles de un fallo.

## P2 · La vida real llama a la puerta

- [ ] **Probar en Bazzite de verdad.** Verificar el paquete Linux, FFmpeg y el
  lanzador `.desktop` en una instalación Bazzite; documentar cualquier paso
  adicional que aparezca.
- [ ] **Aclarar Spotify.** Documentar qué enlaces admite realmente `yt-dlp`,
  si la aplicación necesita alguna credencial y qué ocurre con enlaces que no
  ofrecen audio descargable. Prometer poderes mágicos solo después de probarlos.
