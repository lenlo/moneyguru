# Created On: 2012/02/02
# Copyright 2015 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

"""API to create moneyGuru plugins.

This module was designed to allow developers to easily create plugins for moneyGuru. moneyGuru being
open source, we can already add anything anywhere, but the bar of entry for doing so can be high.

The goal here is to lower the bar of entry by having a simple API to do simple things. Many of the
classes below are either base classes or helper classes. If you want to develop a plugin, this is
the list of classes you can subclass:

* :class:`ReadOnlyTablePlugin`
* :class:`CurrencyProviderPlugin`
"""

import logging

from datetime import date


from collections import namedtuple

from core.model.currency import USD, EUR, CAD
from hscommon.notify import Broadcaster
from ..model.currency import Currency, CurrencyNotSupportedException
from ..gui.base import BaseView
from ..gui.table import GUITable, Row
from ..const import PaneType

class Plugin:
    """Base class for all plugins.

    By itself, it doesn't do much except offer common attributes to all plugins. Don't subclass
    this directly.
    """
    #: Display name of the plugin (for when we list plugins and stuff)
    NAME = ''
    #: Display name of the plugin basic type (import action, currency, etc.)
    TYPE_NAME = ''
    #: Author of the plugin
    AUTHOR = ''
    #: Determines the loading order of the plugins. Lower priorities are loaded first.
    PRIORITY = 0
    #: Whether this plugin is a View, and thus should be in the plugin section of the New View tab.
    IS_VIEW = False

    @classmethod
    def plugin_id(cls):
        return "{}.{}".format(cls.__module__, cls.__qualname__)

    @classmethod
    def is_core(cls):
        return cls.plugin_id().startswith('core.')


class ViewPlugin(Plugin):
    """Base class for viewable plugins.

    Once again, we don't subclass this directly. The way viewable plugin work is that the base
    system provides a couple of view "templates" to offer to the plugin developer, who is then able
    to fill the template with data within that template's bounds.

    This system is there to simplify the plugin developer's work, because otherwise he would have
    to manually code the Qt and Cocoa layers for each view plugin, which could get complicated.

    Subclasses :class:`.Plugin`.
    """
    IS_VIEW = True

    def __init__(self, mainwindow):
        #: The plugin's parent :class:`.MainWindow`.
        self.mainwindow = mainwindow
        #: The plugin's parent :class:`.Document`.
        self.document = mainwindow.document

class ReadOnlyTableRow(Row):
    """A :class:`.Row` with a simplified API for plugin developers."""
    def set_field(self, name, value, sort_value=None):
        """Set the value of an arbitrary field name in the row.

        :param str name: Name of the field to set.
        :param str value: Display value of the field.
        :param sort_value: Value to use for sorting.
        """
        setattr(self, name, value)
        if sort_value is not None:
            setattr(self, '_'+name, sort_value)


class ReadOnlyTable(GUITable):
    """A read-only table to be used in a :class:`.ViewPlugin`.

    It fetches its ``COLUMNS`` attribute (see :class:`.Columns`) directly from its parent plugin
    so that we don't have to subclass this table simply for defining columns.

    Subclasses :class:`.GUITable`.
    """
    def __init__(self, plugin):
        #: The parent plugin.
        self.plugin = plugin
        self.COLUMNS = plugin.COLUMNS
        GUITable.__init__(self, plugin.document)

    def _fill(self):
        self.plugin.fill_table()


class ReadOnlyTableView(BaseView):
    """View for :class:`.ReadOnlyTablePlugin`.

    A simple view containing a :class:`.ReadOnlyTable`, used by :class:`.ReadOnlyTablePlugin`.

    Subclasses :class:`.BaseView`.
    """
    VIEW_TYPE = PaneType.ReadOnlyTablePlugin

    def __init__(self, plugin):
        BaseView.__init__(self, plugin.mainwindow)
        self.plugin = plugin
        self.table = ReadOnlyTable(plugin)
        self.bind_messages(self.INVALIDATING_MESSAGES, self._revalidate)

    def _revalidate(self):
        self.table.refresh_and_show_selection()


class ReadOnlyTablePlugin(ViewPlugin):
    """A view plugin that contains a read-only table.

    To create a plugin from this, subclass it, fill :attr:`COLUMNS` and implement
    :meth:`fill_table`.

    Subclasses :class:`ViewPlugin`.
    """
    TYPE_NAME = "Display Table"
    #: List of columns to be displayed in our table. See :class:`Columns`.
    COLUMNS = []

    def __init__(self, mainwindow):
        ViewPlugin.__init__(self, mainwindow)
        #: Instance of :class:`ReadOnlyTableView`
        self.view = ReadOnlyTableView(self)
        #: Instance of :class:`ReadOnlyTable`
        self.table = self.view.table

    def add_row(self):
        """Add a row to our table and return it.

        :rtype: :class:`ReadOnlyTableRow`
        """
        row = ReadOnlyTableRow(self.table)
        self.table.append(row)
        return row

    def fill_table(self):
        """Fills our table with its intended contents.

        Subclass this to add content to your table. The principle is rather simple: Add your rows
        with :meth:`add_row` and call :meth:`ReadOnlyTableRow.set_field` to set the contents of each
        row.
        """
        raise NotImplementedError()

