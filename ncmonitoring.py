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
        self.contentwindow.clear()
        self.contentwindow.addstr(0, 0, self.content(self.content_height,
                                                     self.content_width))
        if refresh:
            self.refresh()

    def refresh(self):
        if self.borderwindow:
            self.borderwindow.refresh()
        self.contentwindow.refresh()


class ColoredFrame(Frame):
    def update(self, refresh=True):
        self.contentwindow.clear()
        self.content(self.contentwindow,
                     self.content_height, self.content_width)
        if refresh:
            self.refresh()


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
    load = load.split(',')
    load = map(str.strip, load)
    return ' '.join(load)


def draw_load(window, height, width):
    load = get_load(height, width)
    load = load.split()
    load = list(map(float, load))

    for i in range(len(load)):
        color = green
        if load[i] > 2:
            color = yellow
        if load[i] > 4:
            color = red
        window.addstr(0, i * 6, "%5.2f" % load[i], color)


def get_df(height, width, mountpoints='/'):
    graph_width = 20
    ret_val = []
    for mount in mountpoints:
        output = check_output(["df", mount,
                               "--output=size,used,pcent", "-h"])
        output = output.decode('utf8')
        output = output.split("\n")[1]
        output = output.split()
        size, used, percent = output
        percent = int(percent[:-1])

        percent = int(percent * graph_width / 100)

        graph = "[" + "|" * percent + " " * (graph_width - percent) + "]"
        ret_val.append(" ".join([mount, graph, used + "/" + size]))
    return "\n".join(ret_val)


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
    curses.start_color()

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    green = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    yellow = curses.color_pair(2)

    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    red = curses.color_pair(3)

    date = Frame(3, 22, 0, 24, get_date, "date")
    load = Frame(3, 24, 0, 0, get_load, "load")
    cload = ColoredFrame(3, 24, 0, 46, draw_load, "load")
    df = Frame(10, 50, 3, 0,
               lambda x, y: get_df(x, y, ["/", "/home", "/usr", "/var"]),
               "df")
    frames = [date, load, df, cload]

    while True:
        for frame in frames:
            frame.update()
        time.sleep(1)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
