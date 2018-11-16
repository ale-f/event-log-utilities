#!/usr/bin/env python
# encoding: utf-8

# something-to-xes.py
# Copyright © 2017, 2018 Alexander Faithfull

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
from copy import copy as shallow_copy
import gzip
from lxml import etree
from lxml.etree import XPath
from lxml.cssselect import CSSSelector
from uuid import UUID
import random
import argparse
import dateutil.parser

prog_name = os.path.basename(sys.argv[0])

def rigged_shuffle(l, seed=2300):
  r = random.Random()
  r.seed(seed)
  r.shuffle(l)

# All of these lists are, according to Danmarks Statistik, the biggest (most
# popular, ...) in Denmark as of the beginning of 2018
first_names_f = [u"Anne", u"Kirsten", u"Mette", u"Hanne", u"Anna", u"Helle",
               u"Susanne", u"Lene", u"Maria", u"Marianne", u"Lone", u"Camilla",
               u"Inge", u"Pia", u"Karen", u"Bente", u"Louise", u"Charlotte",
               u"Jette", u"Tina"]
first_names_m = [u"Peter", u"Jens", u"Michael", u"Lars", u"Henrik", u"Thomas",
                 u"Søren", u"Jan", u"Christian", u"Martin", u"Niels",
                 u"Anders", u"Morten", u"Jesper", u"Jørgen", u"Hans", u"Mads",
                 u"Per", u"Ole", u"Rasmus"]
first_names = first_names_f + first_names_m
last_names = [u"Nielsen", u"Jensen", u"Hansen", u"Pedersen", u"Andersen",
              u"Christensen", u"Larsen", u"Sørensen", u"Rasmussen",
              u"Jørgensen", u"Petersen", u"Madsen", u"Kristensen", u"Olsen",
              u"Thomsen", u"Christiansen", u"Poulsen", u"Johansen", u"Møller",
              u"Mortensen"]
places = [u"København", u"Aarhus", u"Aalborg", u"Odense", u"Esbjerg",
          u"Vejle", u"Frederiksberg", u"Randers", u"Viborg", u"Kolding",
          u"Silkeborg", u"Horsens", u"Herning", u"Roskilde", u"Næstved",
          u"Slagelse", u"Gentofte", u"Sønderborg", u"Holbæk", u"Gladsaxe",
          u"Hjørring", u"Helsingør", u"Guldborgsund", u"Skanderborg", u"Køge",
          u"Frederikshavn", u"Aabenraa", u"Svendborg", u"Holstebro",
          u"Ringkøbing-Skjern", u"Rudersdal", u"Haderslev", u"Lyngby-Taarbæk",
          u"Hvidovre", u"Faaborg-Midtfyn", u"Fredericia", u"Hillerød",
          u"Høje-Taastrup", u"Varde", u"Greve"]

all_names = [f + u" Kim " + l for f in first_names for l in last_names]
rigged_shuffle(places)
rigged_shuffle(all_names)

def _yield_pseudorandom_uuid(seed=2300):
  r = random.Random()
  r.seed(seed)
  while True:
    yield str(UUID(int=r.getrandbits(128)))

pseudo_pools = {
  "name": {
    "len": len(all_names),
    "example": "Michael Kim Christiansen",
    "iter": iter(all_names)
  },
  "place": {
    "len": len(places),
    "example": "Kolding",
    "iter": iter(places)
  },
  "uuid": {
    "len": float("inf"),
    "example": "50484c7b-4d18-5c1f-6e2c-53cd782a6b63",
    "iter": _yield_pseudorandom_uuid()
  }
}
pseudo_mappings = {a: {} for a in pseudo_pools}

def pseudonymise(kind, n):
  global pseudo_pools, pseudo_mappings
  assert kind in pseudo_pools, """\
no pseudonym pool available for items of type '%s'""" % kind
  if not n in pseudo_mappings[kind]:
    try:
      pseudo_mappings[kind][n] = next(pseudo_pools[kind]["iter"])
    except StopIteration:
      raise Exception("""\
pseudonym pool '%s' is empty""" % kind)
  return pseudo_mappings[kind][n]

def warn(msg):
  sys.stderr.write("%s: warning: %s\n" % (prog_name, msg))

