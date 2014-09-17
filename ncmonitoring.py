#!/usr/bin/env python2
# -*- coding: utf8 -*-

execfile("env/bin/activate_this.py", dict(__file__="env/bin/activate_this.py"))

import ConfigParser
import urwid
import curses
import time
import subprocess
from subprocess import check_output
import uptime
import netifaces
from telnetlib import Telnet
import socket
from srmqt4 import mdstat
import psutil
from natural import constant as natural_constant
from natural import size as natural_size


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

    def update(self, refresh=True):
        if self._borderwindow:
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
                self._contentwindow.insstr(i, 0, content[i])
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
    time_format = "%F %T"
    if width < 19:
        time_format = "%T"
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
        color = COLOR_GREEN
        if load[i] > 2:
            color = COLOR_YELLOW
        if load[i] > 4:
            color = COLOR_RED
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
                  graph[:min(value, warning)], COLOR_GREEN)
    window.addstr(pos_y,
                  pos_x + warning,
                  graph[min(value, warning):min(value, critical)], COLOR_YELLOW)
    window.addstr(pos_y,
                  pos_x + critical,
                  graph[min(value, critical):value], COLOR_RED)
    window.addstr(pos_y,
                  pos_x + value,
                  graph[value:], COLOR_GREY + curses.A_BOLD)


def pretty_size(value, suffix_format='decimal', digits=4):
    suffix = natural_constant.FILESIZE_SUFFIX[suffix_format]
    base = natural_size.FILESIZE_BASE[suffix_format]
    exponent = 0
    value = float(value)
    while value >= 1000:
        exponent += 1
        value = value / base
    format_string = "%." + str(digits) + "f"
    value = format_string % value
    value = value[:digits].strip('.')
    return (value, suffix[exponent])


def draw_df(window, heigth, width, mountpoints=["/"]):
    digits = 4
    if width < 40:
        mountname_length = int(width - 12) / 2
    else:
        mountname_length = 15
    mountname_length = min(mountname_length, max(map(len, mountpoints)))
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
    minutes, _ = divmod(utime, 60)
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
    try:
        telnet_conncection = Telnet()
        telnet_conncection.open("localhost", 7634)
        output = telnet_conncection.read_all()
        telnet_conncection.close()
    except socket.error as error:
        window.addstr(0, 0, str(error)[:heigth*width-1], COLOR_WARNING)
        return
    seperator = '|'
    output = output.split(seperator * 2)
    output = map(lambda x: x.strip(seperator).split(seperator), output)

    line = 0
    for hddtemp in output:
        color = curses.color_pair(0)
        try:
            temp = float(hddtemp[2])
            if temp < 40:
                color = COLOR_GREEN
            if 40 <= temp < 50:
                color = COLOR_YELLOW
            if temp > 50:
                color = COLOR_RED
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


def draw_netstat(window, height, width, device, max_rx, max_tx):
    netstat_generator = __netstat(device)
    graph_length = width - 8
    digits = 4
    while True:
        rx_speed, tx_speed = netstat_generator.next()

        window.addstr(0, 0, "rx: [")
        __draw_bar(window, 0, 5,
                   graph_length,
                   int(round(graph_length * rx_speed / max_rx)),
                   "".join(pretty_size(rx_speed, digits=digits)) + "it/s")
        window.insstr(0, 5 + graph_length, "]")

        window.addstr(1, 0, "tx: [")
        __draw_bar(window, 1, 5,
                   graph_length,
                   int(round(graph_length * tx_speed / max_tx)),
                   "".join(pretty_size(tx_speed, digits=digits)) + "it/s")
        window.insstr(1, 5 + graph_length, "]")
        yield None


def __iostat(device):
    prev_timstamp = time.time()

    disk_io_counters = psutil.disk_io_counters(perdisk=True)
    prev_read = disk_io_counters[device].read_bytes
    prev_write = disk_io_counters[device].write_bytes

    while True:
        timestamp = time.time()
        disk_io_counters = psutil.disk_io_counters(perdisk=True)
        read = disk_io_counters[device].read_bytes
        write = disk_io_counters[device].write_bytes
        read_speed = (read - prev_read) / (timestamp - prev_timstamp)
        write_speed = (write - prev_write) / (timestamp - prev_timstamp)
        prev_timstamp = timestamp
        prev_read = read
        prev_write = write
        yield (read_speed, write_speed)


