from dataclasses import dataclass

@dataclass
class Court:
    id: int
    nombre: str
    deporte: str
    precio_hora: float