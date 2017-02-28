#!/usr/bin/env python
# encoding: utf-8

# something-to-xes.py
# Copyright © 2017 Alexander Faithfull

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranties of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

# something-to-xes converts a XML or CSV document representing an event log
# into a XES document, usable by many process mining tools. It works by
# reducing documents to a flat stream of events with attributes; it then uses
# a user-specified map to convert the attributes of those events into standard
# XES ones.

# The first line of a CSV document should specify the names of each field; each
# subsequent line should specify an event. The parts of a XML document that
# specify events may be extracted using either an XPath expression or a CSS
# selector.

import csv
import sys
from lxml import etree
from lxml.etree import XPath
from lxml.cssselect import CSSSelector
import argparse
import dateutil.parser

def xml_handler(f, selector):
  tree = etree.parse(f)
  for e in selector(tree):
    result = {}
    for child in e:
      result[child.tag] = child.text
      for name, value in child.items():
        result[child.tag + "." + name] = value
    yield result

def utf8(s, errors='strict'):
  return unicode(s, encoding="utf-8", errors=errors)

def csv_handler(f, **fmtparams):
  reader = csv.reader(f, **fmtparams)
  names = map(utf8, next(reader))
  for row in reader:
    yield dict(zip(names, map(utf8, row)))

def xesformat(ts):
  # The XES timestamp format is very nearly compatible with
  # datetime.isoformat(), except that it requires milliseconds instead of any
  # other precision
  base = "%04d-%02d-%02dT%02d:%02d:%02d.%03d" % \
      (ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second,
       round(ts.microsecond / 1000))
  tz = ts.utcoffset()
  if tz:
    hours, minutes = (int(tz / 60), tz % 60)
    if hours < 0:
      return base + ("%d:%d" % (hours, minutes))
    else:
      return base + ("+%d:%d" % (hours, minutes))
  else:
    return base + "Z"

def handle_time(ts):
  return etree.Element(
      "date",
      key="time:timestamp",
      value=xesformat(dateutil.parser.parse(ts)))

types = {
  ("time", "timestamp"): handle_time
}

def dict_to_element(d, mappings, preserve=False):
  el = etree.Element("event")
  for (name, value) in mappings.items():
    p, r = name
    if p:
      raw_name = "%s:%s" % (p, r)
    else:
      raw_name = r
    try:
      actual = value % d
      if not name in types:
        el.append(etree.Element("string", key=raw_name, value=actual))
      else:
        el.append(types[name](actual))
    except KeyError:
      pass
  if preserve:
    for name, value in d.items():
      el.append(etree.Element("string", key=name, value=value if value else ""))
  return el

extensions = {
  "concept": ("Concept", "http://www.xes-standard.org/concept.xesext"),
  "lifecycle": ("Lifecycle", "http://www.xes-standard.org/lifecycle.xesext"),
  "org": ("Organizational", "http://www.xes-standard.org/org.xesext"),
  "time": ("Time", "http://www.xes-standard.org/time.xesext")
}

def get_extension_element(prefix):
  assert prefix in extensions, """\
prefix "%s" does not specify a known standard XES extension""" % prefix
  name, uri = extensions[prefix]
  return etree.Element("extension", name=name, prefix=prefix, uri=uri)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
      'infile',
      metavar='IN',
      help='the input file (defaults to standard input)',
      nargs='?',
      type=argparse.FileType('r'),
      default=sys.stdin)
  parser.add_argument(
      'outfile',
      metavar='OUT',
      help='the output file (defaults to standard output)',
      nargs='?',
      type=argparse.FileType('w'),
      default=sys.stdout)

  xml_group = parser.add_argument_group('XML input arguments')
  xml_group.add_argument(
      '--xml',
      help='parse the input file as a XML document (requires either --xpath ' +
           'or --css)',
      action='store_const',
      dest='mode',
      const='xml')
  xml_group.add_argument(
      '--xpath',
      dest='xpath_selector',
      metavar='EXPRESSION',
      help='select event elements from the input XML document according to ' +
           'the given XPath expression')
  xml_group.add_argument(
      '--css',
      dest='css_selector',
      metavar='SELECTOR',
      help='select event elements from the input XML document according to ' +
           'the given CSS selector')

  csv_group = parser.add_argument_group('CSV input arguments')
  csv_group.add_argument(
      '--csv',
      help='parse the input file as a CSV document',
      action='store_const',
      dest='mode',
      const='csv')

  mapping_group = parser.add_argument_group('attribute mapping arguments', """\
These options control how event attributes will be mapped to XES attributes.
FORMAT-VALUE can contain Python input specifiers that refer to named event
attributes.""")
  mapping_group.add_argument(
      '--mapping',
      metavar=('XES-NAME', 'FORMAT-VALUE'),
      nargs=2,
      action='append',
      help='define a mapping from event attributes to XES attributes')
  mapping_group.add_argument(
      '--trace',
      metavar='FORMAT-VALUE',
      action='append',
      help='define a mapping from event attributes to XES trace names; each ' +
           'event will end up in precisely one trace')
  mapping_group.add_argument(
      '--preserve',
      action='store_true',
      help='preserve all event attributes verbatim in the output, not just ' +
           'the mapped ones')
  args = parser.parse_args()
  if args.trace:
    args.trace.reverse()
  else:
    args.trace = []
  args.trace.append("")

  mappings = {}
  for k, v in args.mapping:
    k = k.split(":", 2)
    if len(k) == 1:
      prefix = None
      name = k[0]
    else:
      prefix, name = k
    mappings[(prefix, name)] = v

  if args.mode == 'xml':
    if args.xpath_selector and args.css_selector:
      pass
    elif args.xpath_selector:
      selector = XPath(args.xpath_selector)
    elif args.css_selector:
      selector = CSSSelector(args.css_selector)
    else:
      assert False
    entries = xml_handler(args.infile, selector)
  elif args.mode == 'csv':
    entries = csv_handler(args.infile, delimiter=";")
  else:
    assert False

  traces = {}
  for e in entries:
    for t in args.trace:
      try:
        possible_name = t % e
        if not possible_name in traces:
          traces[possible_name] = []
        traces[possible_name].append(e)
        break
      except KeyError:
        pass

  root = etree.Element("log")

  used_prefixes = set()
  for prefix, _ in mappings:
    if not prefix or prefix in used_prefixes:
      continue
    root.append(get_extension_element(prefix))
    used_prefixes.add(prefix)
  if not "concept" in used_prefixes:
    root.append(get_extension_element("concept"))

  for t in traces:
    trace = etree.Element("trace")
    trace.append(etree.Element("string", key="concept:name", value=t))
    if traces[t]:
      for d in traces[t]:
        trace.append(dict_to_element(d, mappings, args.preserve))
      root.append(trace)

  args.outfile.write(etree.tostring(root,
      pretty_print=True,
      encoding="utf-8",
      xml_declaration=True))
