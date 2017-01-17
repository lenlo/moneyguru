# Copyright 2016 Lennart Lovstrand
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import yahoo_finance

import logging
from datetime import date, datetime

from core.model.currency import CurrencyNotSupportedException
from core.plugin import CurrencyProviderPlugin

class YahooFinanceProviderPlugin(CurrencyProviderPlugin):
    NAME = 'Yahoo Finance security price fetcher'
    AUTHOR = "Lennart Lovstrand"

    def get_currency_rates(self, currency_code, start_date, end_date):
        logging.debug("YahooFinance: Looking up %s for %s--%s",
                      currency_code, start_date, end_date)

        # We only handle stock symbols as indicated using a "^" prefix.
        if not currency_code.startswith('^'):
            raise CurrencyNotSupportedException()

        # XXX: Cache this?
        stock = yahoo_finance.Share(currency_code[1:])

        data = stock.get_historical(start_date.strftime('%Y-%m-%d'),
                                    end_date.strftime('%Y-%m-%d'))

        return [
            (datetime.strptime(item['Date'], '%Y-%m-%d'), float(item['Close']))
            for item in data
        ]