def draw_iostat(window, height, width, device, max_read, max_write):
    iostat_generator = __iostat(device)
    graph_length = width - 11
    digits = 4
    while True:
        read_speed, write_speed = iostat_generator.next()

        window.addstr(0, 0, "read:  [")
        __draw_bar(window, 0, 8,
                   graph_length,
                   int(round(graph_length * read_speed / max_read)),
                   "".join(pretty_size(read_speed, digits=digits)) + "/s")
        window.insstr(0, 8 + graph_length, "]")

        window.addstr(1, 0, "write: [")
        __draw_bar(window, 1, 8,
                   graph_length,
                   int(round(graph_length * write_speed / max_write)),
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
    color = COLOR_GREEN
    if sensor["input"] >= sensor["max"]:
        color = COLOR_YELLOW
    if sensor["input"] >= sensor["crit"]:
        color = COLOR_RED
    window.addstr(0, 0, "CPU")
    window.insstr(0, 4, "%3.0fC" % sensor["input"], color)
    # return "CPU %5.1f°C" % (sensor["input"])


def draw_libvirt(window, heigth, width):
    name_length = width - 8
    output = check_output(["virsh", "list", "--all"])
    output = output.split("\n")
    output = output[2:]
    line_number = 0
    for line in output:
        line = line.split()
        if len(line) < 3:
            continue
        vm_name = line[1]
        vm_state = " ".join(line[2:])
        vm_state = vm_state.strip()
        window.addstr(line_number, 0, vm_name[:name_length])
        color = COLOR_RED
        if vm_state == "running":
            color = COLOR_GREEN
        if vm_state == "paused":
            color = COLOR_YELLOW
        window.insstr(line_number, name_length, vm_state, color)
        # format_string = "{:<%i} {:<8}" % name_length
        # vm = format_string.format(vm_name, vm_state)
        line_number += 1


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

        color = COLOR_DEFAULT
        if degraded > 0:
            color = COLOR_WARNING

        main_status = "{:<5} {:<6} {:<6} {:<6} ".format(dev_name,
                                                        active,
                                                        personality,
                                                        raid_status)
        window.addstr(line, 0, main_status, color)

        resyc_finish = resyc_finish.replace("min", "'")
        resync_status = "{:<7} {:>8}".format(resyc_type, resyc_finish)
        if color == COLOR_DEFAULT:
            color = COLOR_YELLOW
        window.insstr(line, 27, resync_status, color)
        line += 0


def draw_memory(window, heigth, width):
    graph_length = width - 7
    digits = 4

    memory = psutil.virtual_memory()

    memory_graph = '|' * int(round(float(memory.used) / memory.total
                                   * graph_length))
    memory_graph = memory_graph + ' ' * (graph_length - len(memory_graph))
    memory_usage = "".join(pretty_size(memory.total - memory.available,
                                       digits=digits)) \
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
                  memory_graph[:buffer_start], COLOR_GREEN)
    window.addstr(0, 6 + buffer_start,
                  memory_graph[buffer_start:cashed_start], COLOR_BLUE)
    window.addstr(0, 6 + cashed_start,
                  memory_graph[cashed_start:free_start], COLOR_YELLOW)
    window.addstr(0, 6 + free_start,
                  memory_graph[free_start:], COLOR_GREY + curses.A_BOLD)
    window.insstr(0, width - 1, ']')

    swap = psutil.swap_memory()

    swap_usage = "".join(pretty_size(swap.used, digits=digits)) \
        + "/" + "".join(pretty_size(swap.total, digits=digits))

    window.addstr(1, 0, "swap [")
    __draw_bar(window, 1, 6, graph_length,
               int(round(float(swap.used) / swap.total * graph_length)),
               swap_usage, 0, 0)
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
        color = COLOR_RED
        if status == "PASSED":
            color = COLOR_GREEN
        if status == "UNKNOWN":
            color = COLOR_YELLOW
        window.insstr(line, 10, status, color)
        # print dev, status
        line += 1


def get_performence(height, width):
    prev_time = time.time()
    while True:
        now = time.time()
        delta = now - prev_time
        prev_time = now
        yield "\n".join(["%17.6f" % delta,
                         "%17.6f" % now])


def config2dict(config):
    config_dict = dict()

    for key, value in config:
        config_dict[key] = value
    return config_dict


