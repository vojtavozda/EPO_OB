
from cmath import isnan
from genericpath import isfile
import os
import re
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from timeit import default_timer as timer 

import qtawesome as qta         # run `qta-browser`

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtGui import (QColor, QBrush, QFont, QTextCursor, QRegExpValidator)
from PyQt5.QtCore import (QPoint, Qt, QRegExp)
from PyQt5.QtWidgets import (QAction, QFileDialog, QStyle, QComboBox, QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QStyleFactory, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)


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


class EPOGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        
        # Dataframe holding all data
        self.df = None

        # Define columns
        self.cols = ['ID','Name','Gender','Start','Finish','Time','Loss','Score','Note','Registered','Fee']

        self.csvFile = "/home/vovo/Programming/python/EPO_OB/data.csv"
        self.maxScore = 27
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
        self.qleID.setToolTip(f"Enter runner ID and press enter.\nActivate field by Esc.")
        self.qleID.setValidator(QRegExpValidator(QRegExp("\\d+")))
        self.qleID.returnPressed.connect(self.start_stop)

        self.btnOK = QPushButton(' OK',self)
        self.btnOK.setObjectName('btn_ok')
        self.btnOK.setMaximumWidth(70)
        self.btnOK.setIcon(standardIcon('SP_DialogOkButton'))
        self.btnOK.clicked.connect(self.btnClicked)

        # New runner -----------------------------------------------------------
        self.lblNewRunner = QLabel("New runner")
        self.qleNewName = QLineEdit()
        self.qleNewName.setToolTip("Runner full name")
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
        self.qleFilter.setToolTip("Write part of name")
        self.qleFilter.textChanged.connect(self.setFilter)
        
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
        # self.table.setColumnHidden(self.cols.index('Fee'),True)

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
        hboxID.addStretch()

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

        self.loadCSV()


    
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
            icon=standardIcon('SP_FileIcon'),
            triggered = self.newCSV
        )

        self.openCSVAct = QAction(
            "&Open CSV",
            icon = standardIcon('SP_DialogOpenButton'),
            triggered = self.openCSV
        )

        self.saveCSVAct = QAction(
            "&Save CSV",
            icon=standardIcon('SP_DriveFDIcon'),
            triggered = self.saveCSV
        )
        
        fileMenu = QMenu("&File",self)
        fileMenu.addAction(self.newCSVAct)
        fileMenu.addAction(self.openCSVAct)
        fileMenu.addAction(self.saveCSVAct)

        self.showOutputAct = QAction(
            "Show &output",
            self,
            triggered=self.toggleOutputVisibility,
            checkable=True
        )
        self.showOutputAct.setChecked(True)

        viewMenu = QMenu("&View",self)
        viewMenu.addAction(self.showOutputAct)

        self.aboutAct = ActionDialog(
            parent=self,
            actionStr='&About',
            actionStatusTip='See information about this program',
            actionIcon=qta.icon('fa5s.info'),
            dialogIcon=QMessageBox.Information,
            dialogTitle="About",
            dialogContent='by vovo'
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
            self.dispMsg(f'{name} ({ID}) started at {sec2str(now)}',fc=Qt.darkGreen)
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

    def newCSV(self):
        """ Create new CSV file and redefine `self.csvFile` """

        filename,_ = QFileDialog.getSaveFileName(self, 'New CSV file','','CSV file (*.csv)')
        print(os.path.splitext(filename)[1])
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
        if not {'ID','Name','Gender'}.issubset(df.columns):
            self.dispMsg(f"CSV file must contain at least following columns: ID, Name, Gender",fc=Qt.red)
            return

        # Set column 'ID' as index
        df = df.set_index('ID')

        # Add missing columns
        for col in self.cols:
            if col != 'ID':
                if not {col}.issubset(df.columns): df[col] = np.nan

        # Convert string times to seconds
        df['Start'] = df['Start'].apply(lambda x: str2sec(x))
        df['Finish'] = df['Finish'].apply(lambda x: str2sec(x))

        self.df = df
        self.updateTimeAndLoss()

        self.drawTable()

    def saveCSV(self):
        """ Save data from the table into CSV file """

        csvdf = self.df.copy()
        csvdf['Start'] = csvdf['Start'].apply(lambda x: sec2str(x))
        csvdf['Finish'] = csvdf['Finish'].apply(lambda x: sec2str(x))
        csvdf['Time'] = csvdf['Time'].apply(lambda x: sec2str(x))
        csvdf['Loss'] = csvdf['Loss'].apply(lambda x: sec2str(x,add_sign=True))

        csvdf.to_csv(self.csvFile)


    def setFilter(self,filter_str):

        if filter_str == '':
            self.drawTable()
        else:
            filter_str = '+.*'.join(filter_str[i] for i in range(0,len(filter_str)))
            filter_str = '.*'+filter_str
            filter_str = filter_str.lower()
            print(filter_str)
            try:        re.compile(filter_str)
            except:     return
            df = self.df.copy()
            df['Name'] = df['Name'].apply(lambda x: x.lower())

            df = self.df[df['Name'].str.match(filter_str)]
            self.drawTable(df)

    def addRow(self,row,id,name,gender,start,finish,time,loss,score,note,registered,fee):

        r = row
        id = str(id)
        start = sec2str(start) if not pd.isna(start) else ''
        finish = sec2str(finish) if not pd.isna(finish) else ''
        time = sec2str(time) if not pd.isna(time) else ''
        score = str(int(float(score))) if not pd.isna(score) else ''
        note = note if not pd.isna(note) else ''
        registered = registered if not pd.isna(registered) else False
        fee = str(fee) if not pd.isna(fee) else ''

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
            bclr = QBrush(QColor(230,230,255))
        elif gender == 'W':
            bclr = QBrush(QColor(255,230,230))

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

        # Sort dataframe
        if self.sortBy == 'ID':
            df = df.sort_index()
        elif self.sortBy == 'Name':
            df = df.sort_values(by='Name')
        elif self.sortBy == 'Rank':
            df = df.sort_values(by=['Score','Time'],ascending=[False,True])

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

        self.drawTable()

    def sortTable(self):

        self.drawTable()

    def tableCellChanged(self,row,col):
        """ Callback when any cell is changed (not just manually) """
        
        if self.drawingTable: return

        item = self.table.item(row,col)
        print(row,col,item.text())
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
            time = str2sec(item.text())
            if np.isnan(time):
                self.dispMsg(f"Unexpected format of time (should be 'HH:MM:SS') not '{item.text()}'!",fc=Qt.red)
            else:
                self.df.loc[ID,self.cols[col]] = time
        
        elif col == self.cols.index('Score'):
            if not item.text().isnumeric():
                self.dispMsg(f"Score must be a number! Not '{item.text()}'.",fc=Qt.red)
            else:
                self.df.loc[ID,self.cols[col]] = float(item.text())
        
        elif col == self.cols.index('Fee'):
            if not item.text().isnumeric():
                self.dispMsg(f"Fee must be a number! Not '{item.text()}'.",fc=Qt.red)
            else:
                self.df.loc[ID,self.cols[col]] = float(item.text())

        # self.qleFilter.setText('')

        self.updateTimeAndLoss()
        self.updateTable()
        self.saveCSV()
        
    def tableContextMenu(self,point:QPoint):
        """ Show context menu after right click on table """

        if self.table.rowCount()==0: return

        # Get row and column of clicked cell
        row = self.table.currentRow()
        col = self.table.currentColumn()
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
        removeAct = menu.addAction('&Delete row')

        # Open context menu and get user answer
        action = menu.exec_(self.table.viewport().mapToGlobal(point))

        # Perform action according to answer:
        if action == registerAct:
            # TODO: Call `self.register(ID)` here, ask for price
            self.df.loc[ID,'Registered'] = True
            self.updateTable()
            self.saveCSV()
        elif action == uregisterAct:
            self.df.loc[ID,'Registered'] = False
            self.updateTable()
            self.saveCSV()
        elif action == removeAct:
            self.df = self.df.drop(ID)
            self.updateTable()
            self.saveCSV()

    def cmbSortChanged(self,sortBy):
        self.sortBy = sortBy
        self.sortTable()

    def toggleOutputVisibility(self,setVisible=None):
        if setVisible is not None:
            self.showOutputAct.setChecked(setVisible)
        self.qleMsgBox.setVisible(self.showOutputAct.isChecked())

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key_Escape:
            self.qleFilter.setText('')
            self.table.clearSelection()
            self.qleID.setFocus()

        if a0.key() == Qt.Key_F and a0.modifiers() == Qt.ControlModifier:
            self.table.clearSelection()
            self.qleFilter.setFocus()

        if a0.key() == Qt.Key_Down and self.qleFilter.hasFocus():
            self.table.setFocus()

        return super().keyPressEvent(a0)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        
        return super().closeEvent(a0)

def main():
    
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Cleanlooks"))
    app.setStyle('Fusion')
    handle = EPOGUI()
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
