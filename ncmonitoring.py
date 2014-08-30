#!/usr/bin/env python2
# -*- coding: utf8 -*-

import curses
import time
from subprocess import check_output
import uptime
import netifaces


class Frame:
    _borderwindow = None
    _contentwindow = None
    _content = None
    _title = None
    _height = 0
    _width = 0
    _content_height = 0
    _content_width = 0

    def __init__(self, height, width, pos_y, pos_x, content, title=None):
        self._height = height
        self._width = width
        self._content = content
        if title is None:
            self._borderwindow = None
            self._contentwindow = curses.newwin(height, width, pos_y, pos_x)
            self._content_height = height
            self._content_width = width
        else:
            self._title = title
            self._content_height = height - 2
            self._content_width = width - 2
            self._borderwindow = curses.newwin(height, width, pos_y, pos_x)
            self._contentwindow = curses.newwin(self._content_height,
                                                self._content_width,
                                                pos_y + 1,
                                                pos_x + 1)
            self.update()

    def update(self, refresh=True):
        if self._borderwindow:
            self._borderwindow.border()
            self._borderwindow.addstr(0, 1, self._title)

        self._contentwindow.clear()
        content = self._content(self._content_height, self._content_width)
        content = content.split("\n")
        for i in range(len(content)):
            if i < self._content_height - 1 \
                    or len(content[i]) < self._content_width:
                self._contentwindow.addstr(i, 0,
                                           content[i][:self._content_width])
            else:
                self._contentwindow.addstr(i, 0, content[i][-1:])
                self._contentwindow.insstr(i, 0, content[i][:-1])
        if refresh:
            self.refresh()

    def refresh(self):
        if self._borderwindow:
            self._borderwindow.refresh()
        self._contentwindow.refresh()


class ColoredFrame(Frame):
    def update(self, refresh=True):
        if self._borderwindow:
            # self._borderwindow.clear()
            self._borderwindow.border()
            self._borderwindow.addstr(0, 1, self._title)

        self._contentwindow.clear()
        self._content(self._contentwindow,
                      self._content_height, self._content_width)
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
        value = "%5.2f" % load[i]
        window.addstr(0, i * 6, value[-1:], color)
        window.insstr(0, i * 6, value[:-1], color)


def get_df(height, width, mountpoints=['/']):
    graph_width = 50
    ret_val = []
    for mount in mountpoints:
        output = check_output(["df", mount, "-h"])
        output = output.decode('utf8')
        output = output.split("\n")[1]
        output = output.split()
        size = output[1]
        used = output[2]
        percent = output[4]
        percent = int(percent[:-1])

        percent = int(percent * graph_width / 100)

        graph = "[" + "|" * percent + " " * (graph_width - percent) + "]"
        ret_val.append("{:<15} {:} {:>4}/{:<4}".format(mount, graph,
                                                       used, size))
    return "\n".join(ret_val)


def draw_df(window, heigth, width, mountpoints=["/"]):
    graph_width = 50
    graph_warning = 40
    graph_critical = 45
    mountname_length = 15

    line = 0
    for mount in mountpoints:
        output = check_output(["df", mount, "-h"])
        output = output.decode('utf8')
        output = output.split("\n")[1]
        output = output.split()
        size = output[1]
        used = output[2]
        percent = output[4]
        percent = int(percent[:-1])
        percent = int(percent * graph_width / 100)
        graph = "|" * percent

        window.addstr(line,
                      0,
                      mount[-mountname_length:])
        window.addstr(line,
                      mountname_length + 1,
                      '[')
        window.addstr(line,
                      mountname_length + 2,
                      graph[:graph_warning], green)
        window.addstr(line,
                      mountname_length + 2 + graph_warning,
                      graph[graph_warning:graph_critical], yellow)
        window.addstr(line,
                      mountname_length + 2 + graph_critical,
                      graph[graph_critical:], red)
        window.addstr(line,
                      mountname_length + 2 + graph_width,
                      ']')
        window.addstr(line,
                      mountname_length + 2 + graph_width + 2,
                      "{:>4}/{:<4}".format(used, size))

        line += 1


def get_uptime(heigth, width):
    utime = uptime.uptime()
    utime = int(utime)
    minutes, seconds = divmod(utime, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return "%3i days %02i:%02i" % (days, hours, minutes)


def get_ip(heigth, width, interface='eth0'):
    ip_list = netifaces.ifaddresses(interface)
    ret_val = []

    try:
        ip = ip_list[netifaces.AF_INET]
        ip = ip[0]
        ip = ip['addr']
        ret_val.append(ip[-width:])
    except KeyError:
        ret_val.append("")

    try:
        ip = ip_list[netifaces.AF_INET6]
        ip = ip[0]
        ip = ip['addr']
        ret_val.append(ip[-width:])
    except KeyError:
        ret_val.append("")

    return "\n".join(ret_val)


def draw_hddtemp(window, heigth, width, devices=["/dev/sda"]):
    ret_val = []
    line = 0
    for dev in devices:
        temp = check_output(["hddtemp", "--numeric", "--unit=C", dev])
        temp = float(temp)
        window.addstr(line, 0, dev)
        window.addstr(line, 10, "%3.0f°C" % temp)
        line += 1
        # ret_val.append("--".join([device, name, device]))

    # return "\n".join(ret_val)


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

    # load
    load = ColoredFrame(3, 19, 0, 0, draw_load, "load")
    # date
    date = Frame(3, 21, 0, 59, get_date, "date")
    # df
    df = ColoredFrame(8, 80, 3, 0,
                      lambda w, y, x: draw_df(w, y, x, ["/",
                                                        "/home",
                                                        "/usr",
                                                        "/var",
                                                        "/tmp"]),
                      "df")
    # uptime
    utime = Frame(3, 16, 0, 19, get_uptime, "uptime")
    # iotop
    # vnstat
    # # hddtem
    hddtemp = ColoredFrame(6, 31, 11, 0, lambda y, x, w: draw_hddtemp(y, x, w, ["/dev/sdb"]), "hddtemp")
    # sensors
    # raidstatus
    # smart status
    # ip
    ip = Frame(4, 42, 0, 35, lambda y, x: get_ip(y, x, "em1"), "ip")
    # uname
    # (ftp-status)
    test = Frame(25, 80, 0, 0, lambda y, x: "1234567890", "test")
    frames = [date, load, df, utime, ip, hddtemp]

    while True:
        for frame in frames:
            frame.update()
        time.sleep(1)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
