"""Motor común y agnóstico de fuentes.

No conoce ningún calendario concreto: ofrece generación/validación de ICS,
HTTP con reintentos, escritura atómica, descubrimiento de manifiestos y un
runner que aísla los fallos entre calendarios.
"""
