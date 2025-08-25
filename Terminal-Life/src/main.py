import curses
import time
import traceback

from src.store.simulation import StoreSimulation
from src.engine.render import Renderer
from src.dialogue.dialogue_manager import DialogueManager

TICK_SECONDS = 0.5


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(int(TICK_SECONDS * 1000))

    dialogue_mgr = DialogueManager()
    sim = StoreSimulation(dialogue_mgr=dialogue_mgr)
    renderer = Renderer(simulation=sim)

    paused = False
    running = True
    force_convo = False
    show_help = False
    verbose_llm = False
    last_resize = None

    try:
        while running:
            try:
                rows, cols = stdscr.getmaxyx()
                if (rows, cols) != last_resize:
                    renderer.resize(rows, cols)
                    last_resize = (rows, cols)

                key = stdscr.getch()
                if key != -1:
                    ch = chr(key) if 0 <= key < 256 else ''
                    if ch == 'q':
                        running = False
                    elif ch == 'p':
                        paused = not paused
                    elif ch == 'c':
                        force_convo = True
                    elif ch == 'l':
                        verbose_llm = not verbose_llm
                        sim.add_log(f"Verbose LLM: {verbose_llm}")
                    elif ch == '?':
                        show_help = not show_help
                    elif ch == 'g':
                        renderer.toggle_fancy()
                        sim.add_log(f"Fancy graphics: {renderer.fancy}")

                if not paused:
                    sim.tick(force_conversation=force_convo, verbose_llm=verbose_llm)
                    force_convo = False

                renderer.render(stdscr, show_help=show_help, paused=paused, verbose_llm=verbose_llm)

            except KeyboardInterrupt:
                running = False
            except Exception as e:
                sim.add_log("EXCEPTION: " + repr(e))
                sim.add_log(traceback.format_exc())
                time.sleep(1)
    finally:
        dialogue_mgr.shutdown()

    curses.endwin()


if __name__ == "__main__":
    curses.wrapper(main)