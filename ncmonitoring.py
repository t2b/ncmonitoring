#!/usr/bin/env python2
# -*- coding: utf8 -*-

execfile("env/bin/activate_this.py", dict(__file__="env/bin/activate_this.py"))

import curses
import time
from subprocess import check_output
import uptime
import netifaces
from os import path
from telnetlib import Telnet


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
            # self.update()

    def update(self, refresh=True):
        if self._borderwindow:
            self._borderwindow.clear()
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


class ColorFrame(Frame):
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


class GeneratorFrame(Frame):
    _content_generator = None

    def __init__(self, height, width, pos_y, pos_x, generator, title=None):
        self._content_generator = generator(height, width)
        Frame.__init__(self, height, width, pos_y, pos_x,
                       lambda y, x: self._content_generator.next(), title)


class ColorGeneratorFrame(ColorFrame, GeneratorFrame):
    def __init__(self, height, width, pos_y, pos_x, generator, title=None):
        GeneratorFrame.__init__(self, height, width, pos_y, pos_x,
                                lambda y, x: None, title)
        self._content_generator = generator(self._contentwindow, height, width)
        self._content = lambda w, y, x: self._content_generator.next()


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


def __draw_bar(window, pos_y, pos_x,
               length, value, warning=None, critical=None, sign="|"):
    if critical is None:
        critical = int(length * 0.9)
        if length > 1 and critical == length:
            critical = length - 1

    if warning is None:
        warning = int(length * 0.8)
        if critical > 1 and warning >= critical:
            warning = critical - 1

    graph = sign * value
    window.addstr(pos_y,
                  pos_x,
                  graph[:warning], green)
    window.addstr(pos_y,
                  pos_x + warning,
                  graph[warning:critical], yellow)
    window.addstr(pos_y,
                  pos_x + critical,
                  graph[critical:length], red)


def draw_df(window, heigth, width, mountpoints=["/"]):
    # 80
    if width < 40:
        mountname_length = int(width - 12) / 2
    else:
        mountname_length = 15
    graph_width = width - mountname_length - 13

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

        window.addstr(line,
                      0,
                      mount[-mountname_length:])
        window.addstr(line,
                      mountname_length + 1,
                      '[')
        __draw_bar(window, line, mountname_length + 2,
                   graph_width, percent)
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


def draw_hddtemp(window, heigth, width, devices=None):
    t = Telnet()
    t.open("localhost", 7634)
    output = t.read_all()
    t.close()
    t.close
    seperator = '|'
    output = output.split(seperator * 2)
    output = map(lambda x: x.strip(seperator).split(seperator), output)

    line = 0
    for hddtemp in output:
        color = curses.color_pair(0)
        try:
            temp = float(hddtemp[2])
            if temp < 40:
                color = green
            if 40 <= temp < 50:
                color = yellow
            if temp > 50:
                color = red
        except ValueError:
            pass
        window.addstr(line, 0, hddtemp[0][-9:])
        window.addstr(line, 10, hddtemp[2][-3:], color)
        window.addstr(line, 13, hddtemp[3][-1:], color)
        line += 1


def __netstat(device):
    prev_rx_timstamp = time.time()
    prev_rx_bytes = 0
    with open(path.join(device, "statistics/rx_bytes")) as f:
        prev_rx_bytes = long(f.read())

    prev_tx_timstamp = time.time()
    prev_tx_bytes = 0
    with open(path.join(device, "statistics/tx_bytes")) as f:
        prev_tx_bytes = long(f.read())

    while True:
        rx_timestamp = time.time()
        with open(path.join(device, "statistics/rx_bytes")) as f:
            rx_bytes = long(f.read())
        rx_speed = (rx_bytes - prev_rx_bytes) \
            / (rx_timestamp - prev_rx_timstamp) * 8
        prev_rx_timstamp = rx_timestamp
        prev_rx_bytes = rx_bytes

        tx_timestamp = time.time()
        with open(path.join(device, "statistics/tx_bytes")) as f:
            tx_bytes = long(f.read())
        tx_speed = (tx_bytes - prev_tx_bytes) \
            / (tx_timestamp - prev_tx_timstamp) * 8
        prev_tx_timstamp = tx_timestamp
        prev_tx_bytes = tx_bytes
        yield (rx_speed, tx_speed)


