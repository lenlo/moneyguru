# Created By: Virgil Dupras
# Created On: 2009-11-17
# Copyright 2015 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.gnu.org/licenses/gpl-3.0.html

import os.path as op

from PyQt5.QtCore import QLocale
from PyQt5.QtWidgets import QApplication

from core.model.date import clean_format
from qtlib.preferences import Preferences as PreferencesBase

class Preferences(PreferencesBase):
    def _load_values(self, settings):
        get = self.get_value
        self.recentDocuments = get('RecentDocuments', self.recentDocuments)
        self.recentDocuments = list(filter(op.exists, self.recentDocuments))
        self.dateFormat = get('DateFormat', self.dateFormat)
        self.tableFontSize = get('TableFontSize', self.tableFontSize)
        self.language = get('Language', self.language)
        self.debugMode = get('DebugMode', self.debugMode)
        
    def reset(self):
        locale = QLocale.system()
        self.recentDocuments = []
        dateFormat = str(locale.dateFormat(QLocale.ShortFormat))
        dateFormat = clean_format(dateFormat)
        self.dateFormat = dateFormat
        self.tableFontSize = QApplication.font().pointSize()
        self.language = ''
        self.debugMode = False
        
    def _save_values(self, settings):
        set_ = self.set_value
        set_('RecentDocuments', self.recentDocuments)
        set_('DateFormat', self.dateFormat)
        set_('TableFontSize', self.tableFontSize)
        set_('Language', self.language)
        set_('DebugMode', self.debugMode)
    
