
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
    
    if time_str == '': return None

    try:
        h,m,s = time_str.split(':')
        sec = int(h)*3600 + int(m)*60 + int(s)
        if '-' in time_str: sec = -sec
        return sec
    except:
        return None

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

        #             0    1      2        3       4        5      6      7      8      9      10
        self.cols = ('ID','Name','Gender','Start','Finish','Time','Loss','Score','Note','Reg.','Fee')
        
        # Dataframe holding all data
        self.df = None

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
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(self.cols)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode( 0,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 1,QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode( 2,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 3,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 4,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 5,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 6,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 7,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode( 8,QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode( 9,QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10,QtWidgets.QHeaderView.ResizeToContents)
        self.table.setColumnHidden(9,True)
        self.table.setColumnHidden(10,True)
        
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

        IDs = list()
        scores = list()
        times = list()

        for r in range(self.table.rowCount()):
            # Get runner's time
            sec = str2sec(self.table.item(r,5).text())
            if sec is not None:
                # Store time only if present
                times.append(sec)
                IDs.append(int(self.table.item(r,0).text()))
                score = self.table.item(r,7).text()
                if score != '':
                    scores.append(int(float(score)))
                else:
                    scores.append(0)

        if len(times) == 0:
            self.leaderTime = None
        else:
            data = list(zip(IDs,scores,times))
            df = pd.DataFrame(data,columns=['ID','Score','Time'])
            df = df.sort_values(by=['Score','Time'],ascending=[False,True])

            return df.index[df['ID']==ID].tolist()[0]+1

    def updateLeaderTime(self):
        """ Updates `self.leaderTime` (string) or `None` if nobody in finish """

        df = self.df.sort_values(by=['Score','Time'],ascending=[False,True])

        print("udpate")
        print(df)

        scores = list()
        times = list()

        for r in range(self.table.rowCount()):
            # Get runner's time
            sec = str2sec(self.table.item(r,5).text())
            if sec is not None:
                # Store time only if present
                times.append(sec)
                score = self.table.item(r,7).text()
                if score != '':
                    scores.append(int(float(score)))
                else:
                    scores.append(0)

        if len(times) == 0:
            self.leaderTime = None
        else:
            scores = np.array(scores)
            times = np.array(times)
            times = times[scores==np.max(scores)]
            self.leaderTime = sec2str(np.min(times))

    def updateTimeAndLoss(self):
        """ Update `Time` and `Loss` """

        # Step 1: Update all times
        for i,row in self.df.iterrows():
            start = row['Start']
            finish = row['Finish']
            time = finish-start if start is not None and finish is not None else None
            self.df.iloc[i,self.cols.index('Time')] = time

        # Step 2: Update loss
        self.updateLeaderTime()
        if self.leaderTime is not None:
            for r in range(self.table.rowCount()):
                time = self.table.item(r,5).text()
                if time != '':
                    loss = self.getLoss(time)
                    # loss = '+'+diff_times(leaderTime,time)
                    self.table.item(r,6).setText(loss)
                else:
                    self.table.item(r,6).setText('')

        self.saveCSV()

    def updateTable(self):

        self.saveCSV()
        self.loadCSV()

    def sortTable(self):

        self.saveCSV()
        self.loadCSV()


    def addRow(self,r,ID,name,gender,start,finish,time,loss,score,note,reg,fee):

        if time != '' and score == '': score = 0
        if score != '':
            score = str(int(float(score)))

        reg = reg if reg != '' else False

        self.table.insertRow(r)
        self.table.setRowHeight(r,15)
        self.table.setItem(r, 0,QTableWidgetItem(str(ID)))
        self.table.setItem(r, 1,QTableWidgetItem(str(name)))
        self.table.setItem(r, 2,QTableWidgetItem(str(gender)))
        self.table.setItem(r, 3,QTableWidgetItem(str(start)))
        self.table.setItem(r, 4,QTableWidgetItem(str(finish)))
        self.table.setItem(r, 5,QTableWidgetItem(str(time)))
        self.table.setItem(r, 6,QTableWidgetItem(str(loss)))
        self.table.setItem(r, 7,QTableWidgetItem(str(score)))
        self.table.setItem(r, 8,QTableWidgetItem(str(note)))
        self.table.setItem(r, 9,QTableWidgetItem(str(reg)))
        self.table.setItem(r,10,QTableWidgetItem(str(fee)))

        clr = None
        if gender == 'M':
            clr = QBrush(QColor(230,230,255))
        elif gender == 'W':
            clr = QBrush(QColor(255,230,230))
        if clr is not None:
            for i in range(9):
                self.table.item(r,i).setBackground(clr)

        for i in [0,2,7]:
            self.table.item(r,i).setTextAlignment(Qt.AlignHCenter)

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

        # Check if file contains all columns
        if not {'ID','Name','Gender','Start','Finish','Time','Loss','Score','Note','Reg.','Fee'}.issubset(df.columns):
            self.dispMsg(f"CSV file must contain following columns: ID,Name,Gender,Start,Finish,Time,Loss,Score,Note,Reg.,Fee",fc=Qt.red)
            return

        self.df = df

        for i,row in self.df.iterrows():
            # Change strings to seconds
            self.df.iloc[i,self.cols.index('Start')] = str2sec(row['Start'])
            self.df.iloc[i,self.cols.index('Finish')]= str2sec(row['Finish'])
            self.df.iloc[i,self.cols.index('Time')]  = str2sec(row['Time'])
            self.df.iloc[i,self.cols.index('Loss')]  = str2sec(row['Loss'])

        print(self.df)

        self.updateTimeAndLoss()

        # self.drawTable()

        


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
        df = pd.DataFrame(data,columns=['ID','Name','Gender','Start','Finish','Time','Loss','Score','Note','Reg.','Fee'])
        df.to_csv(self.csvFile,index=False)

    def drawTable(self):
        return
    
        # Sort dataframe
        if self.sortBy == 'ID':
            df = df.sort_values(by='ID')
        elif self.sortBy == 'Name':
            df = df.sort_values(by='Name')
        elif self.sortBy == 'Rank':
            df = df.sort_values(by=['Score','Time'],ascending=[False,True])

        # Read file and store data into table
        for r,(i,row) in enumerate(df.iterrows()):
            start = row['Start'] if not pd.isnull(row['Start']) else ''
            finish = row['Finish'] if not pd.isnull(row['Finish']) else ''
            score = row['Score'] if not pd.isnull(row['Score']) else ''
            note = row['Note'] if not pd.isnull(row['Note']) else ''
            reg = row['Reg.'] if not pd.isnull(row['Reg.']) else ''
            fee = row['Fee'] if not pd.isnull(row['Fee']) else ''

            self.addRow(r,row['ID'],row['Name'],row['Gender'],start,finish,'','',score,note,reg,fee)        

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
