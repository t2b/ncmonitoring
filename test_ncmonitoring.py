#!/usr/bin/env python3

import ncmonitoring as ncm

print("load")
print(ncm.get_load(3, 50))

print()
print("date")
print(ncm.get_date(3, 50))

print()
print("df")
print(ncm.get_df(3, 50, ["/", "/home"]))
