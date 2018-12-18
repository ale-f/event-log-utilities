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

## Examples

### Loading a CSV file

Here's a log for an average day at work, reduced to some core activities:

```
Project,Timestamp,Person,Activity,Location
1,2018-12-11 06:15,Alec,WakeUp,Home
1,2018-12-11 07:45,Alec,Leave,Home
1,2018-12-11 08:15,Alec,Arrive,Work
1,2018-12-11 08:25,Alec,DrinkTea,Work
1,2018-12-11 08:30,Alec,Meeting,Work
1,2018-12-11 09:30,Alec,Meeting,Work
1,2018-12-11 11:45,Alec,Lunch,Work
1,2018-12-11 12:30,Alec,DrinkTea,Work
1,2018-12-11 16:30,Alec,Leave,Work
1,2018-12-11 17:00,Alec,Arrive,Home
```

(I'll assume throughout the rest of these examples that you've saved this log
to `workday.csv`.)

If you really don't want _anything_ fancy to happen to the event log -- if you
just want to convert it into an XES trace -- then this will almost do what you
want:

```
$ something-to-xes.py --csv workday.csv
```

When I say "almost", that's because no mappings from CSV fields to XES ones
have been defined, so the effect of this is to produce a XES log (good!),
containing a XES trace (good!), containing... eleven empty events:

```
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <trace>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
    <event/>
  </trace>
</log>
Writing XML document... done.
```

That's... _technically_ a XES representation of our input, but it's perhaps not
a very useful one. If we add the `--preserve` option, things will improve:

```
$ something-to-xes.py --csv workday.csv --preserve
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <trace>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 06:15"/>
      <string key="Activity" value="WakeUp"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 07:45"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:15"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:25"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 09:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 11:45"/>
      <string key="Activity" value="Lunch"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 12:30"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 16:30"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 17:00"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

### Event attribute mappings (and standard XES attributes)

Our XES log is looking pretty good, but there's a problem: how should people
interpret this log? Why, for example, should someone assume that the `Person`
field is a string that identifies an employee? (In a web services log, say, a
field called `Person` might be a boolean that indicates whether a call was made
by an API or not.)

Luckily, the [XES specification](http://www.xes-standard.org/_media/xes/xesstandarddefinition-2.0.pdf)
has thought of this, and defines some standard property names with a meaning
that everyone in the XES ecosystem has agreed on. For example, a `Person` in
our log is an individual in an institutional hierarchy, which is what XES calls
an `org:resource`.

To connect `Person` to `org:resource`, we need to define a _mapping_. This is
a matter of adding the `--event-attr` command-line option:

```
$ something-to-xes.py --csv workday.csv --preserve \
    --event-attr org:resource "%(Person)s"
```

(Implementation note: events in the input log are converted to Python
dictionaries, and attribute mapping values are Python format strings. The
executive summary of this is that `%(ATTRIBUTE_NAME)s` in a mapping value will
be replaced with the value of the event property `ATTRIBUTE_NAME`.)

```
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <trace>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 06:15"/>
      <string key="Activity" value="WakeUp"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 07:45"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:15"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:25"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 09:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 11:45"/>
      <string key="Activity" value="Lunch"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 12:30"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 16:30"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <string key="org:resource" value="Alec"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 17:00"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

This is much better: now any XES tool knows that every event in this log was
performed by an individual in an institutional hierarchy whose name is `Alec`.
(The log now also declares that it uses the `org` extension; the script will do
this automatically for all of the standard extensions.)

There are other standard names we might want to use here. An event's
`concept:name` is the name of an activity (corresponding to our `Activity`),
while `time:timestamp` is, well, a timestamp. Let's add those two in as well:

