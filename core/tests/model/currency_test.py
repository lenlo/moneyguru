# Created By: Virgil Dupras
# Created On: 2008-05-22
# Copyright 2015 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

from datetime import date, timedelta
import time

from pytest import raises
from hscommon.testutil import jointhreads, eq_

from ...model.amount import convert_amount
from ...model.amount import Amount
from ...model.currency import Currency, USD, CAD, RateProviderUnavailable, RatesDB
from ...plugin import yahoo_currency_provider, boc_currency_provider

def slow_down(func):
    def wrapper(*args, **kwargs):
        time.sleep(0.1)
        return func(*args, **kwargs)

    return wrapper

def set_ratedb_for_tests(async=False, slow_down_provider=False, provider=None):
    log = []

    # Returns a RatesDB that isn't async and that uses a fake provider
    def fake_provider(currency, start_date, end_date):
        log.append((start_date, end_date, currency))
        number_of_days = (end_date - start_date).days + 1
        return [(start_date + timedelta(i), 1.42 + (.01 * i)) for i in range(number_of_days)]

    db = RatesDB(':memory:', async=async)
    if provider is None:
        provider = fake_provider
    if slow_down_provider:
        provider = slow_down(provider)
    db.register_rate_provider(provider)
    Currency.set_rates_db(db)
    return db, log

def test_unknown_currency():
    # Only known currencies are accepted.
    with raises(ValueError):
        Currency('NOPE')

def test_async_and_repeat():
    # If you make an ensure_rates() call and then the same call right after (before the first one
    # is finished, the server will not be hit twice.
    db, log = set_ratedb_for_tests(async=True, slow_down_provider=True)
    lastweek = date.today() - timedelta(days=7)
    db.ensure_rates(lastweek, ['USD'])
    db.ensure_rates(lastweek, ['USD'])
    jointhreads()
    eq_(len(log), 1)

def test_seek_rate():
    # Trying to get rate around the existing date gives the rate in question.
    set_ratedb_for_tests()
    USD.set_CAD_value(0.98, date(2008, 5, 20))
    amount = Amount(42, USD)
    expected = Amount(42 * .98, CAD)
    eq_(convert_amount(amount, CAD, date(2008, 5, 21)), expected)
    eq_(convert_amount(amount, CAD, date(2008, 5, 19)), expected)

# ---
def test_ask_for_rates_in_the_past():
    # If a rate is asked for a date lower than the lowest fetched date, fetch that range.
    db, log = set_ratedb_for_tests()
    someday = date.today() - timedelta(days=4)
    db.ensure_rates(someday, ['USD']) # fetch some rates
    otherday = someday - timedelta(days=6)
    db.ensure_rates(otherday, ['USD']) # this one should also fetch rates
    eq_(len(log), 2)
    eq_(log[1], (otherday, someday - timedelta(days=1), 'USD'))

def test_ask_for_rates_in_the_future(monkeypatch):
    # If a rate is asked for a date equal or higher than the lowest fetched date, fetch cached_end - today.
    monkeypatch.patch_today(2008, 5, 30)
    db, log = set_ratedb_for_tests()
    db.set_CAD_value(date(2008, 5, 20), 'USD', 1.42)
    db.ensure_rates(date(2008, 5, 20), ['USD']) # this one should fetch 2008-5-21 up to today-1
    expected = [(date(2008, 5, 21), date(2008, 5, 29), 'USD')]
    eq_(log, expected)

def test_dont_crash_on_None_rates():
    # Don't crash when a currency provider returns None rates. Just ignore it.

    def provider(currency, start_date, end_date):
        return [(start_date, None)]

    db, log = set_ratedb_for_tests(provider=provider)
    db.ensure_rates(date(2008, 5, 20), ['USD']) # no crash
    db.get_rate(date(2008, 5, 20), 'USD', 'CAD') # no crash

# --- Test for the default XMLRPC provider
def exception_raiser(exception):
    def f(*args, **kwargs):
        raise exception
    return f

def test_no_internet(monkeypatch):
    # No crash occur if the computer don't have access to internet.
    from socket import gaierror
    monkeypatch.setattr(boc_currency_provider, 'urlopen', exception_raiser(gaierror()))
    monkeypatch.setattr(yahoo_currency_provider, 'urlopen', exception_raiser(gaierror()))
    with raises(RateProviderUnavailable):
        boc_currency_provider.BOCProviderPlugin().wrapped_get_currency_rates(
            'USD', date(2008, 5, 20), date(2008, 5, 20)
        )
        yahoo_currency_provider.YahooProviderPlugin().wrapped_get_currency_rates(
            'LVL', date(2008, 5, 20), date(2008, 5, 20)
        )

def test_connection_timeout(monkeypatch):
    # No crash occur the connection times out.
    from socket import error
    monkeypatch.setattr(boc_currency_provider, 'urlopen', exception_raiser(error()))
    monkeypatch.setattr(yahoo_currency_provider, 'urlopen', exception_raiser(error()))
    with raises(RateProviderUnavailable):
        boc_currency_provider.BOCProviderPlugin().wrapped_get_currency_rates(
            'USD', date(2008, 5, 20), date(2008, 5, 20)
        )
        yahoo_currency_provider.YahooProviderPlugin().wrapped_get_currency_rates(
            'LVL', date(2008, 5, 20), date(2008, 5, 20)
        )

