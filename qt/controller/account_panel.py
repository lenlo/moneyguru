# Created By: Virgil Dupras
# Created On: 2009-11-10
# Copyright 2011 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import (QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox, QSizePolicy,
    QPlainTextEdit, QDialogButtonBox)

from hscommon.currency import Currency
from hscommon.trans import tr as trbase
from qtlib.selectable_list import ComboboxModel

from core.gui.account_panel import AccountPanel as AccountPanelModel

from .panel import Panel

tr = lambda s: trbase(s, "AccountPanel")

class AccountPanel(Panel):
    FIELDS = [
        ('nameEdit', 'name'),
        ('currencyComboBox', 'currency_index'),
        ('accountNumberEdit', 'account_number'),
        ('notesEdit', 'notes'),
    ]
    
    def __init__(self, mainwindow):
        Panel.__init__(self, mainwindow)
        self._setupUi()
        self.model = AccountPanelModel(view=self, mainwindow=mainwindow.model)
        self.typeComboBox = ComboboxModel(model=self.model.type_list, view=self.typeComboBoxView)
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
    
    def _setupUi(self):
        self.setWindowTitle(tr("Account Info"))
        self.resize(274, 121)
        self.setModal(True)
        self.verticalLayout = QVBoxLayout(self)
        self.formLayout = QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.label = QLabel(tr("Name"))
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)
        self.nameEdit = QLineEdit()
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.nameEdit)
        self.label_2 = QLabel(tr("Type"))
        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)
        self.typeComboBoxView = QComboBox()
        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.typeComboBoxView)
        self.label_3 = QLabel(tr("Currency"))
        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)
        self.currencyComboBox = QComboBox()
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.currencyComboBox.sizePolicy().hasHeightForWidth())
        self.currencyComboBox.setSizePolicy(sizePolicy)
        self.currencyComboBox.setEditable(True)
        self.currencyComboBox.setInsertPolicy(QComboBox.NoInsert)
        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.currencyComboBox)
        self.accountNumberLabel = QLabel(tr("Account #"))
        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.accountNumberLabel)
        self.accountNumberEdit = QLineEdit()
        self.accountNumberEdit.setMaximumSize(QSize(80, 16777215))
        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.accountNumberEdit)
        self.notesEdit = QPlainTextEdit()
        self.formLayout.setWidget(4, QFormLayout.FieldRole, self.notesEdit)
        self.label1 = QLabel(tr("Notes:"))
        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.label1)
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)
        self.verticalLayout.addWidget(self.buttonBox)
        self.label.setBuddy(self.nameEdit)
        self.label_2.setBuddy(self.typeComboBoxView)
        self.label_3.setBuddy(self.currencyComboBox)
        
        availableCurrencies = ['{currency.code} - {currency.name}'.format(currency=currency) for currency in Currency.all]
        self.currencyComboBox.addItems(availableCurrencies)
    
    def _loadFields(self):
        Panel._loadFields(self)
        self.currencyComboBox.setEnabled(self.model.can_change_currency)
    
