# Evaluación de Spotify (6 de octubre de 2026)

La Web API puede servir para **consultar metadatos**, pero no para obtener audio.
La referencia actual de [Get Playlist Items](https://developer.spotify.com/documentation/web-api/reference/get-playlists-items)
indica que ese endpoint solo acepta listas propias o en las que el usuario
colabora. Para listas privadas se requiere `playlist-read-private`. La misma
documentación prohíbe facilitar descargas o extracción de Spotify Content y
exige atribución al mostrar metadatos y portadas.

Una app de escritorio no debe llevar un secreto de cliente incrustado. Si en
el futuro se añade una consulta opcional, la
[autorización con PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
es el flujo adecuado: consentimiento explícito, ámbito mínimo, token guardado
de forma segura y opción de revocarlo. Antes de construirla habría que
registrar la app, definir el uso permitido de metadatos y comprobar de nuevo
la política vigente.

**Decisión:** no añadir Spotify al flujo de descarga de SpiderToMP3. Tampoco
convertir pistas de Spotify en búsquedas automáticas de audio de otro sitio.
Se mantiene el rechazo claro de esos enlaces. Una futura vista de metadatos
sería una función independiente, sin botón de descarga y con enlaces de
atribución a Spotify.
