# Registro de cambios

Cada versión publicada tiene aquí sus notas. La etiqueta Git `vX.Y.Z` debe
coincidir con `APP_VERSION` en `config.py`.

## [0.3.0]

- Renueva la ventana con paneles claros, pestañas para cola y actividad, temas revisados y mejor uso en ventanas pequeñas.
- Permite importar y exportar listas CSV y M3U conservando título, origen, estado y archivo local.
- Añade metadatos y portada opcionales para MP3, M4A, Opus y FLAC, con pruebas reales por formato.
- Importa podcasts RSS con vista previa de episodios y recuerda los completados cuando se guarda la sesión.
- Permite elegir de forma explícita etiquetas de MusicBrainz en la vista previa.
- Añade vista previa con selección y orden de audios, límite configurable de listas y reanudación de la cola.
- Muestra avance por audio y permite controlar duplicados, reintentos y un registro opcional de IDs descargados.
- Añade pegado y arrastre de enlaces, acciones sobre archivos, informes de errores y temas accesibles.
- Oculta datos sensibles en el registro y permite desactivar o borrar el historial guardado.
- Verifica el audio final antes de marcarlo completado y restaura el ejecutable anterior si la actualización no arranca.
- Amplía las pruebas de los ejecutables con una conversión real desde HTTP local y publica un desinstalador de Linux.

## [0.2.1]

- Corrige el icono de SpiderToMP3 en el menú de KDE: instala un PNG y reconstruye la caché de aplicaciones con el idioma de la sesión.
- Repara el lanzador al abrir la nueva versión si se actualizó desde un instalador anterior.
- Documenta el mismo instalador de usuario para Bazzite, Ubuntu y Fedora.

## [0.2.0]

- Avisa al iniciar el ejecutable cuando hay una Release estable nueva y permite buscarla desde Ayuda.
- Descarga la versión de Windows o Linux, comprueba SHA-256 y actualiza el ejecutable tras cerrar la app.
- Permite cancelar la descarga de actualización y conserva una copia de la versión anterior.
- Estrena un icono SVG de araña con auriculares, incluido también en el ejecutable de Windows.

## [0.1.2]

- Corrige las pruebas de versión para futuras publicaciones.

## [0.1.1]

- Corrige la dependencia libEGL en los jobs de Linux.

## [0.1.0]

- Primera versión de escritorio con descargas y conversiones de audio por lote.
- Cola por audio, cancelación de descarga y conversión, reintentos y preferencias.
- Ejecutables separados para Windows y Linux, con instalador de usuario para Bazzite.
