#!/usr/bin/env python2

import ncmonitoring as ncm

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

print
print "hddtemp"
print ncm.draw_hddtemp(3, 30, None, ["/dev/sdb"])
