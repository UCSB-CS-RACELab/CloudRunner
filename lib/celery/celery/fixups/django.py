from __future__ import absolute_import

import os
import sys
import warnings

from datetime import datetime

from celery import signals
from celery.exceptions import FixupWarning

SETTINGS_MODULE = os.environ.get('DJANGO_SETTINGS_MODULE')
ERR_NOT_INSTALLED = """\
Environment variable DJANGO_SETTINGS_MODULE is defined
but Django is not installed.  Will not apply Django fixups!
"""


def _maybe_close_fd(fh):
    try:
        os.close(fh.fileno())
    except (AttributeError, OSError, TypeError):
        # TypeError added for celery#962
        pass


def fixup(app):
    if SETTINGS_MODULE:
        try:
            import django  # noqa
        except ImportError:
            warnings.warn(FixupWarning(ERR_NOT_INSTALLED))
        return DjangoFixup(app).install()


class DjangoFixup(object):
    _db_recycles = 0

    def __init__(self, app):
        from django import db
        from django.core import cache
        from django.conf import settings
        from django.core.mail import mail_admins

        # Current time and date
        try:
            from django.utils.timezone import now
        except ImportError:  # pre django-1.4
            now = datetime.now  # noqa

        # Database-related exceptions.
        from django.db import DatabaseError
        try:
            import MySQLdb as mysql
            _my_database_errors = (mysql.DatabaseError,
                                   mysql.InterfaceError,
                                   mysql.OperationalError)
        except ImportError:
            _my_database_errors = ()      # noqa
        try:
            import psycopg2 as pg
            _pg_database_errors = (pg.DatabaseError,
                                   pg.InterfaceError,
                                   pg.OperationalError)
        except ImportError:
            _pg_database_errors = ()      # noqa
        try:
            import sqlite3
            _lite_database_errors = (sqlite3.DatabaseError,
                                     sqlite3.InterfaceError,
                                     sqlite3.OperationalError)
        except ImportError:
            _lite_database_errors = ()    # noqa
        try:
            import cx_Oracle as oracle
            _oracle_database_errors = (oracle.DatabaseError,
                                       oracle.InterfaceError,
                                       oracle.OperationalError)
        except ImportError:
            _oracle_database_errors = ()  # noqa

        self.app = app
        self.db_reuse_max = self.app.conf.get('CELERY_DB_REUSE_MAX', None)
        self._cache = cache
        self._settings = settings
        self._db = db
        self._mail_admins = mail_admins
        self._now = now
        self.database_errors = (
            (DatabaseError, ) +
            _my_database_errors +
            _pg_database_errors +
            _lite_database_errors +
            _oracle_database_errors,
        )

    def install(self):
        # Need to add project directory to path
        sys.path.append(os.getcwd())
        signals.beat_embedded_init.connect(self.close_database)
        signals.worker_ready.connect(self.on_worker_ready)
        signals.task_prerun.connect(self.on_task_prerun)
        signals.task_postrun.connect(self.on_task_postrun)
        signals.worker_init.connect(self.on_worker_init)
        signals.worker_process_init.connect(self.on_worker_process_init)

        self.app.loader.now = self.now
        self.app.loader.mail_admins = self.mail_admins

        return self

    def now(self, utc=False):
        return datetime.utcnow() if utc else self._now()

    def mail_admins(self, subject, body, fail_silently=False, **kwargs):
        return self._mail_admins(subject, body, fail_silently=fail_silently)

    def on_worker_init(self, **kwargs):
        """Called when the worker starts.

        Automatically discovers any ``tasks.py`` files in the applications
        listed in ``INSTALLED_APPS``.

        """
        self.close_database()
        self.close_cache()

    def on_worker_process_init(self, **kwargs):
        # the parent process may have established these,
        # so need to close them.

        # calling db.close() on some DB connections will cause
        # the inherited DB conn to also get broken in the parent
        # process so we need to remove it without triggering any
        # network IO that close() might cause.
        try:
            for c in self._db.connections.all():
                if c and c.connection:
                    _maybe_close_fd(c.connection)
        except AttributeError:
            if self._db.connection and self._db.connection.connection:
                _maybe_close_fd(self._db.connection.connection)

        # use the _ version to avoid DB_REUSE preventing the conn.close() call
        self._close_database()
        self.close_cache()

    def on_task_prerun(self, sender, **kwargs):
        """Called before every task."""
        if not getattr(sender.request, 'is_eager', False):
            self.close_database()

    def on_task_postrun(self, **kwargs):
        """Does everything necessary for Django to work in a long-living,
        multiprocessing environment.

        """
        # See http://groups.google.com/group/django-users/
        #            browse_thread/thread/78200863d0c07c6d/
        self.close_database()
        self.close_cache()

    def close_database(self, **kwargs):
        if not self.db_reuse_max:
            return self._close_database()
        if self._db_recycles >= self.db_reuse_max * 2:
            self._db_recycles = 0
            self._close_database()
        self._db_recycles += 1

    def _close_database(self):
        try:
            funs = [conn.close for conn in self._db.connections]
        except AttributeError:
            funs = [self._db.close_connection]  # pre multidb

        for close in funs:
            try:
                close()
            except self.database_errors as exc:
                str_exc = str(exc)
                if 'closed' not in str_exc and 'not connected' not in str_exc:
                    raise

    def close_cache(self):
        try:
            self._cache.cache.close()
        except (TypeError, AttributeError):
            pass

    def on_worker_ready(self, **kwargs):
        if self._settings.DEBUG:
            warnings.warn('Using settings.DEBUG leads to a memory leak, never '
                          'use this setting in production environments!')