```
$ something-to-xes.py --csv workday.csv --preserve \
    --event-attr org:resource "%(Person)s" \
    --event-attr concept:name "%(Activity)s" \
    --event-attr time:timestamp "%(Timestamp)s"
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Time" prefix="time" uri="http://www.xes-standard.org/time.xesext"/>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
  <trace>
    <event>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="WakeUp"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 06:15"/>
      <string key="Activity" value="WakeUp"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 07:45"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:15"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:25"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 08:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 09:30"/>
      <string key="Activity" value="Meeting"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Lunch"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 11:45"/>
      <string key="Activity" value="Lunch"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 12:30"/>
      <string key="Activity" value="DrinkTea"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 16:30"/>
      <string key="Activity" value="Leave"/>
      <string key="Location" value="Work"/>
      <string key="Person" value="Alec"/>
    </event>
    <event>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
      <!-- Raw event attributes follow: -->
      <string key="Project" value="1"/>
      <string key="Timestamp" value="2018-12-11 17:00"/>
      <string key="Activity" value="Arrive"/>
      <string key="Location" value="Home"/>
      <string key="Person" value="Alec"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

Note that `time:timestamp` is a _typed_ attribute, not merely a `string`, and
that the values associated with it have been converted into the standard
datetime format used by the XES standard. (This is done with the help of
[`dateutil.parser`](https://dateutil.readthedocs.io/en/stable/parser.html), so
the script will happily consume and convert more or less any date format.)

Although there's no standard name for `Location`, we may as well define an
explicit mapping for it so that we can stop using `--preserve`:

```
$ something-to-xes.py --csv workday.csv \
    --event-attr org:resource "%(Person)s" \
    --event-attr concept:name "%(Activity)s" \
    --event-attr time:timestamp "%(Timestamp)s" \
    --event-attr where "%(Location)s"
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Time" prefix="time" uri="http://www.xes-standard.org/time.xesext"/>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
  <trace>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

### Trace attributes

This looks much tidier now, but we left `Project` behind when we got rid of
`--preserve`! We should do something about that.

`Project` is a bit of a special case, though: it's the same for everything in
the trace. We might even want to use it as the trace identifier: one trace per
project per log.