class CurrencyProviderPlugin(Plugin):
    """Plugin allowing the creation of new currencies and the fetching of their rates.

    By subclassing this plugin, you can add new currencies to moneyGuru and also add a new source
    to fetch those currencies' exchange rates.

    Subclasses :class:`Plugin`
    """
    TYPE_NAME = "Currency Provider"

    _registered_default_currencies = False

    def __init__(self):
        Plugin.__init__(self)
        self.supported_currency_codes = set()
        try:
            for code, name, exponent, fallback_rate in self.register_currencies():
                self.register_currency(code, name, exponent=exponent, latest_rate=fallback_rate)
        except TypeError: # We return None, which means we registered all currencies manually.
            pass
        Currency.sort_currencies()

    def wrapped_get_currency_rates(self, currency_code, start_date, end_date):
        """Tries to fetch exchange rates for ``currency_code``.

        If our currency is supported by our plugin, we first try the "complex" fetching
        (:meth:`get_currency_rates`). If it's not implemented, we try the "simple" one
        (:meth:`get_currency_rate_today`). We return the result of the first method to work.

        If we can't get results, either because our currency isn't supported or because our
        implementation is incomplete, :exc:`.CurrencyNotSupportedException` is raised.

        This method isn't designed to be overriden.
        """
        logging.debug("wrapped_get_currency_rates(%s, %s, %s) for %s",
                      currency_code, start_date, end_date, self)
        """
        if currency_code not in self.supported_currency_codes:
            raise CurrencyNotSupportedException()
        """
        try:
            return self.get_currency_rates(currency_code, start_date, end_date) or []
        except NotImplementedError:
            try:
                result = self.get_currency_rate_today(currency_code)
                if result is not None:
                    return [(date.today(), result)]
                else:
                    return []
            except NotImplementedError:
                raise CurrencyNotSupportedException()

    def register_currency(self, code, name, **kwargs):
        """Register a currency.

        Calling this gives more options than the simple return scheme of :meth:`register_currencies`.

        ``**kwargs`` is passed directly to :meth:`Currency.register`.

        Returns the resulting currency instance.
        """
        result = Currency.register(code, name, **kwargs)
        self.supported_currency_codes.add(code)
        return result

    def register_currencies(self):
        """Override this and return a list of new currencies to support.

        The expected return value is a list of tuples ``(code, name, exponent, fallback_rate)``.

        If you need to set more option, call :meth:`register_currency` instead.

        ``exponent`` is the number of decimal numbers that should be displayed when formatting
        amounts in this currency.

        ``fallback_rate`` is the rate to use in case we can't fetch a rate. You can use the rate
        that is in effect when you write the plugin. Of course, it will become wildly innaccurate
        over time, but it's still better than a rate of ``1``.
        """
        #raise NotImplementedError()

        # Only do this once
        if CurrencyProviderPlugin._registered_default_currencies:
            return

        self.supported_currency_codes |= {'USD', 'EUR'} # already added
        # In order we want to list them
        USD.priority = 1
        EUR.priority = 2
        self.register_currency(
            'GBP', 'U.K. pound sterling',
            start_date=date(1998, 1, 2), start_rate=2.3397, latest_rate=1.5349, priority=3)
        CAD.priority = 4
        self.register_currency(
            'AUD', 'Australian dollar',
            start_date=date(1998, 1, 2), start_rate=0.9267, latest_rate=0.9336, priority=5)
        self.register_currency(
            'JPY', 'Japanese yen',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.01076, latest_rate=0.01076, priority=6)
        self.register_currency(
            'INR', 'Indian rupee',
            start_date=date(1998, 1, 2), start_rate=0.03627, latest_rate=0.02273, priority=7)
        self.register_currency(
            'NZD', 'New Zealand dollar',
            start_date=date(1998, 1, 2), start_rate=0.8225, latest_rate=0.7257, priority=8)
        self.register_currency(
            'CHF', 'Swiss franc',
            start_date=date(1998, 1, 2), start_rate=0.9717, latest_rate=0.9273, priority=9)
        self.register_currency(
            'ZAR', 'South African rand',
            start_date=date(1998, 1, 2), start_rate=0.292, latest_rate=0.1353, priority=10)
        # The rest, alphabetical
        self.register_currency(
            'AED', 'U.A.E. dirham',
            start_date=date(2007, 9, 4), start_rate=0.2858, latest_rate=0.2757)
        self.register_currency(
            'ARS', 'Argentine peso',
            start_date=date(1998, 1, 2), start_rate=1.4259, latest_rate=0.2589)
        self.register_currency(
            'BRL', 'Brazilian real',
            start_date=date(1998, 1, 2), start_rate=1.2707, latest_rate=0.5741)
        self.register_currency(
            'BSD', 'Bahamian dollar',
            start_date=date(1998, 1, 2), start_rate=1.425, latest_rate=1.0128)
        self.register_currency(
            'CLP', 'Chilean peso',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.003236, latest_rate=0.001923)
        self.register_currency(
            'CNY', 'Chinese renminbi',
            start_date=date(1998, 1, 2), start_rate=0.1721, latest_rate=0.1484)
        self.register_currency(
            'COP', 'Colombian peso',
            start_date=date(1998, 1, 2), start_rate=0.00109, latest_rate=0.000513)
        self.register_currency(
            'CZK', 'Czech Republic koruna',
            start_date=date(1998, 2, 2), start_rate=0.04154, latest_rate=0.05202)
        self.register_currency(
            'DKK', 'Danish krone',
            start_date=date(1998, 1, 2), start_rate=0.2075, latest_rate=0.1785)
        self.register_currency(
            'FJD', 'Fiji dollar',
            start_date=date(1998, 1, 2), start_rate=0.9198, latest_rate=0.5235)
        self.register_currency(
            'GHS', 'Ghanaian cedi',
            start_date=date(2007, 7, 3), start_rate=1.1397, latest_rate=0.7134)
        self.register_currency(
            'GTQ', 'Guatemalan quetzal',
            start_date=date(2004, 12, 21), start_rate=0.15762, latest_rate=0.1264)
        self.register_currency(
            'HKD', 'Hong Kong dollar',
            start_date=date(1998, 1, 2), start_rate=0.1838, latest_rate=0.130385)
        self.register_currency(
            'HNL', 'Honduran lempira',
            start_date=date(1998, 1, 2), start_rate=0.108, latest_rate=0.0536)
        self.register_currency(
            'HRK', 'Croatian kuna',
            start_date=date(2002, 3, 1), start_rate=0.1863, latest_rate=0.1837)
        self.register_currency(
            'HUF', 'Hungarian forint',
            start_date=date(1998, 2, 2), start_rate=0.007003, latest_rate=0.00493)
        self.register_currency(
            'IDR', 'Indonesian rupiah',
            start_date=date(1998, 2, 2), start_rate=0.000145, latest_rate=0.000112)
        self.register_currency(
            'ILS', 'Israeli new shekel',
            start_date=date(1998, 1, 2), start_rate=0.4021, latest_rate=0.2706)
        self.register_currency(
            'ISK', 'Icelandic krona',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.01962, latest_rate=0.00782)
        self.register_currency(
            'JMD', 'Jamaican dollar',
            start_date=date(2001, 6, 25), start_rate=0.03341, latest_rate=0.01145)
        self.register_currency(
            'KRW', 'South Korean won',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.000841, latest_rate=0.000905)
        self.register_currency(
            'LKR', 'Sri Lanka rupee',
            start_date=date(1998, 1, 2), start_rate=0.02304, latest_rate=0.0089)
        self.register_currency(
            'MAD', 'Moroccan dirham',
            start_date=date(1998, 1, 2), start_rate=0.1461, latest_rate=0.1195)
        self.register_currency(
            'MMK', 'Myanmar (Burma) kyat',
            start_date=date(1998, 1, 2), start_rate=0.226, latest_rate=0.1793)
        self.register_currency(
            'MXN', 'Mexican peso',
            start_date=date(1998, 1, 2), start_rate=0.1769, latest_rate=0.08156)
        self.register_currency(
            'MYR', 'Malaysian ringgit',
            start_date=date(1998, 1, 2), start_rate=0.3594, latest_rate=0.3149)
        self.register_currency(
            'NOK', 'Norwegian krone',
            start_date=date(1998, 1, 2), start_rate=0.1934, latest_rate=0.1689)
        self.register_currency(
            'PAB', 'Panamanian balboa',
            start_date=date(1998, 1, 2), start_rate=1.425, latest_rate=1.0128)
        self.register_currency(
            'PEN', 'Peruvian new sol',
            start_date=date(1998, 1, 2), start_rate=0.5234, latest_rate=0.3558)
        self.register_currency(
            'PHP', 'Philippine peso',
            start_date=date(1998, 1, 2), start_rate=0.0345, latest_rate=0.02262)
        self.register_currency(
            'PKR', 'Pakistan rupee',
            start_date=date(1998, 1, 2), start_rate=0.03238, latest_rate=0.01206)
        self.register_currency(
            'PLN', 'Polish zloty',
            start_date=date(1998, 2, 2), start_rate=0.4108, latest_rate=0.3382)
        self.register_currency(
            'RON', 'Romanian new leu',
            start_date=date(2007, 9, 4), start_rate=0.4314, latest_rate=0.3215)
        self.register_currency(
            'RSD', 'Serbian dinar',
            start_date=date(2007, 9, 4), start_rate=0.0179, latest_rate=0.01338)
        self.register_currency(
            'RUB', 'Russian rouble',
            start_date=date(1998, 1, 2), start_rate=0.2375, latest_rate=0.03443)
        self.register_currency(
            'SEK', 'Swedish krona',
            start_date=date(1998, 1, 2), start_rate=0.1787, latest_rate=0.1378)
        self.register_currency(
            'SGD', 'Singapore dollar',
            start_date=date(1998, 1, 2), start_rate=0.84, latest_rate=0.7358)
        self.register_currency(
            'THB', 'Thai baht',
            start_date=date(1998, 1, 2), start_rate=0.0296, latest_rate=0.03134)
        self.register_currency(
            'TND', 'Tunisian dinar',
            exponent=3, start_date=date(1998, 1, 2), start_rate=1.2372, latest_rate=0.7037)
        self.register_currency(
            'TWD', 'Taiwanese new dollar',
            start_date=date(1998, 1, 2), start_rate=0.04338, latest_rate=0.03218)
        self.register_currency(
            'VEF', 'Venezuelan bolivar fuerte',
            start_date=date(2008, 1, 2), start_rate=0.4623, latest_rate=0.2358)
        self.register_currency(
            'VND', 'Vietnamese dong',
            start_date=date(2004, 1, 1), start_rate=8.2e-05, latest_rate=5.3e-05)
        self.register_currency(
            'XAF', 'CFA franc',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.002362, latest_rate=0.002027)
        self.register_currency(
            'XCD', 'East Caribbean dollar',
            start_date=date(1998, 1, 2), start_rate=0.5278, latest_rate=0.3793)
        self.register_currency(
            'XPF', 'CFP franc',
            exponent=0, start_date=date(1998, 1, 2), start_rate=0.01299, latest_rate=0.01114)

        CurrencyProviderPlugin._registered_default_currencies = True

    def get_currency_rate_today(self, currency_code):
        """Override this if you have a 'simple' provider.

        If your provider doesn't give rates for any other date than today, overriding this method
        instead of get_currency_rate() is the simplest choice.

        ``currency_code`` is a string representing the code of the currency to fetch, 'USD' for
        example.

        Return a float representing the value of 1 unit of your currency in CAD.

        If you can't get a rate, return ``None``.

        This method is called asynchronously, so it won't block moneyGuru if it takes time to
        resolve.
        """
        raise NotImplementedError()

    def get_currency_rates(self, currency_code, start_date, end_date):
        """Override this if your provider gives rates for past dates.

        If your provider gives rates for past dates, it's better (although a bit more complicated)
        to override this method so that moneyGuru can have more accurate rates.

        You must return a list of tuples (date, rate) with all rates you can fetch between
        start_date and end_date. You don't need to have one item for every single date in the range
        (for example, most of the time we don't have values during week-ends), moneyGuru correctly
        handles holes in those values. Simply return whatever you can get.

        If you can't get a rate, return an empty list.

        This method is called asynchronously, so it won't block moneyGuru if it takes time to
        resolve.
        """
        raise NotImplementedError()


class ImportActionPlugin(Plugin, Broadcaster):
    """
    Plugin allowing certain kinds of actions to be performed on import.
    By subclassing this plugin, you can add new currencies to moneyGuru and also add a new source
    to fetch those currencies' exchange rates.
    Subclasses :class:`Plugin`, :class:`Broadcaster`
    """
    TYPE_NAME = "Import Action"

    # Signal to the import window to change the name in our drop down list
    action_name_changed = 'action_name_changed'

    # The name that appears in our drop down list
    ACTION_NAME = None

    def __init__(self):
        Plugin.__init__(self)
        Broadcaster.__init__(self)

    def on_selected_pane_changed(self, selected_pane):
        """This method is called whenever the import window has changed it's selected pane."""
        pass

    def always_perform_action(self):
        return False

    def can_perform_action(self, import_document, transactions, panes, selected_rows=None):
        return True

    def perform_action(self, import_document, transactions, panes, selected_rows=None):
        pass


EntryMatch = namedtuple('EntryMatch', 'existing imported will_import weight')


class ImportBindPlugin(Plugin):
    TYPE_NAME = "Import Bind"

    def match_entries(self, target_account, document, import_document, existing_entries, imported_entries):
        # Returns a list of EntryMatch objects.
        return []

