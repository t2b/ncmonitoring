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
print(ncm.get_ip(3, 19, "p6p1"))

print
print "libvirt"
print ncm.get_libvirt(1, 2)

print
print "uname"
print ncm.get_uname(1, 40)
print ncm.get_uname(2, 1)

print "natural"
# import natural
# print help(natural)
# from natural import constant
# print help(constant)
# from natural import data
# print help(data)
# from natural import date
# print help(date)
# from natural import file
# print help(file)
# from natural import number
# print help(number)
# from natural import size
# print help(size)
# from natural import text
# print help(text)
#
# print "number", number.number(12345678)
# print "size.binary", size.binarysize(12345678)
# print "size.decimal", size.decimalsize(12345678)
# print "size.gnu", size.gnusize(12345678)
for n in range(0, 20):
    print ''.join(ncm.pretty_size(11**n))
# print text.nato("ttb")

# netstat = ncm.get_netstat(13, 14, "/sys/class/net/em1/")
# for _ in range(150):
#     print netstat.next(1, 3)
#     time.sleep(.1)

# iostat = ncm.iostat("/sys/class/block/sdb")
# for _ in range(150):
#     print iostat.next()
#     time.sleep(1)