def error(msg, usage=False):
  sys.stderr.write("%s: error: %s\n" % (prog_name, msg))
  if usage:
    sys.stderr.write("Try '%s --help' for more information.\n" % prog_name)
  exit(1)

def progress(msg):
  sys.stderr.write("\r%s" % msg)

def xml_handler(f, prefix, selector):
  tree = etree.parse(f)
  for e in selector(tree):
    result = {}
    for name, value in e.items():
      result[prefix + "." + name] = value
    for child in e:
      result[prefix + child.tag] = child.text
      for name, value in child.items():
        result[prefix + child.tag + "." + name] = value
    yield result

def csv_handler(f, prefix, encoding, **fmtparams):
  def tidy(s):
    return unicode(s, encoding, errors='strict') if s else None
  reader = csv.reader(f, **fmtparams)
  names = map(lambda t: tidy(prefix + t), next(reader))
  for row in reader:
    yield dict(filter(lambda a: a[1], zip(names, map(tidy, row))))

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

def string_element(key, v):
  return etree.Element(
      "string",
      key=key,
      value=v if v else "")

def date_element(key, v):
  return etree.Element(
      "date",
      key=key,
      value=xesformat(dateutil.parser.parse(v)))

def int_element(key, v):
  return etree.Element(
      "int",
      key=key,
      value=str(int(v)))

def float_element(key, v):
  return etree.Element(
      "float",
      key=key,
      value=str(float(v)))

def boolean_element(key, v):
  value = "false"
  v = v.strip().lower()
  if v == "true" or v == "1" or v == "yes":
    value = "true"
  return etree.Element(
      "boolean",
      key=key,
      value=value)

def id_element(key, v):
  return etree.Element(
      "id",
      key=key,
      value=v)

def uuid_element(key, v):
  return id_element(key, str(UUID(v)))

elementary_attribute_types = {
  "string": string_element,
  "date": date_element,
  "int": int_element,
  "float": float_element,
  "boolean": boolean_element,
  "id": id_element,

  # Types with a leading underscore are for internal use and do not appear in
  # the help text's list of elementary types
  "_uuid": uuid_element
}

typed_attributes = {
  ("concept", "name"): "string",
  ("concept", "event"): "string",

  ("lifecycle", "model"): "string",
  ("lifecycle", "transition"): "string",

  ("org", "resource"): "string",
  ("org", "role"): "string",
  ("org", "group"): "string",

  ("time", "timestamp"): "date",

  ("semantic", "modelReference"): "string",

  # Attributes of type "id" are not required by the XES specification to be
  # UUIDs, but the "id" attribute from the identity extension explicitly does
  # require this. A secret extra elementary attribute type takes care of
  # enforcing this constraint
  ("id", "id"): "_uuid",

  ("cost", "total"): "float",
  ("cost", "currency"): "string"
  # The cost extension's meta-attributes are not supported, because
  # meta-attributes in general are not supported
}

def make_element(name, value):
  element_type = "string"
  if name in typed_attributes:
    element_type = typed_attributes[name]
  return elementary_attribute_types[element_type](
      name_to_raw_name(name), value)

def name_to_raw_name(n):
  p, r = n
  if p:
    return "%s:%s" % (p, r)
  else:
    return r

def raw_name_to_name(n):
  parts = n.split(":", 2)
  if len(parts) == 1:
    return (None, parts[0])
  else:
    return (parts[0], parts[1])

def dict_to_element(d, mappings, preserve=False):
  el = etree.Element("event")
  for (name, value) in mappings.items():
    try:
      actual = value % d
      el.append(make_element(name, actual))
    except KeyError:
      pass
    except ValueError:
      pass
  if preserve:
    el.append(etree.Comment(" Raw event attributes follow: "))
    for name, value in d.items():
      el.append(string_element(name, value))
  return el

extensions = {
  "concept": ("Concept", "http://www.xes-standard.org/concept.xesext"),
  "lifecycle": ("Lifecycle", "http://www.xes-standard.org/lifecycle.xesext"),
  "org": ("Organizational", "http://www.xes-standard.org/org.xesext"),
  "time": ("Time", "http://www.xes-standard.org/time.xesext"),
  "semantic": ("Semantic", "http://www.xes-standard.org/semantic.xesext"),
  "id": ("ID", "http://www.xes-standard.org/identity.xesext"),
  "cost": ("Cost", "http://www.xes-standard.org/cost.xesext")
}

