from __future__ import annotations


def error_help(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, FileExistsError) or "already exists" in message or "ya existe" in message:
        return "Archivo existente: elige Renombrar u Omitir en Duplicados."
    if isinstance(exc, PermissionError) or "permission denied" in message or "permiso" in message:
        return "Permisos: elige una carpeta de salida donde puedas escribir."
    if "ffmpeg" in message or "ffprobe" in message or "postprocess" in message:
        return "Conversión: comprueba que FFmpeg y ffprobe están en el PATH."
    if any(part in message for part in ("timeout", "timed out", "connection", "http error", "network")):
        return "Red: comprueba la conexión y vuelve a intentar este audio."
    if any(part in message for part in ("unsupported", "no suitable", "not available", "unavailable")):
        return "Enlace: comprueba que es público y que la app está actualizada."
    return "Consulta el registro y reintenta el audio si el problema es temporal."
