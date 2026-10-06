# Evaluación de cookies del navegador

`yt-dlp` permite pasar cookies de navegadores compatibles mediante
`cookiesfrombrowser`; el conjunto depende de la plataforma y la instalación.
También documenta que compartir una sesión del navegador con una descarga puede
provocar que el sitio invalide las cookies. Véase la
[documentación de autenticación de yt-dlp](https://github.com/yt-dlp/yt-dlp#authentication-options).

## Decisión para SpiderToMP3

La función debe ser opcional y activarse por descarga. No se deben copiar las
cookies a preferencias, archivos temporales propios ni registros. La aplicación
debe pedir consentimiento antes de leer el perfil, mostrar el navegador elegido
y explicar que la sesión concede a `yt-dlp` el acceso que el sitio permita.
Nunca se deben solicitar contraseñas ni exportar cookies a un archivo.

Antes de implementarla hace falta comprobar la lectura de perfiles bloqueados y
los almacenes de claves en Windows y Bazzite, incluido el comportamiento cuando
el perfil está en uso. Una futura variante Flatpak necesitaría permisos de
lectura explícitos para acceder a perfiles fuera del sandbox, lo que requiere una
decisión de diseño específica. Hasta validar esos casos, no se añade un control
de cookies que pueda aparentar funcionar mientras filtra datos sensibles o
falla silenciosamente.

## Pruebas necesarias

1. Probar con una cuenta de prueba y una URL cuyo acceso requiera sesión.
2. Confirmar que cancelar o terminar la descarga no conserva cookies ni perfil.
3. Revisar los registros y mensajes de error para asegurar que no incluyen
   cabeceras, valores de cookies ni rutas completas del perfil.
4. Repetir en Windows y Bazzite; probar perfil abierto, cerrado y almacén de
   claves bloqueado.
