#!/usr/bin/env python3

import curses
import time
from subprocess import check_output


class Frame:
    borderwindow = None
    contentwindow = None
    content = None
    title = None
    height = 0
    width = 0
    content_height = 0
    content_width = 0

    def __init__(self, height, width, pos_y, pos_x, content, title=None):
        self.height = height
        self.width = width
        self.content = content
        if title is None:
            self.borderwindow = None
            self.contentwindow = curses.newwin(height, width, pos_y, pos_x)
            self.content_height = height
            self.content_width = width
        else:
            self.title = title
            self.content_height = height - 2
            self.content_width = width - 2
            self.borderwindow = curses.newwin(height, width, pos_y, pos_x)
            self.borderwindow.border()
            self.borderwindow.addstr(0, 1, title)
            self.contentwindow = curses.newwin(self.content_height,
                                               self.content_width,
                                               pos_y + 1,
                                               pos_x + 1)
        self.update()

    def update(self, refresh=True):
        self.contentwindow.addstr(0, 0, self.content(self.content_height,
                                                     self.content_width))
        if refresh:
            self.refresh()

    def refresh(self):
        if self.borderwindow:
            self.borderwindow.refresh()
        self.contentwindow.refresh()


def get_date(height, width):
    time_format = "%F %X"
    if width < 19:
        time_format = "%X"
    if width < 8:
        time_format = "%H:%M"
    if width < 5:
        time_format = ""
    return time.strftime(time_format)

def get_load(height, width):
    output = check_output(["uptime"])
    output = output.decode('utf8')
    load = output.split("load average:")[1].strip()
    return load

if __name__ == "__main__":
    print(get_load(1, 2))
    # start
    stdscr = curses.initscr()
    # Keine Anzeige gedrückter Tasten
    curses.noecho()
    # Kein line-buffer
    curses.cbreak()
    curses.curs_set(0)
    stdscr.keypad(True)

    date = Frame(3, 20, 0, 24, get_date, "date")
    load = Frame(3, 24, 0, 0, get_load, "load")
    frames = [date, load]

    while True:
        for frame in frames:
            frame.update()
        time.sleep(1)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
