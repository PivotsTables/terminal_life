from dataclasses import dataclass

@dataclass
class Position:
    y: int
    x: int

    def copy(self):
        return Position(self.y, self.x)
