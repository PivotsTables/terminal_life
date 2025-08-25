from typing import List
from src.characters.character import Character
from src.engine.state import Position

def create_cast(store_origin):
    oy, ox = store_origin
    cast: List[Character] = [
        Character("Bob", Position(oy+2, ox+5), is_owner=True),
        Character("Alice", Position(oy+8, ox+10)),
        Character("Ben", Position(oy+10, ox+12)),
        Character("Cara", Position(oy+9, ox+14)),
        Character("Drew", Position(oy+11, ox+16)),
        Character("Eve", Position(oy+12, ox+18)),
        Character("Finn", Position(oy+8, ox+20)),
        Character("Gina", Position(oy+9, ox+22)),
    ]
    return cast
