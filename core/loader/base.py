# Copyright 2016 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import datetime
import logging
import re
from itertools import groupby
from operator import attrgetter

from hscommon.util import nonone, flatten, stripfalse, dedupe
from hscommon.trans import tr

from ..exception import FileFormatError
from ..model.account import Account, Group, AccountList, GroupList, AccountType
from ..model.amount import parse_amount, of_currency, UnsupportedCurrencyError
from ..model.budget import Budget
from ..model.currency import Currency
from ..model.oven import Oven
from ..model.recurrence import Recurrence, Spawn
from ..model.transaction import Transaction, Split
from ..model.transaction_list import TransactionList

# date formats to use for format guessing
# there is not one test for each single format
# The order of the fields depending on the separator is different because we try to minimize the
# possibility of errors. Most american users use the slash separator with month as a first field
# and most european users have dot or hyphen seps with the first field being the day.

BASE_DATE_FORMATS = [
    '%m/%d/%y', '%m/%d/%Y', '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d', '%d/%b/%Y', '%d/%b/%y'
]
EXTRA_DATE_SEPS = ['.', '-', ' ']
DATE_FORMATS = BASE_DATE_FORMATS[:]
# Re-add all date formats with their separator replaced
for sep in EXTRA_DATE_SEPS:
    for base_format in BASE_DATE_FORMATS:
        DATE_FORMATS.append(base_format.replace('/', sep))
# Finally, add special formats
DATE_FORMATS += ['%m/%d\'%y', '%Y%m%d']

POSSIBLE_PATTERNS = [
    r'[\d/.\- ]{6,10}',
    r'\d{1,2}[/.\- ]\w{3}[/.\- ]\d{2,4}',
    r"\d{1,2}/\d{1,2}'\d{2,4}",
]
re_possibly_a_date = re.compile('|'.join(POSSIBLE_PATTERNS))

