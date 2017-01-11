# Copyright 2016 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import re
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from core.model.currency import RateProviderUnavailable
from core.plugin import CurrencyProviderPlugin

CURRENCY2BOCID = {
    'USD': 'LOOKUPS_IEXE0101',
    'ARS': 'LOOKUPS_IEXE2702',
    'AUD': 'LOOKUPS_IEXE1601',
    'BSD': 'LOOKUPS_IEXE6001',
    'BRL': 'LOOKUPS_IEXE2801',
    'XAF': 'LOOKUPS_IEXE4501',
    'XPF': 'LOOKUPS_IEXE4601',
    'CLP': 'LOOKUPS_IEXE2901',
    'CNY': 'LOOKUPS_IEXE2201',
    'COP': 'LOOKUPS_IEXE3901',
    'HRK': 'LOOKUPS_IEXE6101',
    'CZK': 'LOOKUPS_IEXE2301',
    'DKK': 'LOOKUPS_IEXE0301',
    'XCD': 'LOOKUPS_IEXE4001',
    'EUR': 'LOOKUPS_EUROCAE01',
    'FJD': 'LOOKUPS_IEXE4101',
    'GHS': 'LOOKUPS_IEXE4702',
    'GTQ': 'LOOKUPS_IEXE6501',
    'HNL': 'LOOKUPS_IEXE4301',
    'HKD': 'LOOKUPS_IEXE1401',
    'HUF': 'LOOKUPS_IEXE2501',
    'ISK': 'LOOKUPS_IEXE4401',
    'INR': 'LOOKUPS_IEXE3001',
    'IDR': 'LOOKUPS_IEXE2601',
    'ILS': 'LOOKUPS_IEXE5301',
    'JMD': 'LOOKUPS_IEXE6401',
    'JPY': 'LOOKUPS_IEXE0701',
    'MYR': 'LOOKUPS_IEXE3201',
    'MXN': 'LOOKUPS_IEXE2001',
    'MAD': 'LOOKUPS_IEXE4801',
    'MMK': 'LOOKUPS_IEXE3801',
    'NZD': 'LOOKUPS_IEXE1901',
    'NOK': 'LOOKUPS_IEXE0901',
    'PKR': 'LOOKUPS_IEXE5001',
    'PAB': 'LOOKUPS_IEXE5101',
    'PEN': 'LOOKUPS_IEXE5201',
    'PHP': 'LOOKUPS_IEXE3301',
    'PLN': 'LOOKUPS_IEXE2401',
    'RON': 'LOOKUPS_IEXE6505',
    'RUB': 'LOOKUPS_IEXE2101',
    'RSD': 'LOOKUPS_IEXE6504',
    'SGD': 'LOOKUPS_IEXE3701',
    'SKK': 'LOOKUPS_IEXE6201',
    'ZAR': 'LOOKUPS_IEXE3401',
    'KRW': 'LOOKUPS_IEXE3101',
    'LKR': 'LOOKUPS_IEXE5501',
    'SEK': 'LOOKUPS_IEXE1001',
    'CHF': 'LOOKUPS_IEXE1101',
    'TWD': 'LOOKUPS_IEXE3501',
    'THB': 'LOOKUPS_IEXE3601',
    'TND': 'LOOKUPS_IEXE5701',
    'AED': 'LOOKUPS_IEXE6506',
    'GBP': 'LOOKUPS_IEXE1201',
    'VEF': 'LOOKUPS_IEXE5902',
    'VND': 'LOOKUPS_IEXE6503',
}

class BOCProviderPlugin(CurrencyProviderPlugin):
    NAME = 'Bank of Canada currency rates fetcher'
    AUTHOR = "Virgil Dupras"

    def get_currency_rates(self, currency_code, start_date, end_date):
        form_data = {
            'lookupPage': 'lookup_daily_exchange_rates.php',
            'startRange': '2001-07-07',
            'dFrom': start_date.strftime('%Y-%m-%d'),
            'dTo': end_date.strftime('%Y-%m-%d'),
            'series[]': [
                CURRENCY2BOCID[currency_code],
            ],
        }
        url = 'http://www.bankofcanada.ca/rates/exchange/10-year-lookup/'
        try:
            with urlopen(url, urlencode(form_data, True).encode('ascii')) as response:
                contents = response.read().decode('latin-1')
        except Exception:
            raise RateProviderUnavailable()
        # search for a link to XML data
        match = re.search(r'(?<=")http://www\.bankofcanada\.ca/stats/results//?csv.*?(?=")', contents)
        if not match:
            raise RateProviderUnavailable()
        csv_url = contents[match.start():match.end()]
        with urlopen(csv_url) as csv_file:
            # Our "CSV file" starts with non-CSV data that we don't care about, and at the end,
            # there's the data we care about, starting with a header "Date,currency" (example:
            # "Date,USD"). The rest is a list of lines "date,rate".
            csv_contents = csv_file.read().decode('ascii')
            _, rates_contents = csv_contents.split('\nDate,%s\n' % currency_code)
            lines = rates_contents.splitlines()

            def convert(s):
                sdate, svalue = s.split(',')
                date = datetime.strptime(sdate, '%Y-%m-%d').date()
                try:
                    value = float(svalue)
                except ValueError:
                    # We sometimes have the value "Bank Holiday"
                    value = None
                return (date, value)
            try:
                return [convert(l) for l in lines]
            except Exception:
                raise RateProviderUnavailable()

