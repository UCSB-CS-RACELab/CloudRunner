"""
Originally taken from pyiso8601 (http://code.google.com/p/pyiso8601/)

Modified to match the behavior of dateutil.parser:

    - raise ValueError instead of ParseError
    - returns naive datetimes by default
    - uses pytz.FixedOffset

This is the original License:

Copyright (c) 2007 Michael Twomey

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
from __future__ import absolute_import

import re

from datetime import datetime
from pytz import FixedOffset

# Adapted from http://delete.me.uk/2005/03/iso8601.html
ISO8601_REGEX = re.compile(
    r'(?P<year>[0-9]{4})(-(?P<month>[0-9]{1,2})(-(?P<day>[0-9]{1,2})'
    r'((?P<separator>.)(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2})'
    '(:(?P<second>[0-9]{2})(\.(?P<fraction>[0-9]+))?)?'
    r'(?P<timezone>Z|(([-+])([0-9]{2}):([0-9]{2})))?)?)?)?'
)
TIMEZONE_REGEX = re.compile(
    '(?P<prefix>[+-])(?P<hours>[0-9]{2}).(?P<minutes>[0-9]{2})'
)


def parse_iso8601(datestring):
    """Parses ISO 8601 dates into datetime objects"""
    m = ISO8601_REGEX.match(datestring)
    if not m:
        raise ValueError('unable to parse date string %r' % datestring)
    groups = m.groupdict()
    tz = groups['timezone']
    if tz and tz != 'Z':
        m = TIMEZONE_REGEX.match(tz)
        prefix, hours, minutes = m.groups()
        hours, minutes = int(hours), int(minutes)
        if prefix == '-':
            hours = -hours
            minutes = -minutes
        tz = FixedOffset(minutes + hours * 60)
    frac = groups['fraction']
    groups['fraction'] = int(float('0.%s' % frac) * 1e6) if frac else 0
    return datetime(
        int(groups['year']), int(groups['month']), int(groups['day']),
        int(groups['hour']), int(groups['minute']), int(groups['second']),
        int(groups['fraction']), tz
    )
