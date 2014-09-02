#!/usr/bin/env python2
# -*- coding: utf8 -*-

execfile("env/bin/activate_this.py", dict(__file__="env/bin/activate_this.py"))

import curses
import time
import subprocess
from subprocess import check_output
import uptime
import netifaces
from os import path
from telnetlib import Telnet
from srmqt4 import mdstat
import psutil
from natural import size as naturalsize


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
            # self._borderwindow.clear()
            self._borderwindow.border()
            self._borderwindow.addstr(0, 1, self._title)

        # self._contentwindow.clear()
        self.clear()
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

    def clear(self):
        whitespaces = " " * self._content_width
        for line in range(self._content_height):
            self._contentwindow.insstr(line, 0, whitespaces)


class ColorFrame(Frame):
    def update(self, refresh=True):
        if self._borderwindow:
            # self._borderwindow.clear()
            self._borderwindow.border()
            self._borderwindow.addstr(0, 1, self._title)

        # self._contentwindow.clear()
        self.clear()
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
        color = color_green
        if load[i] > 2:
            color = color_yellow
        if load[i] > 4:
            color = color_red
        value = "%5.2f" % load[i]
        window.addstr(0, i * 6, value[-1:], color)
        window.insstr(0, i * 6, value[:-1], color)


def __draw_bar(window, pos_y, pos_x,
               length, value,
               usage_string="", warning=None, critical=None, sign="|"):
    if value > length:
        value = length
    if critical is None:
        critical = int(length * 0.9)
        if length > 1 and critical == length:
            critical = length - 1

    if warning is None:
        warning = int(length * 0.8)
        if critical > 1 and warning >= critical:
            warning = critical - 1

    graph = sign * value
    graph = graph + " " * (length - value)
    if len(usage_string) > 0:
        graph = graph[:-len(usage_string)] + usage_string

    window.addstr(pos_y,
                  pos_x,
                  graph[:min(value, warning)], color_green)
    window.addstr(pos_y,
                  pos_x + warning,
                  graph[min(value, warning):min(value, critical)], color_yellow)
    window.addstr(pos_y,
                  pos_x + critical,
                  graph[min(value, critical):value], color_red)
    window.addstr(pos_y,
                  pos_x + value,
                  graph[value:], color_grey + curses.A_BOLD)


def pretty_size(value, format='decimal', digits=4):
    pretty_value = naturalsize.filesize(value, format=format, digits=digits)
    pretty_value = pretty_value.split()
    pretty_value[0] = pretty_value[0][:digits]
    pretty_value[0] = pretty_value[0].strip('.')
    return pretty_value


def draw_df(window, heigth, width, mountpoints=["/"]):
    digits = 4
    if width < 40:
        mountname_length = int(width - 12) / 2
    else:
        mountname_length = 15
    graph_width = width - mountname_length - 3

    line = 0
    for mount in mountpoints:
        disk_stat = psutil.disk_usage(mount)
        size = disk_stat.total
        size = ''.join(pretty_size(size, digits=digits))
        used = disk_stat.used
        used = ''.join(pretty_size(used, digits=digits))
        percent = disk_stat.percent
        percent = int(percent * graph_width / 100)

        window.addstr(line,
                      0,
                      mount[-mountname_length:])
        window.addstr(line,
                      mountname_length + 1,
                      '[')
        __draw_bar(window, line, mountname_length + 2,
                   graph_width, percent, used + "/" + size)
        window.insstr(line,
                      mountname_length + 2 + graph_width,
                      ']')

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
        pass
        # ret_val.append("")

    try:
        ip = ip_list[netifaces.AF_INET6]
        ip = ip[0]
        ip = ip['addr']
        ret_val.append(ip[-width:])
    except KeyError:
        pass
        # ret_val.append("")

    ret_val = ret_val[:heigth]

    return "\n".join(ret_val)


def draw_hddtemp(window, heigth, width):
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
                color = color_green
            if 40 <= temp < 50:
                color = color_yellow
            if temp > 50:
                color = color_red
        except ValueError:
            pass
        window.addstr(line, 0, hddtemp[0][-9:])
        window.addstr(line, 10, (" " + hddtemp[2])[-3:], color)
        window.insstr(line, 13, hddtemp[3][-1:], color)
        line += 1


