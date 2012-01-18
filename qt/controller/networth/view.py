# Created By: Virgil Dupras
# Created On: 2009-11-01
# Copyright 2011 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtCore import QSize
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout, QFrame, QAbstractItemView

from core.const import PaneArea
from core.gui.networth_view import NetWorthView as NetWorthViewModel

from ...support.item_view import TreeView
from ...support.pie_chart_view import PieChartView
from ...support.line_graph_view import LineGraphView
from ..base_view import BaseView
from .sheet import NetWorthSheet
from .graph import NetWorthGraph
from .asset_pie_chart import AssetPieChart
from .liability_pie_chart import LiabilityPieChart

class NetWorthView(BaseView):
    def __init__(self, mainwindow):
        BaseView.__init__(self)
        self.doc = mainwindow.doc
        self._setupUi()
        self.model = NetWorthViewModel(view=self, mainwindow=mainwindow.model)
        self.nwsheet = NetWorthSheet(self, view=self.treeView)
        self.nwgraph = NetWorthGraph(self, view=self.graphView)
        self.apiechart = AssetPieChart(self, view=self.assetPieChart)
        self.lpiechart = LiabilityPieChart(self, view=self.liabilityPieChart)
        children = [self.nwsheet.model, self.nwgraph.model, self.apiechart.model, self.lpiechart.model]
        self.model.set_children(children)
    
    def _setupUi(self):
        self.resize(558, 447)
        self.verticalLayout_2 = QVBoxLayout(self)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setMargin(0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.treeView = TreeView(self)
        self.treeView.setAcceptDrops(True)
        self.treeView.setFrameShape(QFrame.NoFrame)
        self.treeView.setFrameShadow(QFrame.Plain)
        self.treeView.setEditTriggers(QAbstractItemView.EditKeyPressed|QAbstractItemView.SelectedClicked)
        self.treeView.setDragEnabled(True)
        self.treeView.setDragDropMode(QAbstractItemView.InternalMove)
        self.treeView.setUniformRowHeights(True)
        self.treeView.setAllColumnsShowFocus(True)
        self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeView.header().setStretchLastSection(False)
        self.horizontalLayout.addWidget(self.treeView)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.assetPieChart = PieChartView(self)
        self.assetPieChart.setMinimumSize(QSize(250, 0))
        self.verticalLayout.addWidget(self.assetPieChart)
        self.liabilityPieChart = PieChartView(self)
        self.verticalLayout.addWidget(self.liabilityPieChart)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.graphView = LineGraphView(self)
        self.graphView.setMinimumSize(QSize(0, 200))
        self.verticalLayout_2.addWidget(self.graphView)
    
    #--- QWidget override
    def setFocus(self):
        self.nwsheet.view.setFocus()
    
    #--- Public
    def fitViewsForPrint(self, viewPrinter):
        hidden = self.model.mainwindow.hidden_areas
        viewPrinter.fitTree(self.nwsheet)
        if PaneArea.RightChart not in hidden:
            viewPrinter.fit(self.apiechart.view, 150, 150, expandH=True)
            viewPrinter.fit(self.lpiechart.view, 150, 150, expandH=True)
        if PaneArea.BottomGraph not in hidden:
            viewPrinter.fit(self.nwgraph.view, 300, 150, expandH=True, expandV=True)
    
    #--- model --> view
    def update_visibility(self):
        hidden = self.model.mainwindow.hidden_areas
        self.graphView.setHidden(PaneArea.BottomGraph in hidden)
        self.assetPieChart.setHidden(PaneArea.RightChart in hidden)
        self.liabilityPieChart.setHidden(PaneArea.RightChart in hidden)
    
