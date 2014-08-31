#!/usr/bin/env python2

import ncmonitoring as ncm

import time

print("load")
print(ncm.get_load(3, 50))

print()
print("date")
print(ncm.get_date(3, 50))

print()
print("df")
print(ncm.get_df(3, 50, ["/", "/home"]))

print
print("ip")
print(ncm.get_ip(3, 19, "em1"))


netstat = ncm.get_netstat(13, 14, "/sys/class/net/em1/")
for _ in range(150):
    print netstat.next(1, 3)
    time.sleep(.1)