def __netstat(device):
    prev_timestamp = time.time()
    net_io_counters = psutil.net_io_counters(pernic=True)
    prev_tx_bytes = net_io_counters[device].bytes_sent
    prev_rx_bytes = net_io_counters[device].bytes_recv

    while True:
        timestamp = time.time()
        net_io_counters = psutil.net_io_counters(pernic=True)
        tx_bytes = net_io_counters[device].bytes_sent
        rx_bytes = net_io_counters[device].bytes_recv

        rx_speed = (rx_bytes - prev_rx_bytes) \
            / (timestamp - prev_timestamp) * 8
        prev_rx_bytes = rx_bytes

        tx_speed = (tx_bytes - prev_tx_bytes) \
            / (timestamp - prev_timestamp) * 8
        prev_tx_bytes = tx_bytes

        prev_timestamp = timestamp
        yield (rx_speed, tx_speed)


def draw_netstat(window, height, width, device):
    netstat_generator = __netstat(device)
    graph_length = width - 8
    digits = 4
    while True:
        rx_speed, tx_speed = netstat_generator.next()

        window.addstr(0, 0, "rx: [")
        __draw_bar(window, 0, 5,
                   graph_length,
                   int(round(graph_length * rx_speed / 1024**3)),
                   "".join(pretty_size(rx_speed, digits=digits)) + "it/s")
        window.insstr(0, 5 + graph_length, "]")

        window.addstr(1, 0, "tx: [")
        __draw_bar(window, 1, 5,
                   graph_length,
                   int(round(graph_length * tx_speed / 1024**3)),
                   "".join(pretty_size(tx_speed, digits=digits)) + "it/s")
        window.insstr(1, 5 + graph_length, "]")
        yield None


def __iostat(device):
    prev_timstamp = time.time()

    disk_io_counters = psutil.disk_io_counters(perdisk=True)
    # with open(path.join(device, "stat")) as f:
    #     output = f.read()
    # output = output.split()
    # prev_read = int(output[2])
    # prev_write = int(output[6])
    prev_read = disk_io_counters[device].read_bytes
    prev_write = disk_io_counters[device].write_bytes

    while True:
        timestamp = time.time()
        # with open(path.join(device, "stat")) as f:
        #     output = f.read()
        # output = output.split()
        # read = int(output[2])
        # write = int(output[6])
        disk_io_counters = psutil.disk_io_counters(perdisk=True)
        read = disk_io_counters[device].read_bytes
        write = disk_io_counters[device].write_bytes
        read_speed = (read - prev_read) / (timestamp - prev_timstamp)
        write_speed = (write - prev_write) / (timestamp - prev_timstamp)
        prev_timstamp = timestamp
        prev_read = read
        prev_write = write
        yield (read_speed, write_speed)


def draw_iostat(window, height, width, device):
    iostat_generator = __iostat(device)
    graph_length = width - 11
    digits = 4
    while True:
        read_speed, write_speed = iostat_generator.next()

        window.addstr(0, 0, "read:  [")
        __draw_bar(window, 0, 8,
                   graph_length,
                   int(round(graph_length * read_speed / 1024**2 / 100)),
                   "".join(pretty_size(read_speed, digits=digits)) + "/s")
        window.insstr(0, 8 + graph_length, "]")

        window.addstr(1, 0, "write: [")
        __draw_bar(window, 1, 8,
                   graph_length,
                   int(round(graph_length * write_speed / 1024**2 / 100)),
                   "".join(pretty_size(write_speed, digits=digits)) + "/s")
        window.insstr(1, 8 + graph_length, "]")
        yield None


