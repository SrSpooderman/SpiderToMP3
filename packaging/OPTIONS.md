# Distribución en Bazzite

La distribución actual es un `tar.gz` para Linux publicado como archivo propio
en cada GitHub Release, junto al ejecutable de Windows por separado. Contiene
binario Linux, icono, archivo `.desktop` e instalador de usuario.
`install-bazzite.sh` copia estos archivos a `~/.local`
sin modificar la imagen base del sistema. FFmpeg se usa desde el `PATH` del host.

Se consideraron estas alternativas:

- **AppImage:** permite distribuir un único archivo portable, pero requiere otra
  etapa de empaquetado y pruebas de las bibliotecas Qt. Su [documentación](https://docs.appimage.org/packaging-guide/distribution.html)
  recomienda distribuirlo como archivo independiente; podría sustituir el
  paquete Linux cuando haya pruebas suficientes en Bazzite.
- **Flatpak:** encaja con la [forma habitual de instalar apps en Bazzite](https://docs.bazzite.gg/Installing_and_Managing_Software/Flatpak/).
  Antes de publicarlo habría que definir el acceso a las carpetas elegidas por
  el usuario y cómo incluir o proporcionar FFmpeg dentro del entorno aislado.

Se mantiene el instalador de usuario para el paquete Linux. Si se publica la app
en una tienda o se necesitan actualizaciones automáticas, Flatpak sería la
siguiente opción a preparar y probar.