class Loader:
    """Base interface for loading files containing financial information to load into moneyGuru.

    To use it, just call load() and then fetch the accounts & transactions. This information is in
    the form of lists of dicts. The transactions are sorted in order of date.
    """
    FILE_OPEN_MODE = 'rt'
    FILE_ENCODING = 'utf-8'
    # Native date format is a format native to the file type. It doesn't necessarily means that it's
    # the only possible date format in it, but it's the one that will be tried first when guessing
    # (before the default date format). If guessing never occurs, it will be the parsing date format.
    # This format is a sys format (%-based)
    NATIVE_DATE_FORMAT = None
    # Some extra date formats to try before standard date guessing order
    EXTRA_DATE_FORMATS = None
    # Whether we fail with a ``FileFormatError`` when encountering an unsupported currency or we
    # fall back to the default currency
    STRICT_CURRENCY = False

    def __init__(self, default_currency, default_date_format=None):
        self.default_currency = default_currency
        self.default_date_format = default_date_format
        self.groups = GroupList()
        self.accounts = AccountList(default_currency)
        self.transactions = TransactionList()
        # I did not manage to create a repeatable test for it, but self.schedules has to be ordered
        # because the order in which the spawns are created must stay the same
        self.schedules = []
        self.budgets = []
        self.properties = {}
        self.oven = Oven(self.accounts, self.transactions, self.schedules, self.budgets)
        self.target_account = None # when set, overrides the reference matching system
        self.currency_infos = []
        self.group_infos = []
        self.account_infos = []
        self.transaction_infos = []
        self.recurrence_infos = []
        self.budget_infos = []
        self.currency_info = CurrencyInfo()
        self.group_info = GroupInfo()
        self.account_info = AccountInfo()
        self.transaction_info = TransactionInfo()
        self.transaction_cancelled = False
        self.split_info = SplitInfo()
        self.recurrence_info = RecurrenceInfo()
        self.budget_info = BudgetInfo()
        self.document_id = None
        # The Loader subclass should set parsing_date_format to the format used (system-type) when
        # parsing dates. This format is used in the ImportWindow. It is also used in
        # self.parse_date_str as a default value
        self.parsing_date_format = self.NATIVE_DATE_FORMAT

    # --- Virtual
    def _parse(self, infile):
        """Parse infile and raise FileFormatError if infile is not the right format. Don't bother
        with an exception message, app.MoneyGuru will re-raise it with a message if needed.
        """
        raise NotImplementedError()

    def _load(self):
        """Use the parsed info to fill the appropriate account/txn info with the start_* and flush_*
        methods.
        """
        raise NotImplementedError()

    def _post_load(self):
        """Perform post load processing, such as duplicate removal
        """
        pass

    # --- Protected
    def clean_date(self, str_date):
        # return str_date without garbage around (such as timestamps) or None if impossible
        match = re_possibly_a_date.search(str_date)
        return match.group() if match is not None else None

    def guess_date_format(self, str_dates):
        totry = DATE_FORMATS[:]
        extra = []
        if self.NATIVE_DATE_FORMAT:
            extra.append(self.NATIVE_DATE_FORMAT)
        if self.EXTRA_DATE_FORMATS:
            extra += self.EXTRA_DATE_FORMATS
        if self.default_date_format:
            extra.append(self.default_date_format)
        for format in dedupe(extra + totry):
            found_at_least_one = False
            for str_date in str_dates:
                try:
                    datetime.datetime.strptime(str_date, format)
                    found_at_least_one = True
                except ValueError:
                    logging.debug("Failed try to read the date {0} with the format {1}".format(str_date, format))
                    break
            else:
                if found_at_least_one:
                    logging.debug("Correct date format: {0}".format(format))
                    return format
        return None

    def parse_date_str(self, date_str, date_format=None):
        """Parses date_str using date_format and perform heuristic fixes if needed.
        """
        if not date_format:
            date_format = self.parsing_date_format
        result = datetime.datetime.strptime(date_str, date_format).date()
        if result.year < 1900:
            # we have a typo in the house. Just use 2000 + last-two-digits
            year = (result.year % 100) + 2000
            result = result.replace(year=year)
        return result

    def start_currency(self):
        pass

    def flush_currency(self):
        if self.currency_info.is_valid():
            self.currency_infos.append(self.currency_info)
        self.currency_info = CurrencyInfo()

    def start_group(self):
        pass

    def flush_group(self):
        if self.group_info.is_valid():
            self.group_infos.append(self.group_info)
        self.group_info = GroupInfo()

    def start_account(self):
        self.flush_account() # Implicit

    def flush_account(self):
        self.flush_transaction()
        if self.account_info.is_valid():
            self.account_infos.append(self.account_info)
        self.account_info = AccountInfo()

    def cancel_account(self):
        self.account_info = AccountInfo()
        self.transaction_info = TransactionInfo()
        self.split_info = SplitInfo()

    def start_transaction(self):
        self.flush_transaction() # Implicit

    def flush_transaction(self):
        """If called between a start_account and flush_account call, ACCOUNT is automatically set"""
        self.flush_split()
        if not self.transaction_cancelled:
            if self.transaction_info.account is None and self.account_info and self.account_info.name:
                self.transaction_info.account = self.account_info.name
            if self.transaction_info.is_valid():
                self.transaction_infos.append(self.transaction_info)
        self.transaction_cancelled = False
        self.transaction_info = TransactionInfo()

    def cancel_transaction(self):
        self.transaction_cancelled = True

    def flush_split(self):
        if self.split_info.is_valid():
            self.transaction_info.splits.append(self.split_info)
        self.split_info = SplitInfo()

    def flush_recurrence(self):
        if self.recurrence_info.is_valid():
            self.recurrence_infos.append(self.recurrence_info)
        self.recurrence_info = RecurrenceInfo()

    def flush_budget(self):
        if self.budget_info.is_valid():
            self.budget_infos.append(self.budget_info)
        self.budget_info = BudgetInfo()

    # --- Public
    def parse(self, filename):
        """Parses 'filename' and raises FileFormatError if appropriate."""
        try:
            if 't' in self.FILE_OPEN_MODE:
                kw = {'encoding': self.FILE_ENCODING, 'errors': 'ignore'}
            else:
                kw = {}
            with open(filename, self.FILE_OPEN_MODE, **kw) as infile:
                self._parse(infile)
        except IOError:
            raise FileFormatError()

    @classmethod
    def parse_amount(cls, string, currency):
        try:
            return parse_amount(
                string, currency, with_expression=False, strict_currency=cls.STRICT_CURRENCY
            )
        except UnsupportedCurrencyError as e:
            msg = tr(
                "Unsupported currency: {}. Aborting load. Did you disable a currency plugin?"
            ).format(e.currency)
            raise FileFormatError(msg)

    def load(self):
        """Loads the parsed info into self.accounts and self.transactions.

        You must have called parse() before calling this.
        """
        def load_transaction_info(info):
            description = info.description
            payee = info.payee
            checkno = info.checkno
            date = info.date
            transaction = Transaction(date, description, payee, checkno)
            transaction.notes = nonone(info.notes, '')
            for split_info in info.splits:
                account = split_info.account
                amount = split_info.amount
                if split_info.amount_reversed:
                    amount = -amount
                memo = nonone(split_info.memo, '')
                split = Split(transaction, account, amount)
                split.memo = memo
                if account is None or not of_currency(amount, account.currency):
                    # fix #442: off-currency transactions shouldn't be reconciled
                    split.reconciliation_date = None
                elif split_info.reconciliation_date is not None:
                    split.reconciliation_date = split_info.reconciliation_date
                elif split_info.reconciled: # legacy
                    split.reconciliation_date = transaction.date
                split.reference = split_info.reference
                transaction.splits.append(split)
            while len(transaction.splits) < 2:
                transaction.splits.append(Split(transaction, None, 0))
            transaction.balance()
            transaction.mtime = info.mtime
            if info.reference is not None:
                for split in transaction.splits:
                    if split.reference is None:
                        split.reference = info.reference
            return transaction

        self._load()
        self.flush_account() # Implicit
        # Now, we take the info we have and transform it into model instances
        start_date = datetime.date.max
        currencies = set()
        for info in self.currency_infos:
            logging.debug("# Registering %s (%s, %s)" % (info.code, info.name, info.exponent))
            try:
                Currency(info.code)
            except ValueError:
                Currency.register(info.code, info.name, info.exponent)
        for info in self.group_infos:
            group = Group(info.name, info.type)
            self.groups.append(group)
        for info in self.account_infos:
            account_type = info.type
            if account_type not in AccountType.All:
                account_type = AccountType.Asset
            account_currency = self.default_currency
            try:
                if info.currency:
                    account_currency = Currency(info.currency)
            except ValueError:
                pass # keep account_currency as self.default_currency
            account = Account(info.name, account_currency, account_type)
            if info.group:
                account.group = self.groups.find(info.group, account_type)
            if info.budget:
                self.budget_infos.append(BudgetInfo(info.name, info.budget_target, info.budget))
            account.reference = info.reference
            account.account_number = info.account_number
            account.inactive = info.inactive
            account.notes = info.notes
            currencies.add(account.currency)
            self.accounts.add(account)

        # Pre-parse transaction info. We bring all relevant info recorded at the txn level into the split level
        all_txn = self.transaction_infos + [r.transaction_info for r in self.recurrence_infos] +\
            flatten([stripfalse(r.date2exception.values()) for r in self.recurrence_infos]) +\
            flatten([r.date2globalchange.values() for r in self.recurrence_infos])
        for info in all_txn:
            split_accounts = [s.account for s in info.splits]
            if info.account and info.account not in split_accounts:
                info.splits.insert(0, SplitInfo(info.account, info.amount, info.currency, False))
            if info.transfer and info.transfer not in split_accounts:
                info.splits.append(SplitInfo(info.transfer, info.amount, info.currency, True))
            for split_info in info.splits:
                # this amount is just to determine the auto_create_type
                str_amount = split_info.amount
                if split_info.currency:
                    str_amount += split_info.currency
                amount = self.parse_amount(str_amount, self.default_currency)
                auto_create_type = AccountType.Income if amount >= 0 else AccountType.Expense
                split_info.account = (
                    self.accounts.find(split_info.account, auto_create_type)
                    if split_info.account
                    else None
                )
                currency = split_info.account.currency if split_info.account is not None else self.default_currency
                split_info.amount = self.parse_amount(str_amount, currency)
                if split_info.amount:
                    currencies.add(split_info.amount.currency)

        self.transaction_infos.sort(key=attrgetter('date'))
        for date, transaction_infos in groupby(self.transaction_infos, attrgetter('date')):
            start_date = min(start_date, date)
            for position, info in enumerate(transaction_infos, start=1):
                transaction = load_transaction_info(info)
                self.transactions.add(transaction, position=position)

        # Scheduled
        for info in self.recurrence_infos:
            ref = load_transaction_info(info.transaction_info)
            recurrence = Recurrence(ref, info.repeat_type, info.repeat_every)
            recurrence.stop_date = info.stop_date
            for date, transaction_info in info.date2exception.items():
                if transaction_info is not None:
                    exception = load_transaction_info(transaction_info)
                    spawn = Spawn(recurrence, exception, date, exception.date)
                    recurrence.date2exception[date] = spawn
                else:
                    recurrence.delete_at(date)
            for date, transaction_info in info.date2globalchange.items():
                change = load_transaction_info(transaction_info)
                spawn = Spawn(recurrence, change, date, change.date)
                recurrence.date2globalchange[date] = spawn
            self.schedules.append(recurrence)
        # Budgets
        TODAY = datetime.date.today()
        fallback_start_date = datetime.date(TODAY.year, TODAY.month, 1)
        for info in self.budget_infos:
            account = self.accounts.find(info.account)
            if account is None:
                continue
            target = self.accounts.find(info.target) if info.target else None
            amount = self.parse_amount(info.amount, account.currency)
            start_date = nonone(info.start_date, fallback_start_date)
            budget = Budget(account, target, amount, start_date, repeat_type=info.repeat_type)
            budget.notes = nonone(info.notes, '')
            budget.stop_date = info.stop_date
            if info.repeat_every:
                budget.repeat_every = info.repeat_every
            self.budgets.append(budget)
        self._post_load()
        self.oven.cook(datetime.date.min, until_date=None)
        Currency.get_rates_db().ensure_rates(start_date, [x.code for x in currencies])