def get_extension_element(prefix):
  assert prefix in extensions, """\
prefix "%s" does not specify a known XES extension (see the --xes-extension \
argument)""" % prefix
  name, uri = extensions[prefix]
  return etree.Element("extension", name=name, prefix=prefix, uri=uri)

def file_handle(a, mode='r'):
  if a.endswith(".gz"):
    return gzip.open(a, mode)
  else:
    return open(a, mode)

class ExtendAction(argparse.Action):
  def __init__(self, option_strings, dest, nargs=None,
      default=None, type=None, help=None, metavar=None):
    if nargs == 0:
      raise ValueError
    super(ExtendAction, self).__init__(
        option_strings=option_strings,
        dest=dest,
        nargs=nargs,
        default=default,
        type=type,
        help=help,
        metavar=metavar)

  def __call__(self, parser, namespace, values, option_string=None):
    items = shallow_copy(getattr(namespace, self.dest, []))
    if not items:
      items = []
    items.extend(values)
    setattr(namespace, self.dest, items)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="""\
Convert one or more XML- or CSV-format flat event logs to an XES document
containing structured traces, transforming event attributes into XES attributes
in the process.""")
  parser.add_argument(
      '--quiet',
      help='don\'t write progress information to standard error',
      action='store_false',
      dest='chatty')
  parser.add_argument(
      '--dump-events',
      help='print all the loaded events and exit immediately',
      action='store_true',
      dest='dump_events')

  io_group = parser.add_argument_group('input and output selection', """\
These arguments specify the types and locations of input files and the location
of the output file. Filenames can end with '.gz' for transparent decompression
or compression.""")
  io_group.add_argument(
      '--xml',
      dest='in_xml',
      metavar='INFILE',
      help='load each %(metavar)s, or standard input if none were given, as ' +
           'a XML document',
      action=ExtendAction,
      nargs='*',
      type=lambda s: file_handle(s, "r"),
      default=None)
  io_group.add_argument(
      '--csv',
      dest='in_csv',
      metavar='INFILE',
      help='load each %(metavar)s, or standard input if none were given, as ' +
           'a CSV document',
      action=ExtendAction,
      nargs='*',
      type=lambda s: file_handle(s, "r"),
      default=None)
  io_group.add_argument(
      '-o', '--output',
      dest='outfile',
      metavar='OUTFILE',
      help='the output file (default: standard output)',
      type=lambda s: file_handle(s, "w"),
      default=sys.stdout)

  xml_group = parser.add_argument_group('XML input arguments', """\
These arguments specify how to select event elements from XML input files.
Precisely one of them must be specified.""")
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
These arguments specify the CSV dialect used by CSV input files; all are
optional. If neither --double-quote nor --escape is specified, quoted fields
may not contain quoted characters.""")
  csv_group.add_argument(
      '--delimiter',
      metavar='CHAR',
      help='%(metavar)s is the field delimiter; the special value \'\\t\' ' +
           'specifies a tab (default: \'%(default)s\')',
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

  ppr_group = parser.add_argument_group(
      'event attribute preprocessing arguments')
  ppr_group.add_argument(
      '--unify-attributes',
      dest='unify_attributes',
      help='share event attribute names across all input files (default)',
      action='store_true',
      default=True)
  ppr_group.add_argument(
      '--distinguish-attributes',
      dest='unify_attributes',
      help='rename event attributes to include the format and index of ' +
           'the input file they came from',
      action='store_false')

  pseudo_group = parser.add_argument_group('pseudonymisation arguments', """\
