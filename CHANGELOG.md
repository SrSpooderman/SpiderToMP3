# Registro de cambios

Cada versión publicada tiene aquí sus notas. La etiqueta Git `vX.Y.Z` debe
coincidir con `APP_VERSION` en `config.py`.

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