Trace identifiers also have a standard name (and it's _also_ `concept:name`),
so we can do this easily enough with the help of the `--trace-attr`
command-line option:

```
$ something-to-xes.py --csv workday.csv \
    --event-attr org:resource "%(Person)s" \
    --event-attr concept:name "%(Activity)s" \
    --event-attr time:timestamp "%(Timestamp)s" \
    --event-attr where "%(Location)s" \
    --trace-attr concept:name "%(Project)s"
```

`--trace-attr` works in exactly the same way that `--event-attr` does, except
that the things selected as trace attributes are attached to traces rather than
to events:

```
Loaded events: 10, spread across 1 traces.
Processed traces: 1/1 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Time" prefix="time" uri="http://www.xes-standard.org/time.xesext"/>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
  <trace>
    <string key="concept:name" value="1"/>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

The script actually _itself_ takes advantage of `concept:name` by using it to
group events together into different traces. To see what that looks like, let's
add another trace to the log, with different activities carried out by a
different ~~person~~individual in an institutional hierarchy as part of a
different project. Update `workday.csv` so that it looks like this:

```
Project,Timestamp,Person,Activity,Location
1,2018-12-11 06:15,Alec,WakeUp,Home
1,2018-12-11 07:45,Alec,Leave,Home
1,2018-12-11 08:15,Alec,Arrive,Work
1,2018-12-11 08:25,Alec,DrinkTea,Work
1,2018-12-11 08:30,Alec,Meeting,Work
1,2018-12-11 09:30,Alec,Meeting,Work
1,2018-12-11 11:45,Alec,Lunch,Work
1,2018-12-11 12:30,Alec,DrinkTea,Work
1,2018-12-11 16:30,Alec,Leave,Work
1,2018-12-11 17:00,Alec,Arrive,Home
2,2018-12-11 06:15,Jens,WakeUp,Home
2,2018-12-11 07:45,Jens,Leave,Home
2,2018-12-11 08:15,Jens,Arrive,Work
2,2018-12-11 08:25,Jens,DrinkCoffee,Work
2,2018-12-11 08:30,Jens,Meeting,Work
2,2018-12-11 09:30,Jens,Meeting,Work
2,2018-12-11 11:45,Jens,Lunch,Work
2,2018-12-11 12:30,Jens,DrinkCoffee,Work
2,2018-12-11 16:30,Jens,Leave,Work
2,2018-12-11 17:00,Jens,Arrive,Home
```

`Jens` is very like `Alec`, except that he works on project `2` and performs
the `DrinkCoffee` activity instead of `DrinkTea`. What does the log look like
now?

```
$ something-to-xes.py --csv workday.csv \
    --event-attr org:resource "%(Person)s" \
    --event-attr concept:name "%(Activity)s" \
    --event-attr time:timestamp "%(Timestamp)s" \
    --event-attr where "%(Location)s" \
    --trace-attr concept:name "%(Project)s"
Loaded events: 20, spread across 2 traces.
Processed traces: 2/2 (100%).        
```

(We can already see that the log's events have now been divided up into two
traces.)

```
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Time" prefix="time" uri="http://www.xes-standard.org/time.xesext"/>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
  <trace>
    <string key="concept:name" value="1"/>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Alec"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="2"/>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="DrinkCoffee"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="DrinkCoffee"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Jens"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

These are the basic principles: by dividing the input into event attributes and
trace attributes, the script will make a structured log out of arbitrary input.

### Crazier features

#### Pseudonymisation

Our nice new log gives away a little too much information, though. `Jens` is a
fairly common name in Denmark, but `Alec` isn't -- if we released the log in
this state, people might be able to guess what institution this log was taken
from.

To get around problems like this, the script has _some_ support for
pseudonymising input data. Here, we'll use the `--pseudonymise-name` option,
which maps input fields that contain names into input fields that contain
_Danish_ names:

```
$ something-to-xes.py --csv workday.csv \
    --event-attr org:resource "%(Person)s" \
    --event-attr concept:name "%(Activity)s" \
    --event-attr time:timestamp "%(Timestamp)s" \
    --event-attr where "%(Location)s" \
    --trace-attr concept:name "%(Project)s" \
    --pseudonymise-name Person
```

Note that this option takes the name of an input field and _not_ a Python
format string -- this is because the input is pseudonymised immediately after
it's loaded and not just when it's used. (As a consequence, if we had used
`--preserve` here, the "raw" field values would also have been pseudonymised.)

```
Loaded events: 20, spread across 2 traces.
Processed traces: 2/2 (100%).          
Writing XML document... <?xml version='1.0' encoding='UTF-8'?>
<log>
  <extension name="Time" prefix="time" uri="http://www.xes-standard.org/time.xesext"/>
  <extension name="Organizational" prefix="org" uri="http://www.xes-standard.org/org.xesext"/>
  <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
  <trace>
    <string key="concept:name" value="1"/>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="DrinkTea"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Michael Kim Christiansen"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="2"/>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T06:15:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="WakeUp"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T07:45:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:15:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Arrive"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:25:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="DrinkCoffee"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T08:30:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T09:30:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Meeting"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T11:45:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Lunch"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T12:30:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="DrinkCoffee"/>
    </event>
    <event>
      <string key="where" value="Work"/>
      <date key="time:timestamp" value="2018-12-11T16:30:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Leave"/>
    </event>
    <event>
      <string key="where" value="Home"/>
      <date key="time:timestamp" value="2018-12-11T17:00:00.000Z"/>
      <string key="org:resource" value="Hans Kim Jørgensen"/>
      <string key="concept:name" value="Arrive"/>
    </event>
  </trace>
</log>
Writing XML document... done.
```

Pseudonymous names are drawn from a pool of vaguely plausible-sounding Danish
names (although it is worth noting that, in real life, not _everyone_ in
Denmark has the middle name `Kim`), so now `Alec`'s identity is safe.

**To quote the built-in documentation for a moment: `(This feature is NOT a
good substitute for a proper sensitive data handling policy.)` And it isn't.
Take care when working with personal data -- it's not just a good idea,
[it's the law](https://en.wikipedia.org/wiki/General_Data_Protection_Regulation)!**