These arguments are used to pseudonymise event attribute values that contain
sensitive information by replacing them with values drawn from internal pools.
Pools are shared across attributes. (This feature is NOT a good substitute for
a proper sensitive data handling policy.)""")
  pseudo_group.add_argument(
      '--pseudonymise-name',
      metavar='ATTR',
      dest='pseudo_names',
      action='append',
      default=[],
      help='pseudonymise the event attribute %(metavar)s, which specifies a ' +
           'person\'s name (pool size: %g, example entry: "%s")' % \
           (pseudo_pools["name"]["len"], pseudo_pools["name"]["example"]))
  pseudo_group.add_argument(
      '--pseudonymise-place',
      metavar='ATTR',
      dest='pseudo_places',
      action='append',
      default=[],
      help='pseudonymise the event attribute %(metavar)s, which specifies a ' +
           'town or city (pool size: %g, example entry: "%s")' % \
           (pseudo_pools["place"]["len"], pseudo_pools["place"]["example"]))
  pseudo_group.add_argument(
      '--pseudonymise-uuid',
      metavar='ATTR',
      dest='pseudo_uuids',
      action='append',
      default=[],
      help='pseudonymise the event attribute %(metavar)s, which specifies a ' +
           'UUID (pool size: %g, example entry: "%s")' % \
           (pseudo_pools["uuid"]["len"], pseudo_pools["uuid"]["example"]))

  xes_group = parser.add_argument_group('XES control arguments', """\
These arguments add new XES extensions to the output document and specify the
types of output XES attributes. (The types of the attributes specified in the
standard extensions are already specified.)""")
  xes_group.add_argument(
      '--xes-extension',
      metavar=('PREFIX', 'NAME', 'URI'),
      nargs=3,
      action='append',
      dest='xes_extensions',
      default=[],
      help='add a new XES extension to the document (the specification of ' +
           'which will not be downloaded; attribute types must be declared ' +
           'explicitly)')
  xes_group.add_argument(
      '--type',
      metavar=('XES-NAME', 'TYPE'),
      nargs=2,
      action='append',
      dest='types',
      default=[],
      help='define the elementary type of an XES event attribute; ' +
           'attributes with no defined type will be treated as strings ' +
           '(supported types: %s)' % \
           ", ".join(filter(lambda a: not a.startswith("_"),
               elementary_attribute_types.keys())))

  mapping_group = parser.add_argument_group('attribute mapping arguments', """\
These arguments define the mapping from event attributes to XES attributes.
VALUE can contain Python format specifiers that refer to named event
attributes.""")
  mapping_group.add_argument(
      '--event-attr',
      metavar=('XES-NAME', 'VALUE'),
      nargs=2,
      action='append',
      dest='event_attrs',
      default=[],
      help='define a mapping from event attributes to XES event attributes')
  mapping_group.add_argument(
      '--trace-attr',
      metavar=('XES-NAME', 'VALUE'),
      nargs=2,
      action='append',
      dest='trace_attrs',
      default=[],
      help='define a mapping from event attributes to XES trace attributes; ' +
           'each event will end up in precisely one trace based on these ' +
           'mappings')
  mapping_group.add_argument(
      '--preserve',
      action='store_true',
      help='preserve all event attributes in the output, not just the ' +
           'mapped ones')

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

  if not args.chatty:
    progress = lambda s: None

  attributes_to_pseudonymise = \
      {name: pool for name, pool in \
          map(lambda name: (name, "name"), args.pseudo_names) +
          map(lambda name: (name, "place"), args.pseudo_places) +
          map(lambda name: (name, "uuid"), args.pseudo_uuids)}

  event_attribute_mappings = {}
  for k, v in args.event_attrs:
    event_attribute_mappings[raw_name_to_name(k)] = v

  trace_attribute_mappings = {}
  for k, v in args.trace_attrs:
    trace_attribute_mappings[raw_name_to_name(k)] = v

  for prefix, name, uri in args.xes_extensions:
    assert not prefix in extensions or extensions[prefix] == (name, uri), """\
cannot replace the prefix "%s", which is already associated with the "%s" \
extension (%s)""" % (prefix, extensions[prefix][0], extensions[prefix][1])
    if prefix in extensions:
      pass
    else:
      extensions[prefix] = (name, uri)

  for k, t in args.types:
    assert t in elementary_attribute_types, """\
"%s" does not identify an elementary attribute type""" % t
    name = raw_name_to_name(k)
    assert not name in typed_attributes or typed_attributes[name] == t, """\