def draw_sensors(window, height, width):
    output = check_output(["sensors", "-u"], stderr=subprocess.STDOUT)
    # output = output.decode("utf8")
    output = output.split("\n")
    sensor = dict()
    for line in output:
        if line[:8] == "  temp1_":
            line = line.split(": ")
            sensor[line[0][8:]] = float(line[1])
    color = color_green
    if sensor["input"] >= sensor["max"]:
        color = color_yellow
    if sensor["input"] >= sensor["crit"]:
        color = color_red
    window.addstr(0, 0, "CPU")
    window.insstr(0, 4, "%3.0fC" % sensor["input"], color)
    # return "CPU %5.1f°C" % (sensor["input"])


def get_libvirt(heigth, width):
    output = check_output(["virsh", "list", "--all"])
    output = output.split("\n")
    output = output[2:]
    ret_val = []
    for line in output:
        line = line.split()
        if len(line) < 3:
            continue
        vm_name = line[1]
        vm_state = " ".join(line[2:])
        vm = "{:<15} {:<8}".format(vm_name, vm_state)
        ret_val.append(vm)
    return "\n".join(ret_val)


def draw_mdstat(window, heigth, width):
    status = mdstat.get_status()

    # sample no raid
    # status = {'personalities': '\n',
    #           'devices': {},
    #           'unused devices': '<none>\n'}

    # sample active raid
    # status = {'personalities': '[raid6] [raid5] [raid4] \n',
    #           'devices': {'md0': {'read_only': '',
    #                               'pers': 'raid5',
    #                               'blocks': 8790405120,
    #                               'raid': {'status': 'UUUU',
    #                                        'algorithm': '2',
    #                                        'level': '5',
    #                                        'nondegraded': 4,
    #                                        'chunk': '512k',
    #                                        'total': 4,
    #                                        'degraded': 0},
    #                               'active': True,
    #                               'resync': {'type': ''},
    #                               'disks': {0: {'type': '',
    #                                             'name': 'sdc'},
    #                                         1: {'type': '',
    #                                             'name': 'sdd'},
    #                                         3: {'type': '',
    #                                             'name': 'sde'},
    #                                         4: {'type': '',
    #                                             'name': 'sdb'}},
    #                               'super': '1.2',
    #                               'bitmap': {}
    #                               }
    #                       },
    #           'unused devices': '<none>\n'}

    # sample raid check
    # status = {'personalities': '[raid6] [raid5] [raid4] \n',
    #           'devices': {'md0': {'read_only': '',
    #                               'pers': 'raid5',
    #                               'blocks': 8790405120,
    #                               'raid': {'status': 'UUUU',
    #                                        'algorithm': '2',
    #                                        'level': '5',
    #                                        'nondegraded': 4,
    #                                        'chunk': '512k',
    #                                        'total': 4,
    #                                        'degraded': 0},
    #                               'active': True,
    #                               'resync': {'finish': '560.3min',
    #                                          'blocks': 1828880,
    #                                          'max_blocks': 2930135040,
    #                                          'percent': 0.0,
    #                                          'type': 'check',
    #                                          'speed': '87089K/sec'},
    #                               'disks': {0: {'type': '',
    #                                             'name': 'sdc'},
    #                                         1: {'type': '',
    #                                             'name': 'sdd'},
    #                                         3: {'type': '',
    #                                             'name': 'sde'},
    #                                         4: {'type': '',
    #                                             'name': 'sdb'}},
    #                               'super': '1.2',
    #                               'bitmap': {}
    #                               }
    #                       },
    #           'unused devices': '<none>\n'}

    # sample raid degraded
    # status = {'personalities': '[raid6] [raid5] [raid4] \n',
    #           'devices': {'md0': {'read_only': '',
    #                               'pers': 'raid5',
    #                               'blocks': 8790405120,
    #                               'raid': {'status': 'UU_U',
    #                                        'algorithm': '2',
    #                                        'level': '5',
    #                                        'nondegraded': 3,
    #                                        'chunk': '512k',
    #                                        'total': 4,
    #                                        'degraded': 1},
    #                               'active': True,
    #                               'resync': {'finish': '560.3min',
    #                                          'blocks': 1828880,
    #                                          'max_blocks': 2930135040,
    #                                          'percent': 0.0,
    #                                          'type': 'resync',
    #                                          'speed': '87089K/sec'},
    #                               'disks': {0: {'type': '',
    #                                             'name': 'sdc'},
    #                                         1: {'type': '',
    #                                             'name': 'sdd'},
    #                                         3: {'type': '',
    #                                             'name': 'sde'},
    #                                         4: {'type': '',
    #                                             'name': 'sdb'}},
    #                               'super': '1.2',
    #                               'bitmap': {}
    #                               }
    #                       },
    #           'unused devices': '<none>\n'}

    line = 0
    for dev_name in status['devices']:
        active = False
        personality = ""
        raid_status = ""
        degraded = 0
        resyc_type = ''
        resyc_finish = ''

        dev = status['devices'][dev_name]

        if 'active' in dev:
            active = dev['active']

        if 'pers' in dev:
            personality = dev['pers']

        if 'raid' in dev:
            raid_status_dict = dev['raid']

            if 'status' in raid_status_dict:
                raid_status = raid_status_dict['status']

            if 'degraded' in raid_status_dict:
                degraded = raid_status_dict['degraded']

        if 'resync' in dev:
            resync = dev['resync']

            if 'type' in resync:
                resyc_type = resync['type']

            if 'finish' in resync:
                resyc_finish = resync['finish']

        if active:
            active = "active"

        color = color_default
        if degraded > 0:
            color = color_warning

        main_status = "{:<5} {:<6} {:<6} {:<6} ".format(dev_name,
                                                        active,
                                                        personality,
                                                        raid_status)
        window.addstr(line, 0, main_status, color)

        resyc_finish = resyc_finish.replace("min", "'")
        resync_status = "{:<7} {:>8}".format(resyc_type, resyc_finish)
        if color == color_default:
            color = color_yellow
        window.insstr(line, 27, resync_status, color)
        line += 0


