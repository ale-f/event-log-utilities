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

import os
import csv
import sys
from lxml import etree
from lxml.etree import XPath
from lxml.cssselect import CSSSelector
import argparse
import dateutil.parser

prog_name = os.path.basename(sys.argv[0])

def error(msg, usage=False):
  sys.stderr.write("%s: error: %s\n" % (prog_name, msg))
  if usage:
    sys.stderr.write("Try '%s --help' for more information.\n" % prog_name)
  exit(1)

def xml_handler(f, selector):
  tree = etree.parse(f)
  for e in selector(tree):
    result = {}
    for child in e:
      result[child.tag] = child.text
      for name, value in child.items():
        result[child.tag + "." + name] = value
    yield result

def line_to_unicode(s, encoding, errors='strict'):
  return unicode(s, encoding, errors=errors)

def csv_handler(f, encoding, **fmtparams):
  reader = csv.reader(f, **fmtparams)
  names = map(lambda l: line_to_unicode(l, encoding), next(reader))
  for row in reader:
    yield dict(zip(names, map(lambda l: line_to_unicode(l, encoding), row)))

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

  mode_group_ = parser.add_argument_group('mode arguments', """\
These arguments specify the type of the input file. Precisely one of them must
be specified.""")
  mode_group = mode_group_.add_mutually_exclusive_group(required=True)
  mode_group.add_argument(
      '--xml',
      help='parse the input file as a XML document (requires either --xpath ' +
           'or --css)',
      action='store_const',
      dest='mode',
      const='xml')
  mode_group.add_argument(
      '--csv',
      help='parse the input file as a CSV document',
      action='store_const',
      dest='mode',
      const='csv')

  xml_group = parser.add_argument_group('XML input arguments', """\
These arguments specify how to select event elements from a XML input file.
Precisely one of them must be specified (when using --xml).""")
  selector_group = xml_group.add_mutually_exclusive_group(required=False)
  selector_group.add_argument(
      '--xpath',
      dest='xpath_selector',
      metavar='EXPRESSION',
      help='select event elements from the input XML document according to ' +
           'the given XPath expression')
  selector_group.add_argument(
      '--css',
      dest='css_selector',
      metavar='SELECTOR',
      help='select event elements from the input XML document according to ' +
           'the given CSS selector')

  csv_group = parser.add_argument_group('CSV input arguments', """\
These arguments specify the CSV dialect used by the input file; all are
optional. If neither --double-quote nor --escape is specified, quoted fields
may not contain quoted characters.""")
  csv_group.add_argument(
      '--delimiter',
      metavar='CHAR',
      help='%(metavar)s is the field delimiter (default: \'%(default)s\')',
      default=',')
  csv_group.add_argument(
      '--quote',
      metavar='CHAR',
      help='%(metavar)s introduces a quoted field (default: \'%(default)s\')',
      default='"')
  escape_group = csv_group.add_mutually_exclusive_group(required=False)
  escape_group.add_argument(
      '--double-quote',
      action='store_true',
      help='quote characters inside quotes are escaped by doubling')
  escape_group.add_argument(
      '--escape',
      metavar='CHAR',
      dest='escape',
      help='quote characters inside quotes are escaped by %(metavar)s')
  escape_group.add_argument(
      '--encoding',
      metavar='ENCODING',
      dest='encoding',
      help='the input text encoding is %(metavar)s (default: \'%(default)s\'',
      default='utf-8')

  mapping_group = parser.add_argument_group('attribute mapping arguments', """\
These arguments control how event attributes will be mapped to XES attributes.
The --mapping and --trace arguments may be given several times. VALUE can
contain Python format specifiers that refer to named event attributes.""")
  mapping_group.add_argument(
      '--mapping',
      metavar=('XES-NAME', 'VALUE'),
      nargs=2,
      action='append',
      help='define a mapping from event attributes to XES attributes')
  mapping_group.add_argument(
      '--trace',
      metavar='VALUE',
      action='append',
      help='define a mapping from event attributes to XES trace names; each ' +
           'event will end up in precisely one trace')
  mapping_group.add_argument(
      '--preserve',
      action='store_true',
      help='preserve all event attributes verbatim in the output, not just ' +
           'the mapped ones')

  output_group = parser.add_argument_group('output arguments', """\
These arguments control the generation of the final XES document.""")
  output_group.add_argument(
      '--max-traces',
      metavar='COUNT',
      action='store',
      type=int,
      default=None,
      help='output only the first %(metavar)s traces found in the input ' +
           'file (default: %(default)s)')
  args = parser.parse_args()

  mappings = {}
  if args.mapping:
    for k, v in args.mapping:
      k = k.split(":", 2)
      if len(k) == 1:
        prefix = None
        name = k[0]
      else:
        prefix, name = k
      mappings[(prefix, name)] = v

  if args.mode == 'xml':
    if args.xpath_selector:
      selector = XPath(args.xpath_selector)
    elif args.css_selector:
      selector = CSSSelector(args.css_selector)
    else:
      error("no selector specified; use either --xpath or --css", usage=True)
    entries = xml_handler(args.infile, selector)
  elif args.mode == 'csv':
    if args.xpath_selector or args.css_selector:
      error("XML selectors cannot be used with the --csv argument", usage=True)
    else:
      entries = csv_handler(args.infile, args.encoding,
          delimiter=args.delimiter,
          quotechar=args.quote,
          doublequote=args.double_quote,
          escapechar=args.escape)

  if args.trace:
    args.trace.reverse()
  else:
    args.trace = []
  args.trace.append("")
  traces = {}
  traces_in_order = []
  for e in entries:
    for t in args.trace:
      try:
        possible_name = t % e
        if not possible_name in traces:
          traces[possible_name] = []
          traces_in_order.append(possible_name)
        traces[possible_name].append(e)
        break
      except KeyError:
        pass

  if args.max_traces:
    traces = {ti: traces[ti] for ti in traces_in_order[:args.max_traces]}

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

  etree.ElementTree(root).write(args.outfile,
      pretty_print=True,
      encoding="utf-8",
      xml_declaration=True)
