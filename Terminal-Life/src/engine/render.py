import curses
from dataclasses import dataclass
from typing import List
from src.store.layout import (
    WALL, SHELF, REGISTER, QUEUE, DOOR, FRIDGE, COFFEE, COUNTER,
    PRODUCE, DRINKS, FREEZER, MAGAZINE, TABLE
)

@dataclass
class PanelSplit:
    top_height: int
    bottom_height: int

class Renderer:
    def __init__(self, simulation):
        self.sim = simulation
        self.rows = 0
        self.cols = 0
        self.split = PanelSplit(0, 0)

    def resize(self, rows, cols):
        self.rows = rows
        self.cols = cols
        top = int(rows * 2 / 3)
        bottom = rows - top
        self.split = PanelSplit(top, bottom)
        self.sim.set_bounds(top_rows=top, total_cols=cols)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            # Basic tile colors
            curses.init_pair(1, curses.COLOR_WHITE, -1)   # walls
            curses.init_pair(2, curses.COLOR_YELLOW, -1)  # shelves
            curses.init_pair(3, curses.COLOR_CYAN, -1)    # register
            curses.init_pair(4, curses.COLOR_GREEN, -1)   # queue
            curses.init_pair(5, curses.COLOR_MAGENTA, -1) # fridge
            curses.init_pair(6, curses.COLOR_RED, -1)     # coffee
            curses.init_pair(7, curses.COLOR_BLUE, -1)    # counter lip
            curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)  # door
            curses.init_pair(9, curses.COLOR_GREEN, -1)   # produce
            curses.init_pair(10, curses.COLOR_CYAN, -1)   # drinks ambient
            curses.init_pair(11, curses.COLOR_MAGENTA, -1)# freezer
            curses.init_pair(12, curses.COLOR_YELLOW, -1) # magazine
            curses.init_pair(13, curses.COLOR_WHITE, -1)  # table
            # Mood-based character colors
            curses.init_pair(20, curses.COLOR_GREEN, -1)   # Happy
            curses.init_pair(21, curses.COLOR_CYAN, -1)    # Upbeat
            curses.init_pair(22, curses.COLOR_WHITE, -1)   # Neutral
            curses.init_pair(23, curses.COLOR_YELLOW, -1)  # Flat
            curses.init_pair(24, curses.COLOR_RED, -1)     # Irritated

    def render(self, stdscr, show_help=False, paused=False, verbose_llm=False):
        stdscr.erase()
        store_lines = self.sim.render_store(self.split.top_height, self.cols)
        for r, line in enumerate(store_lines[:self.split.top_height]):
            for c, ch in enumerate(line[:self.cols]):
                attr = curses.A_NORMAL
                if curses.has_colors():
                    if ch == WALL:
                        attr = curses.color_pair(1)
                    elif ch == SHELF:
                        attr = curses.color_pair(2)
                    elif ch == REGISTER:
                        attr = curses.color_pair(3) | curses.A_BOLD
                    elif ch == QUEUE:
                        attr = curses.color_pair(4)
                    elif ch == FRIDGE:
                        attr = curses.color_pair(5)
                    elif ch == COFFEE:
                        attr = curses.color_pair(6)
                    elif ch == COUNTER:
                        attr = curses.color_pair(7)
                    elif ch == DOOR:
                        attr = curses.color_pair(8) | curses.A_BOLD
                    elif ch == PRODUCE:
                        attr = curses.color_pair(9)
                    elif ch == DRINKS:
                        attr = curses.color_pair(10)
                    elif ch == FREEZER:
                        attr = curses.color_pair(11)
                    elif ch == MAGAZINE:
                        attr = curses.color_pair(12)
                    elif ch == TABLE:
                        attr = curses.color_pair(13)
                    else:
                        # Characters overlay later; leave empty cells
                        pass
                try:
                    stdscr.addch(r, 0 + c, ch, attr)
                except curses.error:
                    pass
        # Overlay characters with mood-based colors
        if curses.has_colors():
            for ch in self.sim.characters:
                if not getattr(ch, 'active', True) and not ch.is_owner:
                    continue
                y = ch.pos.y
                x = ch.pos.x
                if 0 <= y < self.split.top_height and 0 <= x < self.cols:
                    mood = getattr(ch, 'mood_label', 'Neutral')
                    pair = 22
                    if mood == 'Happy':
                        pair = 20
                    elif mood == 'Upbeat':
                        pair = 21
                    elif mood == 'Flat':
                        pair = 23
                    elif mood == 'Irritated':
                        pair = 24
                    attr = curses.color_pair(pair) | curses.A_BOLD
                    try:
                        stdscr.addch(y, x, ch.symbol, attr)
                    except curses.error:
                        pass

        info_start = self.split.top_height
        logs = self.sim.get_logs(self.split.bottom_height - 4)
        active = sum(1 for c in self.sim.characters if getattr(c, 'active', True) or c.is_owner)
        total = len(self.sim.characters)
        status = (
            f"Tick:{self.sim.ticks} Act:{active}/{total} Paused:{paused} LLM:{'ON' if self.sim.dialogue_mgr.available else 'OFF'} "
            f"Verbose:{verbose_llm} ?=help"
        )
        try:
            stdscr.addstr(info_start, 0, status[:self.cols])
            stdscr.hline(info_start+1, 0, '-', self.cols)
        except curses.error:
            pass
        # show a quick mood bar for visible active chars on first line after separator
        mood_line = "Moods: " + ", ".join(
            f"{c.symbol}:{getattr(c,'mood_label','-')}" for c in self.sim.characters if (getattr(c,'active', True) or c.is_owner)
        )
        try:
            stdscr.addstr(info_start + 2, 0, mood_line[:self.cols])
        except curses.error:
            pass
        log_offset = 1
        for i, log in enumerate(logs):
            if info_start + 2 + i >= self.rows - 1:
                break
            try:
                stdscr.addstr(info_start + 2 + i + log_offset, 0, log[:self.cols])
            except curses.error:
                pass
        if show_help:
            self._render_help(stdscr)
        stdscr.refresh()

    def _render_help(self, stdscr):
        lines = [
            "Help:",
            " q quit  p pause  c force conversation  l toggle verbose LLM  ? toggle help",
            " Characters move, shop, converse. Bottom shows logs.",
            " Legend: # wall  = shelf  p produce  b drinks  F fridge  f freezer  C coffee",
            "          m magazine  R register  r counter  : queue  D door  t table",
        ]
        maxw = max(len(l) for l in lines) + 4
        maxh = len(lines) + 2
        r0 = 1
        c0 = max(0, self.cols - maxw - 2)
        try:
            for dr in range(maxh):
                for dc in range(maxw):
                    stdscr.addch(r0+dr, c0+dc, ' ')
            stdscr.addstr(r0, c0+2, "HELP")
            for i, l in enumerate(lines):
                stdscr.addstr(r0+1+i, c0+1, l)
        except curses.error:
            pass