class CurrencyInfo:
    def __init__(self):
        self.code = None
        self.name = None
        self.exponent = 2

    def is_valid(self):
        return bool(self.code)


class GroupInfo:
    def __init__(self):
        self.name = None
        self.type = AccountType.Asset

    def is_valid(self):
        return bool(self.name)


class AccountInfo:
    def __init__(self):
        self.name = None
        self.currency = None
        self.type = AccountType.Asset
        self.group = None
        self.budget = None
        self.budget_target = None
        self.reference = None
        self.balance = None
        self.account_number = ''
        self.inactive = False
        self.notes = ''

    def __repr__(self):
        return '<AccountInfo: %s>' % self.name

    def is_valid(self):
        return bool(self.name)


class TransactionInfo:
    def __init__(self):
        self.date = None
        self.description = None
        self.payee = None
        self.checkno = None
        self.notes = None
        self.account = None
        self.transfer = None
        self.amount = None
        self.currency = None
        self.reference = None # will be applied to all splits
        self.mtime = 0
        self.splits = []

    def is_valid(self):
        return bool(self.date and ((self.account and self.amount) or self.splits))


class SplitInfo:
    def __init__(self, account=None, amount=None, currency=None, amount_reversed=False):
        self.account = account
        self.amount = amount
        self.currency = currency
        self.memo = None
        self.reconciled = False
        self.reconciliation_date = None
        self.reference = None
        self.amount_reversed = amount_reversed

    def __repr__(self):
        return '<SplitInfo %r %r>' % (self.account, self.amount)

    def is_valid(self):
        return self.amount is not None


class RecurrenceInfo:
    def __init__(self):
        self.repeat_type = None
        self.repeat_every = 1
        self.stop_date = None
        self.date2exception = {}
        self.date2globalchange = {}
        self.transaction_info = TransactionInfo()

    def is_valid(self):
        return self.transaction_info.is_valid()


class BudgetInfo:
    def __init__(self, account=None, target=None, amount=None):
        self.account = account
        self.target = target
        self.amount = amount
        self.notes = None
        self.repeat_type = None
        self.repeat_every = None
        self.start_date = None
        self.stop_date = None

    def is_valid(self):
        return self.account and self.amount