def draw_memory(window, heigth, width):
    graph_length = width - 7
    digits = 4

    memory = psutil.virtual_memory()

    memory_graph = '|' * int(round(float(memory.used) / memory.total
                                   * graph_length))
    memory_graph = memory_graph + ' ' * (graph_length - len(memory_graph))
    memory_usage = "".join(pretty_size(memory.total - memory.available, digits=digits)) \
        + "/" + "".join(pretty_size(memory.total, digits=digits))
    memory_graph = memory_graph[:-len(memory_usage)] + memory_usage

    buffer_start = int(round(float(memory.total - memory.available) /
                             memory.total * graph_length))
    cashed_start = int(round(float(memory.total - memory.available
                                   + memory.buffers) /
                             memory.total * graph_length))
    free_start = int(round(float(memory.used) / memory.total * graph_length))

    window.addstr(0, 0, "mem  [")
    window.addstr(0, 6,
                  memory_graph[:buffer_start], color_green)
    window.addstr(0, 6 + buffer_start,
                  memory_graph[buffer_start:cashed_start], color_blue)
    window.addstr(0, 6 + cashed_start,
                  memory_graph[cashed_start:free_start], color_yellow)
    window.addstr(0, 6 + free_start,
                  memory_graph[free_start:], color_grey + curses.A_BOLD)
    window.insstr(0, width - 1, ']')

    swap = psutil.swap_memory()

    swap_graph = "|" * int(round(float(swap.used) / swap.total * graph_length))
    free_start = len(swap_graph)
    swap_graph = swap_graph + ' ' * (graph_length - len(swap_graph))
    swap_usage = "".join(pretty_size(swap.used, digits=digits)) \
        + "/" + "".join(pretty_size(swap.total, digits=digits))
    swap_graph = swap_graph[:-len(swap_usage)] + swap_usage

    window.addstr(1, 0, "swap [")
    window.addstr(1, 6, swap_graph[:free_start], color_red)
    window.addstr(1, 6 + free_start, swap_graph[free_start:],
                  color_grey + curses.A_BOLD)
    window.insstr(1, width - 1, ']')


def get_uname(heigth, width):
    nodename = check_output(["uname", "--nodename"]).strip()
    kernel_release = check_output(["uname", "--kernel-release"]).strip()
    if heigth >= 2:
        return nodename + '\n' + kernel_release
    if len(nodename) + len(kernel_release) + 1 <= width:
        return nodename + " " + kernel_release
    return nodename


