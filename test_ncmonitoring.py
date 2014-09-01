#!/usr/bin/env python2

import ncmonitoring as ncm

# import time

print("load")
print(ncm.get_load(3, 50))

print()
print("date")
print(ncm.get_date(3, 50))

print
print("ip")
print(ncm.get_ip(3, 19, "em1"))

print
print "libvirt"
print ncm.get_libvirt(1, 2)

print
print "uname"
print ncm.get_uname(1, 40)
print ncm.get_uname(2, 1)

print "smart"
print ncm.draw_smart(0, 1, 2)

# print
# print "mdstat"
# print ncm.get_mdstat(1, 2)

# netstat = ncm.get_netstat(13, 14, "/sys/class/net/em1/")
# for _ in range(150):
#     print netstat.next(1, 3)
#     time.sleep(.1)

# iostat = ncm.iostat("/sys/class/block/sdb")
# for _ in range(150):
#     print iostat.next()
#     time.sleep(1)
