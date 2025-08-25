from typing import List, Tuple

WALL = '#'
SHELF = '='
REGISTER = 'R'
EMPTY = ' '
QUEUE = ':'
DOOR = 'D'
FRIDGE = 'F'
COFFEE = 'C'
COUNTER = 'r'

class StoreLayout:
    def __init__(self, height=24, width=70):
        self.height = height
        self.width = width
        self.grid = [[EMPTY for _ in range(width)] for _ in range(height)]
        self._build()

    def _build(self):
        # Walls
        for x in range(self.width):
            self.grid[0][x] = WALL
            self.grid[self.height-1][x] = WALL
        for y in range(self.height):
            self.grid[y][0] = WALL
            self.grid[y][self.width-1] = WALL
        # Door
        door_x = self.width // 2
        self.grid[self.height-1][door_x] = DOOR
        # Shelves
        shelf_rows = [4, 7, 10, 13, 16]
        for r in shelf_rows:
            for c in range(3, self.width-3):
                if (c // 6) % 2 == 0:
                    self.grid[r][c] = SHELF
        # Register
        for r in range(2, 6):
            for c in range(self.width-12, self.width-4):
                self.grid[r][c] = REGISTER
        # Counter lip
        for c in range(self.width-12, self.width-4):
            self.grid[6][c] = COUNTER
        # Queue path
        for r in range(6, 14):
            self.grid[r][self.width-8] = QUEUE
        # Fridge section
        for r in range(2, 8):
            self.grid[r][2] = FRIDGE
        # Coffee station
        for c in range(5, 10):
            self.grid[2][c] = COFFEE

    def render_lines(self) -> List[str]:
        return ["".join(row) for row in self.grid]

    def in_bounds(self, y, x):
        return 0 <= y < self.height and 0 <= x < self.width

    def passable(self, y, x):
        if not self.in_bounds(y, x):
            return False
        return self.grid[y][x] in (EMPTY, QUEUE, REGISTER, COUNTER, DOOR)

    def shelf_positions(self) -> List[Tuple[int,int]]:
        out: List[Tuple[int,int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == SHELF:
                    out.append((y, x))
        return out

    def queue_entry(self):
        for y in range(self.height):
            if self.grid[y][self.width-8] == QUEUE:
                return (y, self.width-8)
        return (6, self.width-8)

    def register_positions(self):
        pos=[]
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == REGISTER:
                    pos.append((y,x))
        return pos

    def door_position(self):
        for x in range(self.width):
            if self.grid[self.height-1][x] == DOOR:
                return (self.height-1, x)
        return (self.height-1, self.width//2)
