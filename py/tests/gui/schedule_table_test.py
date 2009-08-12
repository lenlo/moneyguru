# Created By: Virgil Dupras
# Created On: 2009-08-12
# $Id$
# Copyright 2009 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "HS" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/hs_license

from nose.tools import eq_

from ..base import TestCase, CommonSetup

class OneDailyScheduledTransaction(TestCase, CommonSetup):
    def setUp(self):
        self.create_instances()
        self.setup_monthly_range()
        self.setup_scheduled_transaction()
        self.document.select_schedule_table()
    
    def test_edit_stop_date(self):
        # When editing stop date with an invalid date, just abort the edition. stop date is one
        # of those date field where a None value is possible.
        self.sctable[0].stop_date = 'invalid' # no crash
        eq_(self.sctable[0].stop_date, '--') # None display value
    
