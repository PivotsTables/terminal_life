import curses
from dataclasses import dataclass
from typing import List, Dict
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
        # Fancy glyph mapping (logical tile -> displayed glyph)
        # Internal simulation still uses plain ASCII tokens.
        self.fancy = True  # toggle to disable fancy glyphs if terminal has issues
        self.tile_glyphs: Dict[str, str] = {}
        # Mood glyphs (single width). Fallback to character symbol if missing.
        self.mood_glyphs = {
            'Happy': '☺',
            'Upbeat': '♣',
            'Neutral': '•',
            'Flat': '·',
            'Irritated': '✖'
        }

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
        # configure glyphs (after resize for flexibility later)
        self._configure_glyphs()

    def _configure_glyphs(self):
        if not self.fancy:
            # fallback = identity (original chars)
            self.tile_glyphs = {
                WALL: '#', SHELF: '=', REGISTER: 'R', QUEUE: ':', DOOR: 'D', FRIDGE: 'F',
                COFFEE: 'C', COUNTER: 'r', PRODUCE: 'p', DRINKS: 'b', FREEZER: 'f', MAGAZINE: 'm', TABLE: 't'
            }
            return
        # Chosen single-width unicode glyphs safe for most macOS terminals
        self.tile_glyphs = {
            WALL: '▓',
            SHELF: '▒',
            REGISTER: '▩',
            QUEUE: '·',
            DOOR: '▣',
            FRIDGE: '▤',
            FREEZER: '▥',
            COFFEE: '¤',
            COUNTER: '─',
            PRODUCE: '●',
            DRINKS: '○',
            MAGAZINE: '≣',
            TABLE: '◆'
        }

    def toggle_fancy(self):
        self.fancy = not self.fancy
        self._configure_glyphs()

    def render(self, stdscr, show_help=False, paused=False, verbose_llm=False):
        stdscr.erase()
        store_lines = self.sim.render_store(self.split.top_height, self.cols)
        for r, line in enumerate(store_lines[:self.split.top_height]):
            for c, ch in enumerate(line[:self.cols]):
                attr = curses.A_NORMAL
                draw_ch = self.tile_glyphs.get(ch, ch)
                if curses.has_colors():
                    base_attr = curses.A_NORMAL
                    if ch == WALL:
                        base_attr = curses.color_pair(1)
                    elif ch == SHELF:
                        base_attr = curses.color_pair(2)
                    elif ch == REGISTER:
                        base_attr = curses.color_pair(3) | curses.A_BOLD
                    elif ch == QUEUE:
                        base_attr = curses.color_pair(4) | curses.A_DIM
                    elif ch == FRIDGE:
                        base_attr = curses.color_pair(5)
                    elif ch == COFFEE:
                        base_attr = curses.color_pair(6) | curses.A_BOLD
                    elif ch == COUNTER:
                        base_attr = curses.color_pair(7)
                    elif ch == DOOR:
                        base_attr = curses.color_pair(8) | curses.A_BOLD
                    elif ch == PRODUCE:
                        base_attr = curses.color_pair(9)
                    elif ch == DRINKS:
                        base_attr = curses.color_pair(10)
                    elif ch == FREEZER:
                        base_attr = curses.color_pair(11)
                    elif ch == MAGAZINE:
                        base_attr = curses.color_pair(12)
                    elif ch == TABLE:
                        base_attr = curses.color_pair(13)
                    attr = base_attr
                try:
                    stdscr.addch(r, 0 + c, draw_ch, attr)
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
                    style = curses.A_BOLD
                    # add mood-specific style tweaks
                    if mood == 'Flat':
                        style = curses.A_DIM
                    elif mood == 'Irritated':
                        style = curses.A_BOLD | curses.A_STANDOUT
                    attr = curses.color_pair(pair) | style
                    try:
                        disp_symbol = self.mood_glyphs.get(mood, ch.symbol if len(ch.symbol) == 1 else '?')
                        stdscr.addch(y, x, disp_symbol, attr)
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
        # Build legend dynamically from glyph mapping for clarity
        def lg(sym, desc):
            glyph = self.tile_glyphs.get(sym, sym)
            return f" {glyph} {desc}"
        lines = [
            "Help:",
            " q quit  p pause  c force conversation  l toggle verbose LLM  ? toggle help",
            " Characters move, shop, converse. Bottom shows logs.",
            " Legend:" + lg(WALL, 'wall') + lg(SHELF, 'shelf') + lg(PRODUCE, 'produce') + lg(DRINKS, 'drinks'),
            "        " + lg(FRIDGE, 'fridge') + lg(FREEZER, 'freezer') + lg(COFFEE, 'coffee') + lg(MAGAZINE, 'magazine'),
            "        " + lg(REGISTER, 'register') + lg(COUNTER, 'counter') + lg(QUEUE, 'queue') + lg(DOOR, 'door') + lg(TABLE, 'table'),
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
