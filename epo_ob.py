"""
EPO_OB
======
Application based on PyQt5 for logging times and scores of EPO runners.

**Idea:** Input is csv file which contains at least one column with names. This
csv files is loaded into pd.DataFrame which is shown as a table. Any manual
change in the table changes entry in the dataframe and table is then completely
redrawn (yes, redraw one line or one cell is faster but requires more coding).
Dataframe is automatically saved as csv file after every change.
"""

import os
import re
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from timeit import default_timer as timer 
import unidecode
import qtawesome as qta         # run `qta-browser`
import ftplib
import ftp_credentials

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtGui import (QColor, QBrush, QFont, QTextCursor, QRegExpValidator, QKeySequence)
from PyQt5.QtCore import (QPoint, Qt, QTimer, QRegExp)
from PyQt5.QtWidgets import (QAction, QDialogButtonBox, QInputDialog, QDialog, QFileDialog, QStyle, QComboBox, QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QStyleFactory, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

def str2sec(time_str:str):
    
    """ Convert string '+-HH:MM:SS' to seconds """

    if time_str == '': return np.nan

    try:
        time_str = time_str.replace('+','')
        sign = 1 if '-' not in time_str else -1
        time_str = time_str.replace('-','')
        h,m,s = time_str.split(':')
        # print(f'str2sec({time_str})',sign,h,m,s)
        return sign*(int(h)*3600 + int(m)*60 + int(s))
    except:
        return np.nan

def sec2str(seconds:int,add_sign=False):

    """ Convert seconds to string 'HH:MM:SS' """

    if np.isnan(seconds): return np.nan
    
    if seconds >= 0:
        if add_sign:
            sign = '+'
        else:
            sign = ''
    else:
        sign = '-'
    seconds = abs(seconds)

    m, s = divmod(seconds,60)
    h, m = divmod(m,60)
    return sign + '%02d:%02d:%02d'%(h,m,s)

def isNumber(num:str):

    try:
        float(num)
        if np.isnan(float(num)):
            return False
        return True
    except:
        return False

def diff_times(start_str:str,finish_str:str):
    
    if start_str=='' or finish_str=='': return ''

    sec1 = str2sec(start_str)
    sec2 = str2sec(finish_str)
    if sec1 is None or sec2 is None: return None
    
    diff = sec2-sec1
    m, s = divmod(diff,60)
    h, m = divmod(m,60)
    return '%02d:%02d:%02d'%(h,m,s)

def standardIcon(icon):
    return QWidget().style().standardIcon(getattr(QStyle,icon))

class ActionDialog(QAction):
    """ Just a simple action to show dialog window """

    def __init__(self,parent,
        actionStr,actionStatusTip,actionIcon,
        dialogIcon,dialogTitle,dialogContent
    ):

        super().__init__(actionStr,parent)
        self.setStatusTip(actionStatusTip)
        self.triggered.connect(self.showDialog)
        self.setIcon(actionIcon)
        self.dialog = None

        self.dialogIcon = dialogIcon
        self.dialogTitle = dialogTitle
        self.dialogContent = dialogContent

    def showDialog(self):

        self.dialog = QMessageBox(
            self.dialogIcon, self.dialogTitle, self.dialogContent)
        self.dialog.exec_()

    def __parentClose(self):
        try:    self.dialog.close()
        except: pass

class RegisterDialog(QDialog):

    def __init__(self,ID:int,runner:pd.DataFrame):
        super().__init__()

        self.runner = runner

        lblID = QLabel(f"ID: <b>{ID}</b>")
        lblName = QLabel(f"Name: <b>{runner['Name']}</b>")
        note = runner['Note'] if not pd.isna(runner['Note']) else ''
        lblNote = QLabel(f"Note: <b>{note}</b>")
        lblFee = QLabel("Fee:")
        qleFee = QLineEdit()
        qleFee.setMaximumWidth(50)
        qleFee.setValidator(QRegExpValidator(QRegExp("\\d+")))
        qleFee.textChanged.connect(self.changeFee)
        if runner['Note'] == 'EPO':     qleFee.setText('70')
        elif runner['Note'] == 'Late':  qleFee.setText('140')
        else:                           qleFee.setText('90')

        btnCancel = QPushButton(' Cancel',self)
        btnCancel.setIcon(standardIcon('SP_DialogCancelButton'))
        btnCancel.clicked.connect(self.reject)
        btnCancel.setAutoDefault(False)
        btnCancel.setDefault(False)
        btnRegister = QPushButton(' Register',self)
        btnRegister.setIcon(standardIcon('SP_DialogOkButton'))
        btnRegister.clicked.connect(self.accept)
        btnRegister.setAutoDefault(True)
        btnRegister.setDefault(True)


        # Layout ---------------------------------------------------------------

        hboxFee = QHBoxLayout()
        hboxFee.addWidget(lblFee)
        hboxFee.addWidget(qleFee)
        hboxFee.addStretch()

        vboxRunner = QVBoxLayout()
        vboxRunner.addWidget(lblID)
        vboxRunner.addWidget(lblName)
        vboxRunner.addWidget(lblNote)
        vboxRunner.addLayout(hboxFee)

        hboxButtons = QHBoxLayout()
        hboxButtons.addStretch()
        hboxButtons.addWidget(btnCancel)
        hboxButtons.addWidget(btnRegister)

        vbox = QVBoxLayout()
        vbox.addLayout(vboxRunner)
        vbox.addLayout(hboxButtons)

        self.setLayout(vbox)

        # self.setGeometry(150,150,200,200)
        self.setWindowTitle('Runner registration')
        self.adjustSize()
        self.show()

        qleFee.setFocus()

    def changeFee(self,fee_str):

        if isNumber(fee_str):
            self.fee = int(float(fee_str))
        else:
            self.fee = 0

class QuestionDialog(QDialog):

    def __init__(self,question:str,title:str='Question'):
        super().__init__()

        self.setWindowTitle(title)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(question)
        layout.addWidget(message)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

class StatisticsBox(QDialog):

    def __init__(self,df:pd.DataFrame):
        super().__init__()

        reg = df['Registered'].to_numpy()
        reg[pd.isna(reg)] = False
        lblRegistered = QLabel(f"Registered: {np.sum(reg)}/{len(df)}")
        started = np.count_nonzero(~pd.isna(df['Start'].to_numpy()))
        lblStarted = QLabel(f"Started: {started}/{len(df)}")
        finished = np.count_nonzero(~pd.isna(df['Finish'].to_numpy()))
        lblFinished = QLabel(f"Finished: {finished}/{len(df)}")
        lblInForest = QLabel(f"In forest: <b>{started-finished}</b>")

        df = df.sort_values(by=['Score','Time'],ascending=[False,True])
        leaderTime = sec2str(df.iloc[0]['Time']) if not pd.isna(df.iloc[0]['Time']) else '--:--:--'
        lblLeaderTime = QLabel(f"Leader's time: {leaderTime}")
        meanT = sec2str(df['Time'].mean()) if not np.isnan(df['Time'].to_numpy()).all() else '--:--:--'
        lblMeanTime = QLabel(f"Mean time: {meanT}")
        medianT = sec2str(df['Time'].median()) if not np.isnan(df['Time'].to_numpy()).all() else '--:--:--'
        lblMedianTime = QLabel(f"Median time: {medianT}")
        lblTotalFee = QLabel(f"Total fee: {int(df['Fee'].sum())}")

        # Layout ---------------------------------------------------------------
        vbox = QVBoxLayout()
        vbox.addWidget(lblRegistered)
        vbox.addWidget(lblStarted)
        vbox.addWidget(lblFinished)
        vbox.addWidget(lblInForest)
        vbox.addWidget(lblLeaderTime)
        vbox.addWidget(lblMeanTime)
        vbox.addWidget(lblMedianTime)
        vbox.addWidget(lblTotalFee)

        self.setLayout(vbox)
        self.setWindowTitle("Statistics")
        self.show()

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        super(MplCanvas, self).__init__(fig)

class PlotBox(QDialog):

    def __init__(self,df:pd.DataFrame,highlight=None):
        super().__init__()

        sc = MplCanvas(self, width=5, height=4, dpi=100)

        df = df.sort_values(by=['Score','Time'],ascending=[False,True])

        start_wnan = df['Start'].to_numpy()
        finish_wnan = df['Finish'].to_numpy()
        # Remove entries of runners who have not finished yet
        start = start_wnan[np.logical_and(~np.isnan(start_wnan),~np.isnan(finish_wnan))].astype(int)
        finish = finish_wnan[np.logical_and(~np.isnan(start_wnan),~np.isnan(finish_wnan))].astype(int)

        for i in range(len(start)):
            sc.ax1.plot([start[i],finish[i]],[i,i],color='k')
        locs = sc.ax1.get_xticks()
        locs = locs[::2]
        sc.ax1.set_xticks(locs)
        sc.ax1.set_xticklabels([sec2str(t) for t in locs])
        sc.ax1.set_xlabel('Time')
        sc.ax1.set_ylabel('Rank')

        inForestX = np.sort(np.unique(np.concatenate((start,finish))))
        inForestN = np.empty(len(inForestX))

        for i in range(len(start)):
            i1 = np.where(inForestX == start[i])[0][0]
            i2 = np.where(inForestX == finish[i])[0][0]+1
            inForestN[i1:i2] += 1
        sc.ax2.step(inForestX,inForestN,linewidth=2)
        sc.ax2.set_ylabel('Number of people in forest')
        # plt.show()

        vbox = QVBoxLayout()
        vbox.addWidget(sc)
        self.setLayout(vbox)

        self.show()

class EPOGUI(QMainWindow):

    def __init__(self,csv_filepath:str=''):
        super().__init__()
        
        # Dataframe holding all data
        self.df = None

        # Define columns
        self.cols = ['ID','Name','Gender','Start','Finish','Time','Loss','Score','Note','Registered','Fee']

        self.csvFile = csv_filepath
        self.maxScore = 23
        self.leaderTime = None

        # Callback on changing content of the table is called although if it is
        # changed programatically. Therefore `drawingTable` is set to `True`
        # while generating table and to `False` after that. Callback on content
        # change is called only when `drawingTable == False`.
        self.drawingTable = False

        # Start/Finish ---------------------------------------------------------
        self.lblSF = QLabel("Start/Finish")
        self.qleID = QLineEdit()
        self.qleID.setMaximumWidth(50)
        self.qleID.setToolTip(f"Enter runner ID and press enter.\nActivate field by `Esc`.")
        self.qleID.setValidator(QRegExpValidator(QRegExp("\\d+")))
        self.qleID.textChanged.connect(self.qleID_changed)
        self.qleID.returnPressed.connect(self.start_stop)

        self.btnOK = QPushButton(' N/A',self)
        self.btnOK.setObjectName('btn_ok')
        self.btnOK.setMaximumWidth(100)
        self.btnOK.setMinimumWidth(100)
        self.btnOK.setIcon(standardIcon('SP_DialogOkButton'))
        self.btnOK.clicked.connect(self.btnClicked)
        self.btnOK.setEnabled(False)

        self.lblTime = QLabel()
        self.lblTFLS = QLabel("From last start:")
        self.lblTimer = QLabel()
        timer = QTimer(self)
        timer.timeout.connect(self.showTime)
        timer.start(1000)

        self.lblMaxScore = QLabel("Max score:")
        self.qleMaxScore = QLineEdit()
        self.qleMaxScore.setValidator(QRegExpValidator(QRegExp("\\d+")))
        self.qleMaxScore.returnPressed.connect(self.setMaxScore)
        self.qleMaxScore.setMaximumWidth(60)
        self.qleMaxScore.setText(f"{self.maxScore}")

        # New runner -----------------------------------------------------------
        self.lblNewRunner = QLabel("New runner")
        self.qleNewName = QLineEdit()
        self.qleNewName.setToolTip("Runner full name.\nActivate field by `Ctrl+R`.")
        self.qleNewName.returnPressed.connect(self.addRunner)

        self.cmbNewGender = QComboBox()
        self.cmbNewGender.addItems(['M','W'])
        self.cmbNewGender.setToolTip("Gender")
        self.cmbNewGender.setCurrentIndex(0)

        self.qleNewNote = QLineEdit()
        self.qleNewNote.setMaximumWidth(150)
        self.qleNewNote.setToolTip("Arbitrary note")
        self.qleNewNote.returnPressed.connect(self.addRunner)

        self.btnAdd = QPushButton(' Add',self)
        self.btnAdd.setObjectName('btn_add')
        self.btnAdd.setIcon(standardIcon('SP_ArrowForward'))
        self.btnAdd.clicked.connect(self.btnClicked)
        
        # Table menu -----------------------------------------------------------
        self.lblSort = QLabel('Sort by:')
        self.cmbSort = QComboBox()
        self.cmbSort.addItems(['Rank','ID','Name'])
        self.cmbSort.activated[str].connect(self.cmbSortChanged)
        self.sortBy = 'Rank'

        self.lblFilter = QLabel('Filter:')
        self.qleFilter = QLineEdit()
        self.qleFilter.setToolTip("Write part of name or ID.\nActivate field by `Ctrl+F`.\nSelect runner in table by `UP` or `DOWN` key, then press `Enter`.")
        self.qleFilter.textChanged.connect(self.setFilter)
        self.selectedRow = 0
        
        self.btnUpdate = QPushButton(' Update',self)
        self.btnUpdate.setObjectName('btn_update')
        self.btnUpdate.setIcon(standardIcon('SP_BrowserReload'))
        self.btnUpdate.clicked.connect(self.btnClicked)

        # Table ----------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.cols))
        header = self.table.horizontalHeader()
        self.table.setHorizontalHeaderLabels(self.cols)

        header.setSectionResizeMode(self.cols.index('ID'),      QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Name'),    QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(self.cols.index('Gender'),  QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Start'),   QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Finish'),  QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Time'),    QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Loss'),    QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Score'),   QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Note'),    QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(self.cols.index('Registered'),QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.cols.index('Fee'),     QtWidgets.QHeaderView.ResizeToContents)
        self.table.setColumnHidden(self.cols.index('Registered'),True)

        self.table.cellChanged.connect(self.tableCellChanged)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.tableContextMenu)
        
        # Message box ----------------------------------------------------------
        self.msg = ''
        self.qleMsgBox = QTextEdit(self)
        self.qleMsgBox.setMinimumHeight(100)
        self.qleMsgBox.setMaximumHeight(100)
        self.qleMsgBox.setReadOnly(True)

        # Layout ---------------------------------------------------------------
        hboxID = QHBoxLayout()
        hboxID.addWidget(self.lblSF)
        hboxID.addWidget(self.qleID)
        hboxID.addWidget(self.btnOK)
        hboxID.addWidget(self.lblTime)
        hboxID.addWidget(self.lblTFLS)
        hboxID.addWidget(self.lblTimer)
        hboxID.addStretch()
        hboxID.addWidget(self.lblMaxScore)
        hboxID.addWidget(self.qleMaxScore)

        hboxNewRunner = QHBoxLayout()
        hboxNewRunner.addWidget(self.lblNewRunner)
        hboxNewRunner.addWidget(self.qleNewName)
        hboxNewRunner.addWidget(self.cmbNewGender)
        hboxNewRunner.addWidget(self.qleNewNote)
        hboxNewRunner.addWidget(self.btnAdd)

        hboxTabMenu = QHBoxLayout()
        hboxTabMenu.addWidget(self.lblSort)
        hboxTabMenu.addWidget(self.cmbSort)
        hboxTabMenu.addWidget(self.lblFilter)
        hboxTabMenu.addWidget(self.qleFilter)
        hboxTabMenu.addStretch()
        hboxTabMenu.addWidget(self.btnUpdate)

        self.scrlArea = QScrollArea()
        self.scrlArea.setWidget(self.table)
        self.scrlArea.setWidgetResizable(True)
        vboxTable = QVBoxLayout()
        vboxTable.addWidget(self.scrlArea)
        vboxTable.setContentsMargins(0,0,0,0)

        vbox = QVBoxLayout()
        vbox.addLayout(hboxID)
        vbox.addLayout(hboxNewRunner)
        vbox.addLayout(hboxTabMenu)
        vbox.addLayout(vboxTable)
        vbox.addWidget(self.qleMsgBox)

        centralWidget = QWidget()
        centralWidget.setLayout(vbox)
        self.setCentralWidget(centralWidget)

        self.createMenus()

        self.setGeometry(100,100,800,800)
        self.setWindowTitle('EPO OB')
        self.show()

        self.dispMsg("Program started!")

        if self.csvFile:
            self.loadCSV()


    def focusChanged(self,oldWidget,newWidget):
        return
        # Connect this function as following command within `__init__()`
        QApplication.instance().focusChanged.connect(self.focusChanged)
    
    def dispMsg(self,msg,end='\n',fc:QColor=Qt.black,fw:int=QFont.Normal):
        if not isinstance(msg,str): msg = str(msg)
        start = ''
        self.msg += start + msg + end

        self.qleMsgBox.setTextColor(Qt.black)
        self.qleMsgBox.setFontWeight(QFont.Normal)
        self.qleMsgBox.setFontItalic(True)

        self.qleMsgBox.insertPlainText(start)

        self.qleMsgBox.setTextColor(fc)
        self.qleMsgBox.setFontWeight(fw)
        self.qleMsgBox.setFontItalic(False)

        self.qleMsgBox.insertPlainText(msg+end)
        self.qleMsgBox.moveCursor(QTextCursor.End)

    def createMenus(self):

        self.newCSVAct = QAction(
            "&New CSV",
            shortcut = QKeySequence("Ctrl+N"),
            icon=standardIcon('SP_FileIcon'),
            triggered = self.newCSV
        )

        self.openCSVAct = QAction(
            "&Open CSV",
            shortcut = QKeySequence("Ctrl+O"),
            icon = standardIcon('SP_DialogOpenButton'),
            triggered = self.openCSV
        )

        self.saveCSVAct = QAction(
            "&Save CSV",
            shortcut = QKeySequence("Ctrl+S"),
            icon=standardIcon('SP_DriveFDIcon'),
            triggered = self.saveCSV
        )
        
        fileMenu = QMenu("&File",self)
        fileMenu.addAction(self.newCSVAct)
        fileMenu.addAction(self.openCSVAct)
        fileMenu.addAction(self.saveCSVAct)

        self.showStatisticsAct = QAction(
            "Show &statistics",
            self,
            triggered = self.showStatistics,
            icon = qta.icon('ei.align-justify'),
            shortcut = QKeySequence("Ctrl+I")
        )

        self.plotStatisticsAct = QAction(
            "Plot statistics",
            self,
            triggered = self.plotStatistics,
            icon = qta.icon('msc.graph-line'),
            shortcut = QKeySequence("Ctrl+P")
        )

        self.showOutputAct = QAction(
            "Show &output",
            self,
            triggered=self.toggleOutputVisibility,
            shortcut = QKeySequence("Ctrl+M"),
            checkable=True
        )
        self.showOutputAct.setChecked(True)

        self.showAllColumnsAct = QAction(
            "Show all columns",
            self,
            triggered = self.showAllColumns,
            icon = qta.icon('mdi.table-eye')
        )

        viewMenu = QMenu("&View",self)
        viewMenu.addAction(self.showStatisticsAct)
        viewMenu.addAction(self.plotStatisticsAct)
        viewMenu.addAction(self.showOutputAct)
        viewMenu.addAction(self.showAllColumnsAct)

        self.aboutAct = ActionDialog(
            parent=self,
            actionStr='&About',
            actionStatusTip='See information about this program',
            actionIcon=qta.icon('fa5s.info'),
            dialogIcon=QMessageBox.Information,
            dialogTitle="About",
            dialogContent="GitHub: <a href=\"https://github.com/vojtavozda/EPO_OB\">github.com/vojtavozda/EPO_OB</a><br><br>by vovo"
        )

        helpMenu = QMenu("&Help",self)
        helpMenu.addAction(self.aboutAct)

        self.menuBar().addMenu(fileMenu)
        self.menuBar().addMenu(viewMenu)
        self.menuBar().addMenu(helpMenu)

    def btnClicked(self):
        """ Callback connected to buttons """
        sender = self.sender()
        if sender.objectName() == 'btn_ok':
            self.start_stop()
        elif sender.objectName() == 'btn_add':
            self.addRunner()
        elif sender.objectName() == 'btn_update':
            self.updateTable()

    def showTime(self):

        now = datetime.now()
        now = now.hour*3600+now.minute*60+now.second
        self.lblTime.setText(sec2str(now))
        
        if self.df is None or self.df.empty: return

        if pd.isnull(self.df['Start'].to_numpy()).all():
            self.lblTimer.setText('--:--:--')
        else:
            lastStartTime = np.nanmax(self.df['Start'].to_numpy())
            self.lblTimer.setText(sec2str(now-lastStartTime))

    def showStatistics(self):

        dialog = StatisticsBox(self.df)
        dialog.exec()

    def plotStatistics(self):
        dialog = PlotBox(self.df)
        dialog.exec()

    def start_stop(self):

        ID = self.qleID.text()
        try:
            ID = int(self.qleID.text())
        except:
            self.dispMsg("ID must be interger!",fc=Qt.red)
            return

        self.qleID.setText('')

        if ID not in self.df.index:
            self.dispMsg(f'ID {ID} not found!',fc=Qt.red)
            return

        now = datetime.now()
        now = now.hour*3600+now.minute*60+now.second

        start = self.df.loc[ID,'Start']
        name = self.df.loc[ID,'Name']
        if np.isnan(start):
            # Runner not started yet -> start!
            self.df.loc[ID,'Start'] = now
            self.dispMsg(f"{name}",fc=Qt.darkGreen,fw=QFont.Bold,end='')
            self.dispMsg(f' ({ID}) started at {sec2str(now)}',fc=Qt.darkGreen)
        else:

            finish = self.df.loc[ID,'Finish']
            if not np.isnan(finish):
                # Runner is already in finish -> print results
                rank = self.getRank(ID)

                self.dispMsg(f'{name}',fc=Qt.darkYellow,fw=QFont.Bold,end=' ')
                self.dispMsg(f"({ID}) already finished at {sec2str(self.df.loc[ID,'Finish'])}, time =",fc=Qt.darkYellow,end=' ')
                self.dispMsg(f"{sec2str(self.df.loc[ID,'Time'])}",fc=Qt.darkYellow,fw=QFont.Bold,end='')
                self.dispMsg(f', loss =',fc=Qt.darkYellow,end=' ')
                self.dispMsg(f"{sec2str(self.df.loc[ID,'Loss'])}",fc=Qt.darkYellow,fw=QFont.Bold,end='')
                self.dispMsg(f', rank: ',fc=Qt.darkYellow,end='')
                self.dispMsg(f'{rank}',fc=Qt.darkYellow,fw=QFont.Bold)
                return

            # Runner started but not in finish -> finish!
            self.df.loc[ID,'Finish'] = now
            self.df.loc[ID,'Score'] = self.maxScore
            self.updateTimeAndLoss()

            rank = self.getRank(ID)
            self.dispMsg(f'{name}',fc=Qt.blue,fw=QFont.Bold,end=' ')
            self.dispMsg(f'({ID}) finished at {sec2str(now)}, time =',fc=Qt.blue,end=' ')
            self.dispMsg(f"{sec2str(self.df.loc[ID,'Time'])}",fc=Qt.blue,fw=QFont.Bold,end='')
            self.dispMsg(f', loss =',fc=Qt.blue,end=' ')
            self.dispMsg(f"{sec2str(self.df.loc[ID,'Loss'])}",fc=Qt.blue,fw=QFont.Bold,end='')
            self.dispMsg(f', rank: ',fc=Qt.blue,end='')
            self.dispMsg(f'{rank}',fc=Qt.blue,fw=QFont.Bold)

        self.updateTable()
        self.saveCSV()


    def getEmptyID(self):
        """ Return smallest ID which is missing in the dataframe """

        return next(i for i, e in enumerate(sorted(self.df.index.to_list())+[None],1) if i!= e)

    def getRank(self,ID):
        """ Return integer of rank of runner with given ID """

        df = self.df.sort_values(by=['Score','Time'],ascending=[False,True])
        return df.index.get_loc(ID)+1

    def updateLeaderTime(self):
        """ Update `self.leaderTime`: seconds or NaN if nobody in finish """

        # Get dataframe sorted by Score and Time
        df = self.df.sort_values(by=['Score','Time'],ascending=[False,True])
        # Leaders time is the first one
        self.leaderTime = df.iloc[0]['Time']

    def updateTimeAndLoss(self):
        """ Update `Time` and `Loss` """

        # Update time
        self.df['Time'] = self.df['Finish'] - self.df['Start']
        # Update leader time
        self.updateLeaderTime()
        # Update loss
        self.df['Loss'] = self.df['Time'] - self.leaderTime


    def addRunner(self):
        """ Add entry for new runner """

        newName = self.qleNewName.text()
        # Check if `newName` if filled
        if newName=='':
            self.dispMsg('Name must be filled!',fc=Qt.red)
            return
        # Get gender from drop box
        newGender = 'M' if self.cmbNewGender.currentIndex()==0 else 'W'
        # Get note
        newNote = self.qleNewNote.text()

        # if len(self.df) == 0:
        #     # Create new df
        #     pass
        # else:
        # ID is the lowest ID which is not in the table
        newID = self.getEmptyID()
        # Create new dataframe line
        newdf = pd.DataFrame({'Name':newName,'Gender':newGender,'Note':newNote},index=[newID])
        newdf.index.name = 'ID'
        # Concat two dataframes
        self.df = pd.concat([self.df,newdf])

        # Clear text box so it is ready for new entry
        self.qleNewName.setText('')
        self.dispMsg(f"New runner: {newID}, {newName}, {newGender}",fc=Qt.darkGreen)
        # Update table
        self.updateTable()
        # Save CSV
        self.saveCSV()

        # print('Dataframe after adding ==================================')
        # print(self.df)

    def registerRunner(self,ID):
        
        runner = self.df.loc[ID]
        dialog = RegisterDialog(ID,runner)
        if dialog.exec():
            self.df.loc[ID,'Fee'] = dialog.fee
            self.df.loc[ID,'Registered'] = True
            self.updateTable()
            self.saveCSV()
            self.dispMsg(f"Runner ",fc=Qt.darkGreen,end='')
            self.dispMsg(f"{self.df.loc[ID,'Name']} ",fc=Qt.darkGreen,fw=QFont.Bold,end='')
            self.dispMsg(f"({ID}) successfully registered!",fc=Qt.darkGreen)
        else:
            self.dispMsg(f"Registration of runner {self.df.loc[ID,'Name']} ({ID}) cancelled!",fc=Qt.darkYellow)

    def setScore(self,ID):

        score, done = QInputDialog.getInt(self,'Input dialog',f"Set score of runner {self.df.loc[ID,'Name']} ({ID}):")
        if done:
            score = int(score)
            self.dispMsg(f"Score of ",fc=Qt.darkGreen,end='')
            self.dispMsg(f"{self.df.loc[ID,'Name']} ",fc=Qt.darkGreen,fw=QFont.Bold,end='')
            self.dispMsg(f"changed from ",fc=Qt.darkGreen,end='')
            self.dispMsg(f"{int(self.df.loc[ID,'Score'])}",fc=Qt.darkGreen,fw=QFont.Bold,end='')
            self.dispMsg(f" to ",fc=Qt.darkGreen,end='')
            self.dispMsg(f"{score}",fc=Qt.darkGreen,fw=QFont.Bold)
            self.df.loc[ID,'Score'] = score
            self.updateTable()
            self.saveCSV()


    def newCSV(self):
        """ Create new CSV file and redefine `self.csvFile` """

        filename,_ = QFileDialog.getSaveFileName(self, 'New CSV file','','CSV file (*.csv)')
        
        if filename != '' and os.path.splitext(filename)[1]=='.csv':
            self.csvFile = filename
            self.dispMsg(f"New CSV file '{filename}' defined!",fc=Qt.darkGreen)
            # Define empty dataframe
            newcols = self.cols.copy()
            newcols.remove('ID')
            self.df = pd.DataFrame(columns=newcols)
            self.df.index.name = 'ID'
            self.updateTable()
        else:
            self.dispMsg(f"File '{filename}' not created!",fc=Qt.red)
            self.dispMsg(f"Filename should not be empty and must end with '.csv' extension!",fc=Qt.red)

    def openCSV(self):
        """ Define new `self.csvFile` """
        filename,_ = QFileDialog.getOpenFileName(self, 'Select CSV file','',"CSV file (*.csv)")
        if os.path.isfile(filename):
            self.csvFile = filename
            self.dispMsg(f"New CSV file '{filename}' selected!",fc=Qt.darkGreen)
            self.loadCSV()

    def loadCSV(self):
        """ Load CSV file into table """

        if not os.path.isfile(self.csvFile):
            self.dispMsg(f"File '{self.csvFile}' not found!",fc=Qt.red)
            return

        # Clear table
        self.table.setRowCount(0)

        # Load file
        df = pd.read_csv(self.csvFile)

        # Check if file contains all required columns
        if not {'Name'}.issubset(df.columns):
            self.dispMsg(f"CSV file must contain at least following columns: Name",fc=Qt.red)
            return

        if not {'ID'}.issubset(df.columns):
            df['ID'] = np.arange(1,len(df)+1)

        # Set column 'ID' as index
        df = df.set_index('ID')

        # Add missing columns
        for col in self.cols:
            if col != 'ID':
                if not {col}.issubset(df.columns): df[col] = np.nan

        # Convert string times to seconds
        df['Start'] = df['Start'].apply(lambda x: str2sec(x))
        df['Finish'] = df['Finish'].apply(lambda x: str2sec(x))
        df['Fee'] = df['Fee'].apply(lambda x: int(float(x)) if isNumber(x) else np.nan)

        self.df = df
        self.updateTimeAndLoss()

        self.drawTable()

    def saveCSV(self):
        """ Save data from the table into CSV file """

        csvdf = self.getSortedDF(self.df)

        csvdf['Start'] = csvdf['Start'].apply(lambda x: sec2str(x))
        csvdf['Finish'] = csvdf['Finish'].apply(lambda x: sec2str(x))
        csvdf['Time'] = csvdf['Time'].apply(lambda x: sec2str(x))
        csvdf['Loss'] = csvdf['Loss'].apply(lambda x: sec2str(x,add_sign=True))

        csvdf.to_csv(self.csvFile)

        self.saveHTML()

    def saveHTML(self):

        htmlfile = f"{os.path.splitext(self.csvFile)[0]}.html"

        old_sort_by = self.sortBy

        self.sortBy = 'Rank'

        htmldf = self.getSortedDF(self.df)

        htmldf['Start'] = htmldf['Start'].apply(lambda x: sec2str(x))
        htmldf['Finish'] = htmldf['Finish'].apply(lambda x: sec2str(x))
        htmldf['Time'] = htmldf['Time'].apply(lambda x: sec2str(x))
        htmldf['Loss'] = htmldf['Loss'].apply(lambda x: sec2str(x,add_sign=True))
        htmldf.insert(0, 'Rank', range(1, 1 + len(htmldf)))

        htmldf.to_html(
            htmlfile,
            columns=('Rank','Name','Gender','Start','Finish','Time','Loss','Score','Note'),
            index=False,
            )

        try:
            session = ftplib.FTP(
                ftp_credentials.HOST,
                ftp_credentials.USER,
                ftp_credentials.PSWD
            )
            file = open(htmlfile,'rb')                  # file to send
            session.storbinary('STOR epo.html', file)     # send the file
            file.close()                                    # close file and FTP
            session.quit()
        except:
            pass

        self.sortBy = old_sort_by


    def getSortedDF(self,df):

        # Sort dataframe
        if self.sortBy == 'ID':
            df = df.sort_index()
        elif self.sortBy == 'Name':
            df = df.sort_values(by='Name')
        elif self.sortBy == 'Rank':
            df = df.sort_values(by=['Score','Time'],ascending=[False,True])
        else:
            df = self.df

        return df

    def qleID_changed(self,ID:str):

        try:
            ID = int(ID)
        except:
            ID = ''

        if ID not in self.df.index:
            self.btnOK.setText(" N/A")
            self.btnOK.setEnabled(False)
            if ID == '':
                self.drawTable()
            else:
                self.table.setRowCount(0)
            return

        start = self.df.loc[ID,'Start']
        finish = self.df.loc[ID,'Finish']
        if np.isnan(start):
            # Runner not started yet -> start!
            self.btnOK.setText(" START!")
        elif np.isnan(finish):
            # Not finished yet -> finish!
            self.btnOK.setText(" FINISH!")
        else:
            # Runner is already in finish -> print results
            self.btnOK.setText(" PRINT!")
        self.btnOK.setEnabled(True)

        df = self.df.loc[[ID]]
        self.drawTable(df)


    def setMaxScore(self):

        score_str = self.qleMaxScore.text()

        if not score_str.isnumeric():
            return
        else:
            self.dispMsg("Max score is set from ",end='')
            self.dispMsg(f"{self.maxScore}",fw=QFont.Bold,end='')
            self.dispMsg(" to ",end='')
            self.maxScore = int(score_str)
            self.dispMsg(f"{self.maxScore}",fw=QFont.Bold,end='')

    def setFilter(self,filter_str:str):

        if filter_str == '':
            self.drawTable()
            if self.qleFilter.hasFocus():
                self.selectedRow = 0
                self.table.selectRow(self.selectedRow)
        else:

            df = self.df

            if filter_str.isnumeric():
                ID = int(filter_str)
                if ID in self.df.index:
                    df = self.df.loc[[ID]]

            else:
                
                filter_str = filter_str.lower()
                filter_str = unidecode.unidecode(filter_str)

                filter_str = '+.*'.join(filter_str[i] for i in range(0,len(filter_str)))
                filter_str = '.*'+filter_str
                try:        re.compile(filter_str)
                except:     return

                df = self.df.copy()
                df['Name'] = df['Name'].apply(lambda x: x.lower())
                df['Name'] = df['Name'].apply(lambda x: unidecode.unidecode(x))

                df = self.df[df['Name'].str.match(filter_str)]

            self.drawTable(df)

            self.selectedRow = 0
            self.table.selectRow(self.selectedRow)

    def addRow(self,row,id,name,gender,start,finish,time,loss,score,note,registered,fee):

        r = row
        id = str(id)
        start = sec2str(start) if not pd.isna(start) else ''
        finish = sec2str(finish) if not pd.isna(finish) else ''
        time = sec2str(time) if not pd.isna(time) else ''
        score = str(int(float(score))) if not pd.isna(score) else ''
        note = note if not pd.isna(note) else ''
        registered = registered if not pd.isna(registered) else False
        fee = str(int(float(fee))) if not pd.isna(fee) and isNumber(fee) else ''

        if pd.isna(gender): gender = ''

        if not pd.isna(loss):
            sign = '+' if loss>=0 else '-'
            loss = sign + sec2str(np.abs(loss))
        else:
            loss = ''

        self.table.insertRow(r)
        self.table.setRowHeight(r,15)
        self.table.setItem(r,self.cols.index('ID'),QTableWidgetItem(id))
        self.table.setItem(r,self.cols.index('Name'),QTableWidgetItem(name))
        self.table.setItem(r,self.cols.index('Gender'),QTableWidgetItem(gender))
        self.table.setItem(r,self.cols.index('Start'),QTableWidgetItem(start))
        self.table.setItem(r,self.cols.index('Finish'),QTableWidgetItem(finish))
        self.table.setItem(r,self.cols.index('Time'),QTableWidgetItem(time))
        self.table.setItem(r,self.cols.index('Loss'),QTableWidgetItem(loss))
        self.table.setItem(r,self.cols.index('Score'),QTableWidgetItem(score))
        self.table.setItem(r,self.cols.index('Note'),QTableWidgetItem(note))
        self.table.setItem(r,self.cols.index('Registered'),QTableWidgetItem(str(registered)))
        self.table.setItem(r,self.cols.index('Fee'),QTableWidgetItem(fee))

        self.table.item(r,self.cols.index('ID')).setFlags(Qt.ItemIsEnabled)

        bclr = QBrush(QColor(255,255,255))
        if gender == 'M':
            bclr = QBrush(QColor(230,230,255)) if registered else QBrush(QColor(245,245,255))
        elif gender == 'W':
            bclr = QBrush(QColor(255,230,230)) if registered else QBrush(QColor(255,245,245))

        fclr = QBrush(QColor(0,0,0)) if registered else QBrush(QColor(100,100,100))
        for i in range(self.table.columnCount()):
            self.table.item(r,i).setBackground(bclr)
            self.table.item(r,i).setForeground(fclr)

        for i in [0,2,7]:
            self.table.item(r,i).setTextAlignment(Qt.AlignHCenter)

    def drawTable(self,df=None):
    
        if df is None: df = self.df

        start = timer()

        self.drawingTable = True

        # Clear table
        self.table.setRowCount(0)

        df = self.getSortedDF(df)

        # Read dataframe and store data into table
        for r,(i,row) in enumerate(df.iterrows()):

            self.addRow(
                row = r,
                id = i,
                name = row['Name'],
                gender = row['Gender'],
                start = row['Start'],
                finish = row['Finish'],
                time = row['Time'],
                loss = row['Loss'],
                score = row['Score'],
                note = row['Note'],
                registered = row['Registered'],
                fee = row['Fee']
            )

        end = timer()

        self.drawingTable = False

        # self.dispMsg(f"Table drawn in {end-start}")

    def updateTable(self):

        if not self.df.empty:
            self.updateTimeAndLoss()
        self.drawTable()

    def sortTable(self):

        self.drawTable()

    def tableCellChanged(self,row,col):
        """ Callback when any cell is changed (not just manually) """
        
        if self.drawingTable: return

        item = self.table.item(row,col)
        ID = int(self.table.item(row,self.cols.index('ID')).text())

        if col == self.cols.index('ID'):
            self.dispMsg("Manual changing of ID may lead to unexpected behaviour!",fc=Qt.red)

        elif col in [self.cols.index('Name'),self.cols.index('Note')]:
            self.df.loc[ID,self.cols[col]] = item.text()

        elif col == self.cols.index('Gender'):
            if not (item.text()=="M" or item.text()=="W"):
                self.dispMsg("Gender should be 'M' or 'W'!",fc=Qt.darkYellow)
            self.df.loc[ID,self.cols[col]] = item.text()

        elif col in [self.cols.index('Start'),self.cols.index('Finish'),self.cols.index('Time'),self.cols.index('Loss')]:
            if item.text() == '':
                self.df.loc[ID,self.cols[col]] = np.nan
            else:
                time = str2sec(item.text())
                if np.isnan(time):
                    self.dispMsg(f"Unexpected format of time (should be 'HH:MM:SS') not '{item.text()}'!",fc=Qt.red)
                else:
                    self.df.loc[ID,self.cols[col]] = time
        
        elif col == self.cols.index('Score'):
            if item.text() == '':
                self.df.loc[ID,self.cols[col]] = np.nan
            else:
                if not item.text().isnumeric():
                    self.dispMsg(f"Score must be a number! Not '{item.text()}'.",fc=Qt.red)
                else:
                    self.df.loc[ID,self.cols[col]] = float(item.text())
        
        elif col == self.cols.index('Fee'):
            if item.text() == '':
                self.df.loc[ID,self.cols[col]] = np.nan
            else:
                if not item.text().isnumeric():
                    self.dispMsg(f"Fee must be a number! Not '{item.text()}'.",fc=Qt.red)
                else:
                    self.df.loc[ID,self.cols[col]] = float(item.text())

        self.updateTimeAndLoss()
        self.updateTable()
        self.saveCSV()
        
    def tableContextMenu(self,point:QPoint):
        """ Show context menu after right click on table """

        if self.table.rowCount()==0: return

        # Get row and column of clicked cell
        row = self.table.currentRow()
        col = self.table.currentColumn()
        if row<0 or col<0: return
        ID = int(float(self.table.item(row,self.cols.index('ID')).text()))

        # Compose context menu
        menu = QMenu(self)

        # Create actions
        if self.df.loc[ID,'Registered'] == False or pd.isna(self.df.loc[ID,'Registered']):
            registerAct = menu.addAction('&Register')
            uregisterAct = None
        else:
            registerAct = None
            uregisterAct = menu.addAction('Un&register')
        setScoreAct = menu.addAction('Set &score')
        removeAct = menu.addAction('&Delete row')
        hideColAct = menu.addAction('&Hide column')
        showAllColsAct = menu.addAction('Show &all columns')

        # Open context menu and get user answer
        action = menu.exec_(self.table.viewport().mapToGlobal(point))

        if action is None:
            return

        # Perform action according to answer:
        if action == registerAct:
            self.registerRunner(ID)
            
        elif action == uregisterAct:
            self.df.loc[ID,'Registered'] = False
            self.updateTable()
            self.saveCSV()

        elif action == setScoreAct:
            self.setScore(ID)

        elif action == removeAct:
            dialog = QuestionDialog(f"Are you sure you want to remove runner '{self.df.loc[ID,'Name']}'?","Remove runner?")
            if dialog.exec():
                self.dispMsg("Runner ",fc=Qt.red,end='')
                self.dispMsg(self.df.loc[ID,'Name'],fc=Qt.red,fw=QFont.Bold,end='')
                self.dispMsg(" removed!",fc=Qt.red)
                self.df = self.df.drop(ID)
                self.updateTable()
                self.saveCSV()
            else:
                self.dispMsg("Removing cancelled!",fc=Qt.darkYellow)

        elif action == hideColAct:
            self.table.setColumnHidden(col,True)

        elif action == showAllColsAct:
            self.showAllColumns()

    def showAllColumns(self):
        for i in range(self.table.columnCount()):
            if i != self.cols.index('Registered'):
                self.table.setColumnHidden(i,False)

    def cmbSortChanged(self,sortBy):
        self.sortBy = sortBy
        self.sortTable()

    def toggleOutputVisibility(self,setVisible=None):
        if setVisible is not None:
            self.showOutputAct.setChecked(setVisible)
        self.qleMsgBox.setVisible(self.showOutputAct.isChecked())

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:

        if a0.key() == Qt.Key_Escape:
            ID = np.nan
            if self.qleFilter.hasFocus():
                try:
                    row = self.table.selectedItems()[0].row()
                    ID = int(self.table.item(row,self.cols.index('ID')).text())
                except:
                    pass
            self.qleFilter.setText('')
            self.qleID.setText('')
            self.table.clearSelection()
            if not np.isnan(ID):
                df = self.getSortedDF(self.df)
                row = df.index.get_loc(ID)
                self.table.selectRow(row)
            self.qleID.setFocus()

        if a0.key() == Qt.Key_F and a0.modifiers() == Qt.ControlModifier:
            self.selectedRow = 0
            self.table.clearSelection()
            self.qleFilter.setFocus()
            self.table.selectRow(self.selectedRow)

        if (a0.key() == Qt.Key_Down or a0.key() == Qt.Key_Up) and self.qleFilter.hasFocus():
            if a0.key() == Qt.Key_Down:
                self.selectedRow += 1
                if self.selectedRow >= self.table.rowCount():
                    self.selectedRow = 0
            elif a0.key() == Qt.Key_Up:
                self.selectedRow -= 1
                if self.selectedRow < 0:
                    self.selectedRow = self.table.rowCount()-1
            self.table.selectRow(self.selectedRow)

        if a0.key() in [Qt.Key_Enter,Qt.Key_Return] and self.qleFilter.hasFocus():
            ID = int(self.table.item(self.selectedRow,self.cols.index('ID')).text())
            if pd.isna(self.df.loc[ID,'Finish']):
                # Not in finish -> register
                self.registerRunner(ID)
            else:
                # In finish -> change score
                self.setScore(ID)
            self.qleFilter.setText('')

        if a0.key() == Qt.Key_R and a0.modifiers() == Qt.ControlModifier:
            self.selectedRow = 0
            self.table.clearSelection()
            self.qleNewName.setFocus()

        return super().keyPressEvent(a0)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        
        return super().closeEvent(a0)

def main():
    
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Cleanlooks"))
    app.setStyle('Fusion')
    handle = EPOGUI("/home/vovo/Programming/python/EPO_OB/test_event.csv")
    sys.exit(app.exec_())


if __name__ == "__main__":
    """ Run `main()` for standalone execution. """
    try:
        import pyi_splash                               # type: ignore
        pyi_splash.update_text('UI Loaded ...')
        pyi_splash.close()
    except:
        pass
    main()
