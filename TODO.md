# TODO de mejoras

Ordenado por impacto. Cada casilla describe una tarea pendiente y cómo comprobar
que está terminada.

## P0 · Funcionamiento y errores

- [ ] **Hacer que la cola y el progreso representen cada audio de una playlist.**
  Ahora el porcentaje usa el número de enlaces y la cola muestra enlaces, aunque
  uno pueda contener varios audios. Terminado cuando el porcentaje no retrocede,
  no llega al 100 % antes de acabar la conversión y cada audio tiene un estado
  visible (`pendiente`, `descargando`, `convirtiendo`, `completado` o `fallido`).
- [ ] **Hacer la cancelación fiable durante descargas y conversiones largas.**
  Hoy se comprueba en los hooks de `yt-dlp`, así que puede tardar en responder si
  no llegan eventos. Terminado cuando cancelar o cerrar detiene el trabajo,
  espera al hilo sin bloquear indefinidamente y deja la interfaz en un estado
  coherente. Añadir pruebas de cancelación durante descarga y FFmpeg.
- [ ] **Validar las opciones antes de arrancar el hilo.** Comprobar que la carpeta
  de salida se puede crear y escribir, que la plantilla de nombre es válida para
  `yt-dlp` y que FFmpeg está disponible. Mostrar el problema junto al campo
  afectado. Terminado cuando estas entradas fallan antes de iniciar una descarga
  y tienen pruebas de casos inválidos.

## P1 · Calidad y distribución

- [ ] **Tratar los errores por elemento de la cola.** Ahora un fallo detiene el
  lote completo (`ignoreerrors=False`). Permitir reintentar un elemento fallido
  o continuar con los siguientes, y mostrar un resumen final de éxitos y fallos.
- [ ] **Ajustar la calidad al formato elegido.** El deslizador de 0 a 9 se pasa
  igual a todos los códecs, aunque su significado cambia. Mostrar opciones
  válidas y comprensibles para MP3, M4A, Opus, WAV y FLAC, con pruebas de las
  opciones que llegan a `yt-dlp`.
- [ ] **Añadir pruebas de integración sin depender de Internet.** Usar un archivo
  de audio local y FFmpeg para comprobar la conversión, y cubrir el ciclo de
  vida de la ventana y el hilo en Qt. Mantener las pruebas unitarias rápidas.
- [ ] **Verificar ambos ejecutables antes de publicar el ZIP.** El workflow ya
  prueba el arranque del binario Linux; añadir una prueba equivalente para el
  `.exe` de Windows y comprobar que el ZIP final contiene los dos archivos con
  los nombres esperados.
- [ ] **Hacer las compilaciones reproducibles.** Fijar y actualizar de forma
  controlada las versiones de las dependencias de ejecución y de empaquetado;
  publicar sumas SHA-256 junto a los binarios. Terminado cuando la misma revisión
  usa las mismas versiones en ambos sistemas y el ZIP incluye las sumas.

## P2 · Experiencia de uso

- [ ] **Guardar preferencias e historial.** Recordar carpeta, formato, calidad y
  enlaces recientes entre sesiones; permitir borrar el historial desde la app.
- [ ] **Mejorar el uso en Bazzite.** Crear un icono y un archivo `.desktop` para
  abrir el ejecutable desde el menú; estudiar AppImage o Flatpak si se busca una
  instalación sin pasos manuales.
- [ ] **Revisar accesibilidad y textos.** Asociar etiquetas a los controles,
  comprobar navegación con teclado y lectores de pantalla, y corregir tildes y
  mensajes de error en la interfaz.