def main(_):
    config = ConfigParser.ConfigParser()
    config.read("config.cfg")

    ip_config = config.items("ip")
    ip_config = config2dict(ip_config)

    netstat_config = config.items("netstat")
    netstat_config = config2dict(netstat_config)
    netstat_config["max_tx"] = float(netstat_config["max_tx"]) * 1000**2
    netstat_config["max_rx"] = float(netstat_config["max_rx"]) * 1000**2

    iostat_config = config.items("iostat")
    iostat_config = config2dict(iostat_config)
    iostat_config["max_read"] = float(iostat_config["max_read"]) * 1024**2
    iostat_config["max_write"] = float(iostat_config["max_write"]) * 1024**2

    diskusage_config = config.items("diskusage")
    diskusage_config = config2dict(diskusage_config)
    diskusage_config["devicelist"] = map(str.strip, diskusage_config["devicelist"].split(","))

    smart_config = config.items("smart")
    smart_config = config2dict(smart_config)
    smart_config["devicelist"] = map(str.strip, smart_config["devicelist"].split(","))

    # load
    load = ColorFrame(3, 19, 1, 16, draw_load, "load")
    # date
    date = Frame(1, 19, 0, 61, get_date)
    # df
    df = ColorFrame(6, 61, 8, 19,
                    lambda w, y, x: draw_df(w, y, x, diskusage_config["devicelist"]),
                    "df")
    # uptime
    utime = Frame(3, 16, 1, 0, get_uptime, "uptime")
    # iotop
    def draw_iostat_(window, height, width):
        return draw_iostat(window, height, width,
                           iostat_config["device"],
                           max_read=iostat_config["max_read"],
                           max_write=iostat_config["max_write"])

    iostat = ColorGeneratorFrame(4, 61, 18, 19,
                                 draw_iostat_,
                                 iostat_config["device"])
    # vnstat
    def draw_netstat_(window, height, width):
        return draw_netstat(window, height, width,
                            netstat_config["interface"],
                            max_rx=netstat_config["max_rx"],
                            max_tx=netstat_config["max_tx"])

    nstat = ColorGeneratorFrame(4, 61, 14, 19,
                                draw_netstat_, netstat_config["interface"])
    # hddtem
    hddtemp = ColorFrame(6, 16, 12, 0, draw_hddtemp, "hddtemp")
    # sensors
    sensors = ColorFrame(3, 10, 22, 19, draw_sensors, "temp")
    # raidstatus
    raid = ColorFrame(3, 45, 22, 35, draw_mdstat, "mdadm")
    # smart status
    smart = ColorFrame(7, 19, 18, 0,
                       lambda w, y, x: draw_smart(w, y, x, smart_config["devicelist"]),
                       "SMART")
    # ip
    ip = Frame(4, 42, 0, 38,
               lambda y, x: get_ip(y, x, ip_config["interface"]),
               "ip")
    # uname
    uname = Frame(1, 38, 0, 0, get_uname)
    # vmstat/mem
    memory = ColorFrame(4, 61, 4, 19, draw_memory, "mem")
    # virsh list
    libvirt = ColorFrame(8, 19, 4, 0, draw_libvirt, "libvirt")
    # (ftp-status)

    # def test_func(y, x):
    #     line = "%" * x
    #     retval = []
    #     for _ in xrange(y):
    #         retval.append(line)
    #     return "\n".join(retval)
    #
    # test = Frame(25, 80, 0, 0, test_func, "test")
    # test.update()
    # time.sleep(5)

    performence = None
    performence = GeneratorFrame(2, 20, 25, 0, get_performence)

    frames_high_frequency = [date,
                             load,
                             nstat,
                             iostat,
                             memory]
    frames_low_frequency = [df,
                            utime,
                            hddtemp,
                            sensors,
                            libvirt,
                            raid,
                            uname,
                            smart,
                            ip]

    while True:
        for frame in frames_low_frequency:
            frame.update()
        for _ in xrange(3):
            if performence:
                performence.update()
            for frame in frames_high_frequency:
                frame.update()
            time.sleep(1)


if __name__ == "__main__":
    txt = urwid.Text(u"loading monitoring screen...", "center")
    fill = urwid.Filler(txt, "middle")
    loop = urwid.MainLoop(fill)
    loop.screen.start()
    loop.draw_screen()
    time.sleep(1)

    # start
    stdscr = curses.initscr()
    # Keine Anzeige gedrückter Tasten
    curses.noecho()
    # Kein line-buffer
    curses.cbreak()
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.start_color()

    COLOR_DEFAULT = curses.color_pair(0)

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    COLOR_GREEN = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    COLOR_YELLOW = curses.color_pair(2)

    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    COLOR_RED = curses.color_pair(3)

    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
    COLOR_WARNING = curses.color_pair(4)

    curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)
    COLOR_BLUE = curses.color_pair(5)

    curses.init_pair(6, curses.COLOR_BLACK + 8, curses.COLOR_BLACK)
    COLOR_GREY = curses.color_pair(6)

    curses.wrapper(main)

    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
