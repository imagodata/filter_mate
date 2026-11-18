# -*- coding: utf-8 -*-
"""A real pointer and keyboard on the X display (the XTest extension, through ctypes: libX11 and libXtst are in
every qgis/qgis image, no tool to install).

The GUI smoke runs it beside QGIS for what cannot be checked by calling a handler: a drag started by the mouse
blocks the handler that started it (``QDrag.exec``, the move of a dock), so the pointer has to be moved from
another process, as a hand does. The X server sends QGIS the same events as for a real mouse.

    python3 x_mouse.py move 800 400 down 1 drag 1200 400 sleep 0.3 up 1 key Escape

Actions, in order:

* ``move X Y``: the pointer jumps there.
* ``drag X Y``: the pointer goes there step by step (a drag is told from a click by the way it moves, and a dock
  looks for its drop place at each move).
* ``down N`` / ``up N``: the button N is pressed, released (1: left, 3: right).
* ``key NAME``: a key pressed and released (``Escape``).
* ``sleep S``: seconds.
"""
import ctypes
import sys
import time

KEYSYMS = {"Escape": 0xFF1B, "Return": 0xFF0D}
STEP = 6  # pixels between two positions of a drag
PAUSE = 0.012  # seconds between them: Qt gets each one


def main(arguments):
    x11 = ctypes.CDLL("libX11.so.6")
    xtst = ctypes.CDLL("libXtst.so.6")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XKeysymToKeycode.restype = ctypes.c_ubyte
    xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    display = x11.XOpenDisplay(None)
    if not display:
        print("x_mouse: no X display", file=sys.stderr)
        return 2
    position = [0, 0]

    def to(x, y):
        xtst.XTestFakeMotionEvent(display, -1, int(x), int(y), 0)
        x11.XSync(display, 0)
        position[0], position[1] = int(x), int(y)

    words = list(arguments)
    while words:
        action = words.pop(0)
        if action == "move":
            to(int(words.pop(0)), int(words.pop(0)))
        elif action == "drag":
            x, y = int(words.pop(0)), int(words.pop(0))
            start = tuple(position)
            count = max(1, int(max(abs(x - start[0]), abs(y - start[1])) / STEP))
            for index in range(1, count + 1):
                to(start[0] + (x - start[0]) * index / count, start[1] + (y - start[1]) * index / count)
                time.sleep(PAUSE)
        elif action in ("down", "up"):
            xtst.XTestFakeButtonEvent(display, int(words.pop(0)), 1 if action == "down" else 0, 0)
            x11.XSync(display, 0)
        elif action == "key":
            code = x11.XKeysymToKeycode(display, KEYSYMS[words.pop(0)])
            xtst.XTestFakeKeyEvent(display, code, 1, 0)
            xtst.XTestFakeKeyEvent(display, code, 0, 0)
            x11.XSync(display, 0)
        elif action == "sleep":
            time.sleep(float(words.pop(0)))
        else:
            print(f"x_mouse: unknown action {action!r}", file=sys.stderr)
            return 2
    x11.XSync(display, 0)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
