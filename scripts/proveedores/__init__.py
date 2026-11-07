"""Proveedores de fuentes externas compartidos entre calendarios.

Un proveedor no sabe de un equipo o calendario concreto: recibe una
configuración y devuelve datos normalizados. Así dos equipos de la misma
competición pueden reutilizar el mismo parser sin duplicar código.
"""
