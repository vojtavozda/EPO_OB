
from genericpath import isfile
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

import qtawesome as qta         # run `qta-browser`

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtGui import (QColor, QBrush, QFont, QTextCursor, QRegExpValidator)
from PyQt5.QtCore import (QPoint, Qt, QRegExp)
from PyQt5.QtWidgets import (QAction, QFileDialog, QStyle, QComboBox, QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QStyleFactory, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)


def str2sec(time_str:str):
    
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

def sec2str(seconds:int):

    m, s = divmod(seconds,60)
    h, m = divmod(m,60)
    return '%02d:%02d:%02d'%(h,m,s)

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
        self.table.setColumnHidden(self.cols.index('Fee'),True)

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

        return

        row = None
        for r in range(self.table.rowCount()):
            rID = int(self.table.item(r,0).text())
            if rID == ID:
                row = r
                break
        if row is None:
            self.dispMsg(f'ID {ID} not found!',fc=Qt.red)
            return

        now = datetime.now()
        now = sec2str(now.hour*3600+now.minute*60+now.second)
        start = self.table.item(row,3).text()
        name = self.table.item(row,1).text()
        if start=='':
            self.table.item(row,3).setText(now)
            self.dispMsg(f'{name} ({ID}) started at {now}',fc=Qt.darkGreen)
            self.saveCSV()
        else:
            
            finish = self.table.item(row,4).text()
            
            if finish != '':
                time = diff_times(start,now)
                loss = self.getLoss(time)
                rank = self.getRank(ID)

                self.dispMsg(f'{name}',fc=Qt.darkYellow,fw=QFont.Bold,end=' ')
                self.dispMsg(f'({ID}) already finished at {now}, time =',fc=Qt.darkYellow,end=' ')
                self.dispMsg(f'{time}',fc=Qt.darkYellow,fw=QFont.Bold,end='')
                self.dispMsg(f', loss =',fc=Qt.darkYellow,end=' ')
                self.dispMsg(f'{loss}',fc=Qt.darkYellow,fw=QFont.Bold,end='')
                self.dispMsg(f', rank: ',fc=Qt.darkYellow,end='')
                self.dispMsg(f'{rank}',fc=Qt.darkYellow,fw=QFont.Bold)
                return

            # Store time
            self.table.item(row,4).setText(now)
            time = diff_times(start,now)
            loss = self.getLoss(time)
            self.table.item(row,5).setText(time)
            self.table.item(row,6).setText(loss)
            self.table.item(row,7).setText(str(self.maxScore))

            if self.leaderTime is None:
                # First runner in finish -> new leader time
                self.updateTimeAndLoss()
            elif str2sec(time) < str2sec(self.leaderTime):
                # New leading runner
                self.updateTimeAndLoss()

            if self.sortBy == 'Rank':
                self.sortTable()
            else:
                self.saveCSV()

            rank = self.getRank(ID)
            self.dispMsg(f'{name}',fc=Qt.blue,fw=QFont.Bold,end=' ')
            self.dispMsg(f'({ID}) finished at {now}, time =',fc=Qt.blue,end=' ')
            self.dispMsg(f'{time}',fc=Qt.blue,fw=QFont.Bold,end='')
            self.dispMsg(f', loss =',fc=Qt.blue,end=' ')
            self.dispMsg(f'{loss}',fc=Qt.blue,fw=QFont.Bold,end='')
            self.dispMsg(f', rank: ',fc=Qt.blue,end='')
            self.dispMsg(f'{rank}',fc=Qt.blue,fw=QFont.Bold)



    def getEmptyID(self):
        """ Return smallest ID which is missing in the table """
        
        IDs = list()
        for r in range(self.table.rowCount()):
            IDs.append(int(self.table.item(r,0).text()))

        # Return smallest missing number
        return next(i for i, e in enumerate(sorted(IDs)+[None],1) if i != e)

    def getLoss(self,time:str):
        """ Return loss (str) to the leader """

        leaderTime = self.leaderTime
        if leaderTime is None: leaderTime = time
        if str2sec(leaderTime) <= str2sec(time):
            return '+'+diff_times(leaderTime,time)
        else:
            return '-'+diff_times(time,leaderTime)
        # r1 = times.index(min(times)) 

    def getRank(self,ID):
        """ int """

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

    def updateTable(self):

        self.saveCSV()
        self.loadCSV()

    def sortTable(self):

        self.saveCSV()
        self.loadCSV()


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
        # ID is the lowest ID which is not in the table
        newID = self.getEmptyID()
        # Apend row to the end of the table
        r = self.table.rowCount()
        self.addRow(r,newID,newName,newGender,'','','','','',newNote,'','')
        # Clear text box so it is ready for new entry
        self.qleNewName.setText('')
        self.dispMsg(f"New runner: {newID}, {newName}, {newGender}",fc=Qt.darkGreen)
        # Save CSV in case of sudden crash
        self.saveCSV()

        if self.sortBy == 'Name' or self.sortBy == 'ID':
            self.sortTable()

    def newCSV(self):
        """ Create new CSV file and redefine `self.csvFile` """
        filename,_ = QFileDialog.getSaveFileName(self, 'New CSV file','','CSV file (*.csv)')
        print(os.path.splitext(filename)[1])
        if filename != '' and os.path.splitext(filename)[1]=='.csv':
            self.csvFile = filename
            self.dispMsg(f"New CSV file '{filename}' defined!",fc=Qt.darkGreen)
            self.table.setRowCount(0)
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

        ID = list()
        name = list()
        gender = list()
        start = list()
        finish = list()
        time = list()
        loss = list()
        score = list()
        note = list()
        reg = list()
        fee = list()
        for r in range(self.table.rowCount()):
            ID.append(self.table.item(r,0).text())
            name.append(self.table.item(r,1).text())
            gender.append(self.table.item(r,2).text())
            start.append(self.table.item(r,3).text())
            finish.append(self.table.item(r,4).text())
            time.append(self.table.item(r,5).text())
            loss.append(self.table.item(r,6).text())
            score.append(self.table.item(r,7).text())
            note.append(self.table.item(r,8).text())
            reg.append(self.table.item(r,9).text())
            fee.append(self.table.item(r,10).text())


        data = list(zip(ID,name,gender,start,finish,time,loss,score,note,reg,fee))
        df = pd.DataFrame(data,columns=self.cols)
        df.to_csv(self.csvFile,index=False)



    def addRow(self,row,id,name,gender,start,finish,time,loss,score,note,registered,fee):

        r = row
        id = str(id)
        start = sec2str(start) if not np.isnan(start) else ''
        finish = sec2str(finish) if not np.isnan(finish) else ''
        time = sec2str(time) if not np.isnan(time) else ''
        score = str(int(float(score))) if not np.isnan(score) else ''
        note = note if not np.isnan(note) else ''
        registered = registered if not np.isnan(registered) else False
        fee = str(fee) if not np.isnan(fee) else ''

        if not np.isnan(loss):
            sign = '+' if loss>=0 else '-'
            loss = sign + sec2str(np.abs(loss))
        else:
            loss = ''

        self.table.insertRow(r)
        self.table.setRowHeight(r,15)
        self.table.setItem(r, 0,QTableWidgetItem(id))
        self.table.setItem(r, 1,QTableWidgetItem(name))
        self.table.setItem(r, 2,QTableWidgetItem(gender))
        self.table.setItem(r, 3,QTableWidgetItem(start))
        self.table.setItem(r, 4,QTableWidgetItem(finish))
        self.table.setItem(r, 5,QTableWidgetItem(time))
        self.table.setItem(r, 6,QTableWidgetItem(loss))
        self.table.setItem(r, 7,QTableWidgetItem(score))
        self.table.setItem(r, 8,QTableWidgetItem(note))
        self.table.setItem(r, 9,QTableWidgetItem(str(registered)))
        self.table.setItem(r,10,QTableWidgetItem(fee))

        bclr = QBrush(QColor(255,255,255))
        if gender == 'M':
            bclr = QBrush(QColor(230,230,255))
        elif gender == 'W':
            bclr = QBrush(QColor(255,230,230))

        fclr = QBrush(QColor(0,0,0)) if registered else QBrush(QColor(100,100,100))
        for i in range(9):
            self.table.item(r,i).setBackground(bclr)
            self.table.item(r,i).setForeground(fclr)

        for i in [0,2,7]:
            self.table.item(r,i).setTextAlignment(Qt.AlignHCenter)

    def drawTable(self):
    
        # Clear table
        self.table.setRowCount(0)

        # Sort dataframe
        if self.sortBy == 'ID':
            df = self.df.sort_index()
        elif self.sortBy == 'Name':
            df = self.df.sort_values(by='Name')
        elif self.sortBy == 'Rank':
            df = self.df.sort_values(by=['Score','Time'],ascending=[False,True])

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

    def tableCellChanged(self,row,col):
        """ Callback when any cell is changed (not just manually) """
        
        # item = self.table.item(row,col)
        # if col == 0:
        #     self.dispMsg("You should not change ID manually!",fc=Qt.red)
        # elif col == 3:
        #     if item.text() != "M" or item.text() != "W":
        #         self.dispMsg("Gender should be 'M' or 'W'!",fc=Qt.darkYellow)
        # elif col == 7:
        #     if self.sortBy == 'Rank': self.sortTable()
        
    def tableContextMenu(self,point:QPoint):
        """ Show context menu after right click on table """

        if self.table.rowCount()==0: return

        # Get row and column of clicked cell
        row = self.table.currentRow()
        col = self.table.currentColumn()

        # Compose context menu
        menu = QMenu(self)

        # Create actions
        removeAct = menu.addAction('&Delete row')

        # Open context menu and get user answer
        action = menu.exec_(self.table.viewport().mapToGlobal(point))

        # Perform action according to answer:
        if action == removeAct:
            self.table.removeRow(row)
            self.updateTable()

    def cmbSortChanged(self,sortBy):
        self.sortBy = sortBy
        self.sortTable()

    def toggleOutputVisibility(self,setVisible=None):
        if setVisible is not None:
            self.showOutputAct.setChecked(setVisible)
        self.qleMsgBox.setVisible(self.showOutputAct.isChecked())

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key_Escape:
            self.qleID.setFocus()

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