def draw_smart(window, height, width, devices):
    line = 0
    for dev in devices:
        output = check_output(["smartctl", "-H", dev])
        output = output.split('\n')
        status = "UNKNOWN"
        for output_line in output:
            output_line = output_line.split(": ")
            magic_line = "SMART overall-health self-assessment test result"
            if not output_line[0] == magic_line:
                continue
            status = output_line[1].strip()
            # print dev, status
        window.addstr(line, 0, dev)
        color = color_red
        if status == "PASSED":
            color = color_green
        if status == "UNKNOWN":
            color = color_yellow
        window.insstr(line, 10, status, color)
        # print dev, status
        line += 1


if __name__ == "__main__":
    # start
    stdscr = curses.initscr()
    # Keine Anzeige gedrückter Tasten
    curses.noecho()
    # Kein line-buffer
    curses.cbreak()
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.start_color()

    color_default = curses.color_pair(0)

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    color_green = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    color_yellow = curses.color_pair(2)

    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    color_red = curses.color_pair(3)

    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
    color_warning = curses.color_pair(4)

    curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)
    color_blue = curses.color_pair(5)

    curses.init_pair(6, curses.COLOR_BLACK + 8, curses.COLOR_BLACK)
    color_grey = curses.color_pair(6)

    # load
    load = ColorFrame(4, 19, 3, 0, draw_load, "load")
    # date
    date = Frame(3, 21, 0, 59, get_date, "date")
    # df
    __df_dev = ["/", "/home", "/tmp"]
    df = ColorFrame(5, 55, 7, 0,
                    lambda w, y, x: draw_df(w, y, x, __df_dev),
                    "df")
    # uptime
    utime = Frame(3, 16, 0, 0, get_uptime, "uptime")
    # iotop
    __iostat_dev = "sda2"
    iostat = ColorGeneratorFrame(4, 61, 16, 19,
                                 lambda w, y, x: draw_iostat(w, y, x,
                                                             __iostat_dev),
                                 "sda")
    # vnstat
    __nstat_dev = "wlp1s0"
    nstat = ColorGeneratorFrame(4, 61, 12, 19,
                                lambda w, y, x: draw_netstat(w, y, x,
                                                             __nstat_dev),
                                "p6p1")
    # hddtem
    hddtemp = ColorFrame(6, 16, 12, 0,
                         lambda w, y, x: draw_hddtemp(w, y, x),
                         "hddtemp")
    # sensors
    sensors = ColorFrame(3, 10, 20, 19, draw_sensors, "temp")
    # raidstatus
    raid = ColorFrame(3, 45, 20, 35, draw_mdstat, "mdadm")
    # smart status
    __smart_dev = ["/dev/sda"]
    smart = ColorFrame(7, 19, 18, 0,
                       lambda w, y, x: draw_smart(w, y, x, __smart_dev),
                       "SMART")
    # ip
    ip = Frame(3, 42, 23, 38, lambda y, x: get_ip(y, x, "p6p1"), "ip")
    # uname
    uname = Frame(3, 43, 0, 16, get_uname, "host")
    # vmstat/mem
    memory = ColorFrame(4, 61, 3, 19, draw_memory, "mem")
    # virsh list
    libvirt = Frame(5, 25, 7, 55, get_libvirt, "libvirt")
    # (ftp-status)

    def test_func(y, x):
        line = "%" * x
        retval = []
        for _ in xrange(y):
            retval.append(line)
        return "\n".join(retval)
    test = Frame(25, 80, 0, 0, test_func, "test")
    test.update()

    frames_high_frequency = [date,
                             load,
                             nstat,
                             iostat,
                             memory]
    frames_low_frequency = [df,
                            utime,
                            ip,
                            hddtemp,
                            sensors,
                            libvirt,
                            raid,
                            uname,
                            smart]

    while True:
        for frame in frames_low_frequency:
                frame.update()
        for _ in xrange(30):
            for frame in frames_high_frequency:
                frame.update()
            time.sleep(1)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
