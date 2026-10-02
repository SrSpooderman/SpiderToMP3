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
están en la raíz del repositorio. Escribe uno o varios enlaces, elige la carpeta
de salida y el formato, y pulsa **Descargar**.

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

En **Releases** de este repositorio, cada versión tendrá tres descargas separadas:

- `SpiderToMP3-vX.Y.Z-windows-x86_64.exe` para Windows.
- `SpiderToMP3-vX.Y.Z-linux-x86_64.tar.gz` con el ejecutable e instalador de Linux.
- `SHA256SUMS` para comprobar ambas descargas.

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

Para volver a una versión anterior, descarga sus archivos desde esa Release y
ejecuta de nuevo el instalador de Linux, o usa su `.exe` en Windows.

La app guarda la carpeta, formato, calidad y hasta 20 enlaces recientes en las
preferencias del usuario. El botón **Borrar historial** elimina esos enlaces.
Los enlaces deben ser HTTP o HTTPS; se admiten comas dentro de una URL. El
nombre por defecto incluye el identificador del audio para evitar colisiones.
Si el archivo de salida ya existe, se informa del fallo y no se sobrescribe.
El registro de pantalla conserva las últimas 1000 líneas y se puede copiar con
**Copiar registro**.

## Próximas mejoras

Consulta el [TODO de mejoras](TODO.md) para ver las tareas priorizadas.
