# Copyright 2016 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import sys
import os.path as op
import xml.etree.cElementTree as ET

from ..model.amount import format_amount
from ..model.currency import Currency
from hscommon.util import remove_invalid_xml, ensure_folder

def save(filename, document_id, properties, accounts, groups, transactions, schedules, budgets):
    def date2str(date):
        return date.strftime('%Y-%m-%d')

    def handle_newlines(s):
        # etree doesn't correctly save newlines. In fields that allow it, we have to escape them so
        # that we can restore them during load.
        # XXX It seems like newer version of etree do escape newlines. When we use Python 3.2, we
        # can probably remove this.
        if not s:
            return s
        return s.replace('\n', '\\n')

    def setattrib(attribs, attribname, value):
        if value:
            attribs[attribname] = value

    def write_transaction_element(parent_element, transaction):
        transaction_element = ET.SubElement(parent_element, 'transaction')
        attrib = transaction_element.attrib
        attrib['date'] = date2str(transaction.date)
        setattrib(attrib, 'description', transaction.description)
        setattrib(attrib, 'payee', transaction.payee)
        setattrib(attrib, 'checkno', transaction.checkno)
        setattrib(attrib, 'notes', handle_newlines(transaction.notes))
        attrib['mtime'] = str(int(transaction.mtime))
        for split in transaction.splits:
            split_element = ET.SubElement(transaction_element, 'split')
            attrib = split_element.attrib
            attrib['account'] = split.account_name
            attrib['amount'] = format_amount(split.amount)
            setattrib(attrib, 'memo', split.memo)
            setattrib(attrib, 'reference', split.reference)
            if split.reconciliation_date is not None:
                attrib['reconciliation_date'] = date2str(split.reconciliation_date)

    root = ET.Element('moneyguru-file')
    root.attrib['document_id'] = document_id
    props_element = ET.SubElement(root, 'properties')
    for name, value in properties.items():
        if name == 'default_currency':
            value = value.code
        else:
            value = str(value)
        props_element.attrib[name] = value
    for currency in Currency.all:
        if currency.user_defined:
            currency_element = ET.SubElement(root, 'currency')
            attrib = currency_element.attrib
            attrib['code'] = currency.code
            attrib['exponent'] = str(currency.exponent)
            if currency.name:
                attrib['name'] = currency.name
            if currency.base_currency:
                attrib['base'] = currency.base_currency.code
    for group in groups:
        group_element = ET.SubElement(root, 'group')
        attrib = group_element.attrib
        attrib['name'] = group.name
        attrib['type'] = group.type
    for account in accounts:
        account_element = ET.SubElement(root, 'account')
        attrib = account_element.attrib
        attrib['name'] = account.name
        attrib['currency'] = account.currency.code
        attrib['type'] = account.type
        if account.group:
            attrib['group'] = account.group.name
        if account.reference is not None:
            attrib['reference'] = account.reference
        if account.account_number:
            attrib['account_number'] = account.account_number
        if account.inactive:
            attrib['inactive'] = 'y'
        if account.notes:
            attrib['notes'] = handle_newlines(account.notes)
    for transaction in transactions:
        write_transaction_element(root, transaction)
    # the functionality of the line below is untested because it's an optimisation
    scheduled = [s for s in schedules if s.is_alive]
    for recurrence in scheduled:
        recurrence_element = ET.SubElement(root, 'recurrence')
        attrib = recurrence_element.attrib
        attrib['type'] = recurrence.repeat_type
        attrib['every'] = str(recurrence.repeat_every)
        if recurrence.stop_date is not None:
            attrib['stop_date'] = date2str(recurrence.stop_date)
        for date, change in recurrence.date2globalchange.items():
            change_element = ET.SubElement(recurrence_element, 'change')
            change_element.attrib['date'] = date2str(date)
            if change is not None:
                write_transaction_element(change_element, change)
        for date, exception in recurrence.date2exception.items():
            exception_element = ET.SubElement(recurrence_element, 'exception')
            exception_element.attrib['date'] = date2str(date)
            if exception is not None:
                write_transaction_element(exception_element, exception)
        write_transaction_element(recurrence_element, recurrence.ref)
    for budget in budgets:
        budget_element = ET.SubElement(root, 'budget')
        attrib = budget_element.attrib
        attrib['account'] = budget.account.name
        attrib['type'] = budget.repeat_type
        attrib['every'] = str(budget.repeat_every)
        attrib['amount'] = format_amount(budget.amount)
        attrib['notes'] = budget.notes
        if budget.target is not None:
            attrib['target'] = budget.target.name
        attrib['start_date'] = date2str(budget.start_date)
        if budget.stop_date is not None:
            attrib['stop_date'] = date2str(budget.stop_date)
    for elem in root.getiterator():
        attrib = elem.attrib
        for key, value in attrib.items():
            attrib[key] = remove_invalid_xml(value)
    tree = ET.ElementTree(root)
    ensure_folder(op.dirname(filename))
    fp = open(filename, 'wt', encoding='utf-8')
    fp.write('<?xml version="1.0" encoding="utf-8"?>\n')
    # This 'unicode' encoding thing is only available (and necessary) from Python 3.2
    if sys.version_info[1] >= 2:
        tree.write(fp, encoding='unicode')
    else:
        tree.write(fp)
