# `something-to-xes.py`

This repository contains `something-to-xes.py`, the all-purpose power tool I
developed over the years for converting logs of many kinds into
[XES](http://www.xes-standard.org/) traces. It turns one or more XML- or
CSV-format flat event logs into a single XES log with events nicely grouped
into traces according to user-defined mappings.

The script will print usage help for all of its (many!) command-line options
when used with the `--help` option.

## Dependencies

* Python 2.7 (Python 3 is, due to `unicode` peculiarities, not yet supported)
* `lxml` (Debian package `python-lxml`, `pip` package `lxml`)
* `dateutil` (Debian and `pip` package `python-dateutil`)