cannot change the type of "%s" from %s to \
%s""" % (k, typed_attributes[name], t)
    if name in typed_attributes:
      pass
    else:
      typed_attributes[name] = t

  root_el = etree.Element("log")

  used_prefixes = set()
  for (prefix, _) in \
      event_attribute_mappings.keys() + trace_attribute_mappings.keys():
    if not prefix or prefix in used_prefixes:
      continue
    root_el.append(get_extension_element(prefix))
    used_prefixes.add(prefix)

  stdin_used = False
  event_iterators = []
  if args.in_xml != None:
    if args.xpath_selector:
      selector = XPath(args.xpath_selector)
    elif args.css_selector:
      selector = CSSSelector(args.css_selector)
    else:
      error("no selector specified; use either --xpath or --css", usage=True)
    if args.in_xml:
      print("Loading XML files: %s" % args.in_xml)
      for idx, inf in enumerate(args.in_xml):
        event_iterators.append(xml_handler(
            inf, "" if args.unify_attributes else ("xml%d." % idx), selector))
    else:
      stdin_used = True
      event_iterators.append(xml_handler(
          sys.stdin, "" if args.unify_attributes else "xml-.", selector))
  elif (args.xpath_selector or args.css_selector):
    warning("XML selectors were specified, but there were no XML input files")

  def _csv_handler(f, prefix):
    return csv_handler(f, prefix, args.encoding,
        delimiter=args.delimiter,
        quotechar=args.quote,
        doublequote=args.double_quote,
        escapechar=args.escape)
  if args.in_csv != None:
    if args.delimiter == '\\t':
      args.delimiter = '\t'
    if args.in_csv:
      for inf in args.in_csv:
        event_iterators.append(_csv_handler(
            inf, "" if args.unify_attributes else ("csv%d." % idx)))
    elif stdin_used:
      error("cannot load standard input as both XML and CSV", usage=True)
    else:
      stdin_used = True
      event_iterators.append(_csv_handler(
          sys.stdin, "" if args.unify_attributes else "csv-."))

  if not event_iterators:
    error("no input files were specified", usage=True)

  trace_names = [""]
  for name, value in trace_attribute_mappings.items():
    if name == ("concept", "name"):
      trace_names.insert(0, value)

  traces = {}
  traces_in_order = []
  count = 0
  for it in event_iterators:
    for e in it:
      if attributes_to_pseudonymise:
        for attr_name, attr_value in e.items():
          if attr_name in attributes_to_pseudonymise:
            e[attr_name] = pseudonymise(
                attributes_to_pseudonymise[attr_name], attr_value)
      if not args.dump_events:
        for t in trace_names:
          try:
            possible_name = t % e
            if not possible_name in traces:
              traces[possible_name] = []
              traces_in_order.append(possible_name)
            traces[possible_name].append(e)
            count += 1
            if count % 1000 == 0:
              progress("Loading events: %d..." % count)
            break
          except KeyError:
            pass
      else:
        for attr_name, attr_value in e.items():
          print("%s: %s" % (attr_name, attr_value))
        print("--")
  if args.dump_events:
    sys.exit(0)
  total_traces = len(traces)
  progress("Loaded events: %d, spread across %d traces.\n" % \
      (count, total_traces))

  if args.max_traces:
    progress("Pruning to at most %d traces.\n" % args.max_traces)
    traces = {ti: traces[ti] for ti in traces_in_order[:args.max_traces]}
    total_traces = len(traces)

  count = 0
  for trace in traces:
    trace_el = etree.Element("trace")
    trace_attributes = {}

    for event in traces[trace]:
      event_el = dict_to_element(
          event, event_attribute_mappings, args.preserve)
      for name, value in trace_attribute_mappings.items():
        try:
          actual = value % event
          if not name in trace_attributes:
            trace_attributes[name] = actual
          else:
            assert trace_attributes[name] == actual, """\
trace '%s': not all events have the same value for trace attribute '%s'""" % \
  (trace, name_to_raw_name(name))
        except KeyError:
          pass
      trace_el.append(event_el)

    pos = 0
    for name, actual in trace_attributes.items():
      try:
        trace_el.insert(pos, make_element(name, actual))
        pos += 1
      except ValueError:
        pass
    root_el.append(trace_el)

    count += 1
    if count % 1000 == 0:
      progress("Processing traces: %d/%d (%g%%)...        \b\b\b\b\b\b\b\b" % \
          (count, total_traces, (float(count) / total_traces) * 100))
  progress("Processed traces: %d/%d (100%%).          \n" % (count, total_traces))
  progress("Writing XML document... ")
  etree.ElementTree(root_el).write(args.outfile,
      pretty_print=True,
      encoding="utf-8",
      xml_declaration=True)
  progress("Writing XML document... done.\n")
