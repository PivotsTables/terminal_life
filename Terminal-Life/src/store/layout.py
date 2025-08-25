from typing import List, Tuple

# Core structural tiles
WALL = '#'
EMPTY = ' '
DOOR = 'D'
COUNTER = 'r'          # counter lip in front of register block
REGISTER = 'R'         # register block proper
QUEUE = ':'            # queue column

# Merch / interaction zones (non-passable)
SHELF = '='            # general snacks
PRODUCE = 'p'          # produce bins
DRINKS = 'b'           # beverage coolers (ambient)
FRIDGE = 'F'           # refrigerated upright coolers
FREEZER = 'f'          # freezer chest
COFFEE = 'C'           # coffee station / hot drinks
MAGAZINE = 'm'         # magazine / impulse rack
TABLE = 't'            # small seating table (non-passable)

class StoreLayout:
    """Defines a richer store layout with multiple themed zones.

    Legend (also shown in help):
      = snack shelves   p produce   b drinks   F fridge   f freezer
      C coffee bar      m magazine  R register r counter  : queue
      D door            t table
    """

    def __init__(self, height=26, width=78):
        self.height = height
        self.width = width
        self.grid = [[EMPTY for _ in range(width)] for _ in range(height)]
        self._build()

    def _hline(self, y: int, x0: int, x1: int, ch: str):
        for x in range(max(0, x0), min(self.width, x1+1)):
            self.grid[y][x] = ch

    def _vline(self, x: int, y0: int, y1: int, ch: str):
        for y in range(max(0, y0), min(self.height, y1+1)):
            self.grid[y][x] = ch

    def _build(self):
        # Outer walls
        for x in range(self.width):
            self.grid[0][x] = WALL
            self.grid[self.height-1][x] = WALL
        for y in range(self.height):
            self.grid[y][0] = WALL
            self.grid[y][self.width-1] = WALL

        # Door (single opening on bottom)
        door_x = self.width // 2
        self.grid[self.height-1][door_x] = DOOR

        # Register block (top-right corner block)
        reg_left = self.width - 14
        reg_right = self.width - 5
        for y in range(2, 6):
            for x in range(reg_left, reg_right):
                self.grid[y][x] = REGISTER
        for x in range(reg_left, reg_right):
            self.grid[6][x] = COUNTER  # counter lip

        # Queue channel leading downward from counter
        qx = reg_left + 4  # slight inset
        for y in range(7, 18):
            self.grid[y][qx] = QUEUE

        # Long snack shelf aisles (center region)
        shelf_rows = [4, 7, 10, 13, 16]
        for r in shelf_rows:
            for c in range(6, self.width-20):
                if (c // 5) % 2 == 0:
                    self.grid[r][c] = SHELF

        # Produce zone (left-front quadrant)
        for y in range(3, 8):
            for x in range(2, 6):
                if (x + y) % 2 == 0:
                    self.grid[y][x] = PRODUCE

        # Beverage ambient shelves along left wall mid-store
        for y in range(9, 16):
            if y % 2 == 1:
                self.grid[y][2] = DRINKS
                self.grid[y][3] = DRINKS

        # Fridge & freezer bank (upper-left vertical)
        for y in range(2, 8):
            self.grid[y][self.width-30] = FRIDGE
        for x in range(self.width-35, self.width-31):
            self.grid[8][x] = FREEZER

        # Coffee bar (near top center-left)
        for x in range(12, 18):
            self.grid[2][x] = COFFEE

        # Magazine / impulse rack near queue entrance
        for x in range(qx-2, qx):
            self.grid[8][x] = MAGAZINE

        # Small seating (tables) near door area (bottom center)
        for x in range(door_x-8, door_x-3, 2):
            self.grid[self.height-4][x] = TABLE
        for x in range(door_x+4, door_x+9, 2):
            self.grid[self.height-5][x] = TABLE

    def render_lines(self) -> List[str]:
        return ["".join(row) for row in self.grid]

    def in_bounds(self, y, x):
        return 0 <= y < self.height and 0 <= x < self.width

    def passable(self, y, x):
        if not self.in_bounds(y, x):
            return False
        # Only walk through open floor / queue / counter zone / door.
        return self.grid[y][x] in (EMPTY, QUEUE, COUNTER, DOOR, REGISTER)

    def shelf_positions(self) -> List[Tuple[int,int]]:
        out: List[Tuple[int,int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] in (SHELF, PRODUCE, DRINKS):
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
