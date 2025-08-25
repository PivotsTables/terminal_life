import random
from typing import List, Optional
from collections import deque
from src.store.layout import StoreLayout
from src.characters.cast import create_cast
from src.engine.state import Position
from src.characters.character import Character
from src.dialogue.dialogue_manager import DialogueManager

LOG_LIMIT = 400

class StoreSimulation:
    def __init__(self, dialogue_mgr: DialogueManager):
        self.layout = StoreLayout()
        self.origin = (0, 0)
        self.characters: List[Character] = create_cast(self.origin)
        self.dialogue_mgr = dialogue_mgr
        self.logs = deque(maxlen=LOG_LIMIT)
        self.ticks = 0
        self.top_rows = self.layout.height
        self.total_cols = self.layout.width
        self._queue: List[str] = []
        self.add_log("Simulation started.")

    def set_bounds(self, top_rows, total_cols):
        self.top_rows = top_rows
        self.total_cols = total_cols

    def add_log(self, msg):
        self.logs.append(f"[{self.ticks:05d}] {msg}")

    def get_logs(self, max_lines):
        return list(self.logs)[-max_lines:]

    def render_store(self, max_rows, max_cols):
        base = self.layout.render_lines()
        area = [list(line[:max_cols].ljust(max_cols)) for line in base[:max_rows]]
        for c in self.characters:
            if 0 <= c.pos.y < len(area) and 0 <= c.pos.x < len(area[0]):
                area[c.pos.y][c.pos.x] = c.symbol
        return ["".join(row) for row in area]

    def tick(self, force_conversation=False, verbose_llm=False):
        self.ticks += 1
        for c in self.characters:
            if c.is_owner:
                continue
            # handle offstage comeback
            if not c.active and c.return_tick is not None and self.ticks >= c.return_tick:
                self._spawn_customer(c)
            if not c.active:
                continue
            if not c.path:
                self._maybe_assign_path(c)
            c.step()
            c.update_mood()
        bob = self._bob()
        if self.ticks % 20 == 0:
            self._bob_idle_move(bob)
        if self.ticks % 7 == 0 or force_conversation:
            self._attempt_conversations(verbose_llm=verbose_llm)
        self._update_queue()

    def _bob(self):
        return next(c for c in self.characters if c.is_owner)

    def _bob_idle_move(self, bob: Character):
        # Keep Bob constrained to register area small jitter
        register_tiles = self.layout.register_positions()
        if not register_tiles:
            return
        miny = min(y for y, _ in register_tiles)
        maxy = max(y for y, _ in register_tiles)
        minx = min(x for _, x in register_tiles)
        maxx = max(x for _, x in register_tiles)
        choices = [(0,0),(0,1),(0,-1),(1,0),(-1,0)]
        random.shuffle(choices)
        for dy, dx in choices:
            ny, nx = bob.pos.y + dy, bob.pos.x + dx
            if miny <= ny <= maxy and minx <= nx <= maxx:
                bob.pos.y, bob.pos.x = ny, nx
                break

    def _maybe_assign_path(self, c: Character):
        if c.target_kind == 'register':
            return
        if random.random() < 0.15:
            self._assign_queue_path(c)
        else:
            self._assign_shelf_path(c)

    def _assign_shelf_path(self, c: Character):
        shelf_positions = self.layout.shelf_positions()
        tgt = random.choice(shelf_positions)
        path = self._straight_path(c.pos, Position(*tgt))
        c.set_path(path, 'shelf')
        c.waiting_ticks = random.randint(1, 4)

    def _assign_queue_path(self, c: Character):
        qy, qx = self.layout.queue_entry()
        path = self._straight_path(c.pos, Position(qy, qx))
        c.set_path(path, 'register')

    def _straight_path(self, start: Position, end: Position):
        path = []
        y, x = start.y, start.x
        dy = 1 if end.y > y else -1
        dx = 1 if end.x > x else -1
        while x != end.x:
            x += dx
            if self.layout.passable(y, x):
                path.append(Position(y, x))
        while y != end.y:
            y += dy
            if self.layout.passable(y, x):
                path.append(Position(y, x))
        return path

    def _attempt_conversations(self, verbose_llm=False):
        active_chars = [c for c in self.characters if (c.is_owner or c.active)]
        pairs = []
        for i, a in enumerate(active_chars):
            for b in active_chars[i+1:]:
                if abs(a.pos.y - b.pos.y) <= 1 and abs(a.pos.x - b.pos.x) <= 1:
                    pairs.append((a, b))
        if not pairs:
            return
        a, b = random.choice(pairs)
        speaker, listener = (a, b) if random.random() < 0.5 else (b, a)
        situational = self._situational_context(speaker, listener)
        active_names = [c.name for c in active_chars]
        line = self.dialogue_mgr.generate_line(speaker, listener, situational, verbose=verbose_llm, tick=self.ticks, active_names=active_names)
        self.add_log(f"{speaker.name}->{listener.name}: {line}")

    def _situational_context(self, a: Character, b: Character):
        tile_a = self._tile_at(a.pos)
        tile_b = self._tile_at(b.pos)
        focused = {tile_a, tile_b}
        if '=' in focused:
            return "by snack shelves"
        if 'p' in focused:
            return "in the produce section"
        if 'b' in focused:
            return "near the ambient drink racks"
        if 'F' in focused:
            return "at the refrigerated coolers"
        if 'f' in focused:
            return "by the freezer chest"
        if 'C' in focused:
            return "at the coffee station"
        if 'm' in focused:
            return "near the magazine rack"
        if 'R' in focused:
            return "near the register"
        if ':' in focused:
            return "standing in the checkout line"
        if 't' in focused:
            return "near the small seating tables"
        return "inside the general aisles"

    def _tile_at(self, pos: Position):
        if self.layout.in_bounds(pos.y, pos.x):
            return self.layout.grid[pos.y][pos.x]
        return ' '

    def _update_queue(self):
        qy, qx = self.layout.queue_entry()
        queue_chars = []
        for c in self.characters:
            if c.is_owner:
                continue
            if c.target_kind == 'register':
                if c.pos.x == qx:
                    queue_chars.append(c)
        queue_chars.sort(key=lambda cc: cc.pos.y)
        self._queue = [c.name for c in queue_chars]
        register_positions = self.layout.register_positions()
        if not register_positions:
            return
        front_reg = min(register_positions)
        bob = self._bob()
        if queue_chars:
            first = queue_chars[0]
            if first.pos.y > front_reg[0] + 1:
                ny = first.pos.y - 1
                if self.layout.passable(ny, first.pos.x):
                    first.pos.y = ny
            else:
                if self.ticks % 9 == 0:
                    situ = "completing a purchase"
                    active_names = [cc.name for cc in self.characters if cc.is_owner or cc.active]
                    line = self.dialogue_mgr.generate_line(bob, first, situ, tick=self.ticks, active_names=active_names)
                    self.add_log(f"{bob.name}->{first.name}: {line}")
                if self.ticks % 15 == 0:
                    self.add_log(f"{first.name} leaves after checkout.")
                    self._offstage_customer(first)

    # Offstage / spawn logic
    def _offstage_customer(self, c: Character):
        c.active = False
        c.return_tick = self.ticks + random.randint(80, 260)  # several minutes sim time
        c.path = []
        c.target_kind = None
        self.add_log(f"{c.name} exits (will return later).")
        # drop any conversation threads involving this character
        self.dialogue_mgr.drop_threads_involving(c.name)

    def _spawn_customer(self, c: Character):
        c.active = True
        c.return_tick = None
        # spawn at door (or fallback to lower area)
        door = getattr(self.layout, 'door_position', None)
        if door:
            dy, dx = self.layout.door_position()
            c.pos.y, c.pos.x = dy, dx
        else:
            c.pos.y = random.randint(self.layout.height//2, self.layout.height-3)
            c.pos.x = random.randint(2, self.layout.width-3)
        c.waiting_ticks = random.randint(1, 4)
        self.add_log(f"{c.name} enters the store.")