def draw_netstat(window, height, width, device):
    netstat_generator = __netstat(device)
    graph_length = width - 22
    while True:
        rx_speed, tx_speed = netstat_generator.next()
        rx_speed = rx_speed / 1000**2
        tx_speed = tx_speed / 1000**2

        window.addstr(0, 0, "rx: [")
        __draw_bar(window, 0, 5,
                   graph_length, int(round(graph_length * rx_speed / 1000)))
        window.insstr(0, 5 + graph_length, "] %6.1f Mbit/s" % rx_speed)

        window.addstr(1, 0, "tx: [")
        __draw_bar(window, 1, 5,
                   graph_length, int(round(graph_length * tx_speed / 1000)))
        window.insstr(1, 5 + graph_length, "] %6.1f Mbit/s" % tx_speed)
        yield None


def __iostat(device):
    prev_timstamp = time.time()
    with open(path.join(device, "stat")) as f:
        output = f.read()
    output = output.split()
    prev_read = int(output[2])
    prev_write = int(output[6])

    while True:
        timestamp = time.time()
        with open(path.join(device, "stat")) as f:
            output = f.read()
        output = output.split()
        read = int(output[2])
        write = int(output[6])
        read_speed = (read - prev_read) / (timestamp - prev_timstamp) * 512
        write_speed = (write - prev_write) / (timestamp - prev_timstamp) * 512
        prev_timstamp = timestamp
        prev_read = read
        prev_write = write
        yield (read_speed, write_speed)


def draw_iostat(window, height, width, device):
    iostat_generator = __iostat(device)
    graph_length = width - 22
    while True:
        read_speed, write_speed = iostat_generator.next()
        read_speed = read_speed / 1000**2
        write_speed = write_speed / 1000**2

        window.addstr(0, 0, "read:  [")
        __draw_bar(window, 0, 8,
                   graph_length, int(round(graph_length * read_speed / 100)))
        window.insstr(0, 8 + graph_length, "] %5.1f MB/s" % read_speed)

        window.addstr(1, 0, "write: [")
        __draw_bar(window, 1, 8,
                   graph_length, int(round(graph_length * write_speed / 100)))
        window.insstr(1, 8 + graph_length, "] %5.1f MB/s" % write_speed)
        yield None


def draw_sensors(window, height, width):
    import subprocess
    output = check_output(["sensors", "-u"], stderr=subprocess.STDOUT)
    # output = output.decode("utf8")
    output = output.split("\n")
    sensor = dict()
    for line in output:
        if line[:8] == "  temp1_":
            line = line.split(": ")
            sensor[line[0][8:]] = float(line[1])
    color = green
    if sensor["input"] >= sensor["max"]:
        color = yellow
    if sensor["input"] >= sensor["crit"]:
        color = red
    window.addstr(0, 0, "CPU")
    window.insstr(0, 4, "%3.0fC" % sensor["input"], color)
    # return "CPU %5.1f°C" % (sensor["input"])


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
    load = ColorFrame(3, 19, 0, 0, draw_load, "load")
    # date
    date = Frame(3, 21, 0, 59, get_date, "date")
    # df
    df = ColorFrame(8, 80, 3, 0,
                    lambda w, y, x: draw_df(w, y, x, ["/",
                                                      "/home",
                                                      "/usr",
                                                      "/var",
                                                      "/tmp"]),
                    "df")
    # uptime
    utime = Frame(3, 16, 0, 19, get_uptime, "uptime")
    # iotop
    iostat = ColorGeneratorFrame(4, 60, 25, 0,
                                 lambda w, y, x: draw_iostat(w, y, x, "/sys/class/block/sdb"),
                                 "sdb")
    # vnstat
    nstat = ColorGeneratorFrame(4, 60, 21, 0,
                                lambda w, y, x: draw_netstat(w, y, x, "/sys/class/net/em1"),
                                "em1")
    # # hddtem
    hddtemp = ColorFrame(6, 16, 11, 0,
                         lambda y, x, w: draw_hddtemp(y, x, w, ["/dev/sdb"]),
                         "hddtemp")
    # sensors
    sensors = ColorFrame(3, 10, 0, 39, draw_sensors, "temp")
    # raidstatus
    # smart status
    # ip
    ip = Frame(4, 42, 11, 16, lambda y, x: get_ip(y, x, "em1"), "ip")
    # uname
    # vmstat/mem
    # virsh list
    # (ftp-status)
    # test = Frame(25, 80, 0, 0, lambda y, x: "1234567890", "test")
    frames = [date, load, df, utime, ip, nstat, nstat, iostat, hddtemp, sensors]

    while True:
        for frame in frames:
            frame.update()
        time.sleep(1)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
