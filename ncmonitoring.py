#!/usr/bin/env python3

import curses


class Frame:
    borderwindow = None
    contentwindow = None
    content = ""
    title = None

    def __init__(self, heigth, width, pos_y, pos_x, content, title=None):
        self.content = content
        if title is None:
            self.borderwindow = None
            self.contentwindow = curses.newwin(heigth, width, pos_y, pos_x)
        else:
            self.borderwindow = curses.newwin(heigth, width, pos_y, pos_x)
            self.borderwindow.border()
            self.borderwindow.addstr(0, 1, title)
            self.contentwindow = curses.newwin(heigth - 2, width - 2,
                                               pos_y + 1, pos_x + 1)
        self.contentwindow.addstr(content)
        self.refresh()

    def refresh(self):
        if self.borderwindow:
            self.borderwindow.refresh()
        self.contentwindow.refresh()


# start
stdscr = curses.initscr()
# Keine Anzeige gedrückter Tasten
curses.noecho()
# Kein line-buffer
curses.cbreak()


tw0 = Frame(10, 30, 1, 1, "hallo welt\nfoobar")
tw1 = Frame(10, 30, 5, 5, "lorem ipsum", "hallo welt")
tw2 = Frame(10, 30, 5, 35, "lorem ipsum", "")

# foo =

import time
time.sleep(100)

curses.echo()
curses.endwin()
