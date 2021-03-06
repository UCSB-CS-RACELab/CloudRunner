# -*- coding: utf-8 -*-
"""
    celery.utils.debug
    ~~~~~~~~~~~~~~~~~~

    Utilities for debugging memory usage.

"""
from __future__ import absolute_import, print_function

import os

from contextlib import contextmanager
from functools import partial

from celery.five import format_d, range
from celery.platforms import signals

try:
    from psutil import Process
except ImportError:
    Process = None  # noqa

_process = None
_mem_sample = []


def _on_blocking(signum, frame):
    import inspect
    raise RuntimeError(
        'Blocking detection timed-out at: %s' % (
            inspect.getframeinfo(frame), ))


@contextmanager
def blockdetection(timeout):
    if not timeout:
        yield
    else:
        old_handler = signals['ALRM']
        old_handler = None if old_handler == _on_blocking else old_handler

        signals['ALRM'] = _on_blocking

        try:
            yield signals.arm_alarm(timeout)
        finally:
            if old_handler:
                signals['ALRM'] = old_handler
            signals.reset_alarm()


def sample_mem():
    """Sample RSS memory usage.

    Statistics can then be output by calling :func:`memdump`.

    """
    current_rss = mem_rss()
    _mem_sample.append(current_rss)
    return current_rss


def _memdump(samples=10):
    S = _mem_sample
    prev = list(S) if len(S) <= samples else sample(S, samples)
    _mem_sample[:] = []
    import gc
    gc.collect()
    after_collect = mem_rss()
    return prev, after_collect


def memdump(samples=10, file=None):
    """Dump memory statistics.

    Will print a sample of all RSS memory samples added by
    calling :func:`sample_mem`, and in addition print
    used RSS memory after :func:`gc.collect`.

    """
    say = partial(print, file=file)
    if ps() is None:
        say('- rss: (psutil not installed).')
        return
    prev, after_collect = _memdump(samples)
    if prev:
        say('- rss (sample):')
        for mem in prev:
            say('-    > {0},'.format(mem))
    say('- rss (end): {0}.'.format(after_collect))


def sample(x, n, k=0):
    """Given a list `x` a sample of length ``n`` of that list is returned.

    E.g. if `n` is 10, and `x` has 100 items, a list of every 10th
    item is returned.

    ``k`` can be used as offset.

    """
    j = len(x) // n
    for _ in range(n):
        yield x[k]
        k += j


def humanbytes(s):
    return '{0}MB'.format(format_d(s // 1024))


def mem_rss():
    """Returns RSS memory usage as a humanized string."""
    p = ps()
    if p is not None:
        return humanbytes(p.get_memory_info().rss)


def ps():
    """Returns the global :class:`psutil.Process` instance,
    or :const:`None` if :mod:`psutil` is not installed."""
    global _process
    if _process is None and Process is not None:
        _process = Process(os.getpid())
    return _process
