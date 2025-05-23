#!/usr/bin/env python3
"""Table view of process variables from EPICS and liteServer infrastructures"""
__version__= 'v3.1.0 2025-05-08'# save/resore is working, pushbutton style, pargs.instance 

#TODO: If tabs are with different namespaces, then only one gets updated 
#TODO: embedding works on Raspberry and Lubuntu but not on RedHat
#TODO: If connection is restored, subscribtion times out

import os, threading, subprocess, sys, time, math
timer = time.perf_counter
from datetime import datetime
from qtpy import QtWidgets as QW, QtGui, QtCore
from qtpy.QtWidgets import QApplication, QFileDialog
from pyqtgraph import SpinBox
import numpy as np
import traceback
from functools import partial
from os import system as os_system, environ as os_environ

from . import detachable_tabs

try:    Browser = os_environ["BROWSER"]
except: Browser = 'firefox'

#``````````````````Globals````````````````````````````````````````````````````
AppName = 'pypet'
DefaultNamespace = 'EPICS'

Process_data_Lock = threading.Lock()# it has no effect
pargs = None
EventExit = threading.Event()
DataDeliveryModes = {'Asynchronous':0., 'Stopped':0., 'Polling 1 s':1.,
    'Polling 0.1 s':0.1, 'Polling 0.01 s':0.01, 'Polling 0.001 s':0.001,
    'Polling 10 s':10., 'Polling 1 min':60.}
StyleSheet_darkBackground = 'background-color: rgb(120, 120, 0); color: white'
StyleSheet_lightBackground = 'background-color: white; color: black'
Win = None
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#````````````````````````````Helper functions`````````````````````````````````
programStartTime = time.time()
def timeInProgram():
    return round(time.time() - programStartTime,6)
def printw(msg): 
    print(f'WRN.PP@{timeInProgram()}: '+msg)
    if Win: Win.update_statusBar('WRN:'+msg)
def printe(msg):
    print(f'ERR.PP@{timeInProgram()}: '+msg)
    if Win: Win.update_statusBar('ERR:'+msg)
def printi(msg): print(f'INF.PP@{timeInProgram()}: '+msg)
def printv(msg):
    try:
        if pargs.verbose: print(croppedText('PP.DBG0:'+str(msg)))
    except: pass
def printvv(msg):
        if pargs.verbose > 1: print(croppedText('PP.DDB1:'+str(msg)))

def croppedText(txt, limit=200):
    if len(txt) > limit:
        txt = txt[:limit]+'...'
    return txt

def iterable(values):
    """Return iterables of any values"""
    if isinstance(values, str):
        return [values]
    try:
        if len(values) == 0:
            values = [values]
    except: values = [values]
    return values  

def v2t(values, l=60, fmt=None):
    """Pretty text from numerical values"""
    suffix = '...'
    if isinstance(values, str):
        v = values
    else:
        values = iterable(values)
        r = []
        if fmt is None:
            fmt = '%.4g'
        for i in values:
            r.append(fmt%i if isinstance(i,float) else str(i))
        v = ', '.join(r)
    lv = len(v)
    return v if lv < l else v[:l]+'...' 

def t2v(txt, dtype):
    """convert text to array of numbers"""
    numbers = {
        'CharType': int,
        'UCharType': int,
        'ShortType': int,
        'UShortType': int,
        'LongType': int,
        'ULongType': int,
        'FloatType': float,
        'DoubleType': float,
        #'StringType': string,
        #BlobType': bytes,
        'IntType': int,
        'UIntType': int,
    }
    if dtype not in numbers:
        return txt
    try:
        v = [numbers[dtype](i) for i in txt.split(',')]
    except Exception as e:
        msg = f't2v: Cannot convert {txt} to values, {e}'
        raise ValueError(msg)
    return v

def select_files_interactively(directory, title='Select a *_pp.py file'):
    #print(f'select_files_interactively:{directory}')
    abspath = os.path.abspath(directory)
    dialog = QFileDialog()
    dialog.setFileMode( QFileDialog.FileMode() )
    ffilter = 'pypet (*_pp.py)'
    files = dialog.getOpenFileNames( None, title, abspath, ffilter)[0]
    r = []
    for file in files:
        relativeName = file.replace(abspath+'/', '')
        r.append(relativeName[:-3])# remove .py
    return r

def pvplot(devPars, plotType=None, dialog=None):
    """Plot device:parameters using pvplot app"""
    #print(f'pvplot: {devPars, plotType}')
    # prefix devPars for LITE and EPICS namespace
    prefix = {'EPICS':'E:', 'PVA':'P:', 'LITE':'L:'}
    ns = get_namespace()
    #printi(f'namespace:{ns}, {prefix.get(ns,"")}')
    devPars = [prefix.get(ns,'')+i for i in devPars]
    delimiter = ',' if plotType == 'Correlation' else ' '
    #subprocCmd = ['pvplot', delimiter.join(devPars)]
    subprocCmd = ['python3', '-m', 'pvplot', delimiter.join(devPars)]
    printi(f'Executing: `{" ".join(subprocCmd)}`')
    # the following does not work as hoovering in menu area clears the statusBar
    #Win.update_statusBar(msg)
    subprocess.Popen(subprocCmd, stdout=subprocess.PIPE)
    if dialog:  dialog.accept()

def get_namespace():
    """Retrieve namespace (EPICS, PVA or LITE from configuation"""
    return currentDaTable().pypage.namespace.upper()

def rgbColorCode(text):
    """Return color code, associated with three first letters of the text"""
    colorDict = {'ERR':[255,170,170], 'UNK':[255,170,170], 'WAR':[255,255,150],
    '?':[231,157,237]}
    color = colorDict.get(text[:3])
    if not color: color = [255,255,255]
    return color

def split_slice(parNameSlice):
    """Decode 'name[n1:n2]' to 'name',[n1:n2]"""
    devParSlice = parNameSlice.split('[',1)
    if len(devParSlice) < 2:
        return devParSlice[0], None
    sliceStr = devParSlice[1].replace(']','')
    vrange = sliceStr.split(':',1)
    r0 = int(vrange[0])
    if len(vrange) == 1:
        vslice = (r0, r0+1)
    else:
        vslice = (r0, int(vrange[1]))
    #print(f'vslice: {vslice}')
    return devParSlice[0], vslice

def configColor(color):
    """Convert color from config file to QColor"""
    c = QtGui.QColor(*color) if isinstance(color,(list,tuple))\
      else QtGui.QColor(color)
    return c

def mkColor(color):
    if color is None:
        #color = 'lightCyan'
        color = [240,240,240]
    return 'rgb(%i,%i,%i)'%tuple(color)\
          if isinstance(color,list) else str(color)

#``````````````````Custom widgets`````````````````````````````````````````````
#class QDoubleSpinBoxDAO(QW.QDoubleSpinBox):
class QDoubleSpinBoxDAO(SpinBox):
    """Spinbox associated with the Data Access Object.
    Inherited from pyqtgraph, which has useful features:
    - it does not react on frequent changes,
    - units are shown,
    - smart nudging.
    """ 
    def __init__(self, dao, color=None):
        super().__init__()
        self.dao = dao
        self.lastValue = None
        ivalue = self.dao.attr['value']
        try:    ivalue = ivalue[0]
        except: pass
        bounds = self.dao.attr.get('opLimits')
        if not bounds:  bounds = (None, None)
        self.integer = isinstance(ivalue, int)
        printv(f'QDoubleSpinBoxDAO {self.dao.name} int:{self.integer}, {ivalue}')
        #self.valueChanged.connect(self.do_action)
        self.editingFinished.connect(self.do_action)
        #self.sigValueChanged.connect(self.do_action)
        units = self.dao.attr.get('units')
        units = ' ' + units if units else ''
        self.setOpts(dec=True, int=self.integer, suffix=units,
          decimals=6, bounds=bounds)
        if not self.integer and ivalue == 0.:
            self.setOpts(minStep=0.01)
        self.setButtonSymbols(QW.QAbstractSpinBox.NoButtons)
        c = mkColor(color)
        self.setStyleSheet(f'color:darkblue;min-height:14px;background-color:{c}')#; font-weight: bold;')
                    
    def contextMenuEvent(self, event):
        # we don't need its contextMenu (activated on right click)
        printv(f'RightClick at spinbox {self.dao.name}')
        Win.rightClick(self.dao)

    def do_action(self):
        locked = Process_data_Lock.locked()
        idle = locked or DataAccessMonitor.currentDeliveryMode == 'Stopped'
        #printv(f'data delivery: {DataAccessMonitor.currentDeliveryMode}')
        printv(f'>do_action {idle,locked,pargs.readonly,self.dao.name}')
        if idle:
            # do not execute set() during initialization.
            return
        widgetValue = self.value()
        if self.integer:
            widgetValue = int(widgetValue)
        if widgetValue == self.lastValue:
            return
        r = self.dao.set(widgetValue)
        if not r:
            printw(f'Could not set {self.dao.name} {widgetValue}')
            if isinstance(self.lastValue,(list,tuple)):
                #printw('DoubleSpinbox value is iterable (lite issue)?)')
                self.lastValue = self.lastValue[0]
            self.setValue(self.lastValue)
        else:
            self.lastValue = widgetValue        

    def wheelEvent(self, event):
        event.ignore()

class QComboBoxDAO(QW.QComboBox):
    """ComboBox associated with the Data Access Object""" 
    def __init__(self, dao):
        super().__init__()
        self.setEditable(True)
        self.dao = dao
        try:    v = self.dao.attr['value'][0]
        except: v = self.dao.attr['value']
        self.lastValue = v
        printv(f'QComboBoxDAO {self.dao.name}')
        lvs = dao.attr['legalValues']
        if lvs:
            for lv in lvs:
                self.addItem(str(lv))
        self.activated[str].connect(self.onComboChanged)

    def onComboChanged(self,txt):
        if self.dao.set(txt):
            #printi('combo changed '+txt)
            self.lastValue = txt
        else:
            printv(f'lastValue: {self.lastValue}')
            self.lineEdit().setText(self.lastValue)

    def setText(self,txt):
        #print(f'combo {self.dao.name} set to {txt}')
        self.lineEdit().setText(txt)

    def contextMenuEvent(self,event):
        #print(f'RightClick at comboBox {self.dao.name}')
        Win.rightClick(self.dao)

    def wheelEvent(self, event):
        event.ignore()
    
class QLineEditDAO(QW.QLineEdit):
    """LineEdit associated with the Data Access Object""" 
    def __init__(self,dao):
        super().__init__()
        # the following does not work if text overflows the cell
        QW.QLineEdit.setAlignment(self, QtCore.Qt.AlignLeft)
        self.dao = dao
        printv(f'QLineEditDAO {self.dao.name}')
        self.returnPressed.connect(self.handle_value_changed)

    def setText(self, txt):
        lineEdit = QW.QLineEdit
        color = rgbColorCode(txt)
        lineEdit.setText(self, txt)
        self.setStyleSheet(f'background-color: rgb{tuple(color)};')

    def handle_value_changed(self):
        txt = self.text()
        dtype = self.dao.attr.get('type')
        printv(f'lineedit changed to {txt}, expect {dtype}')
        try:
            v = t2v(txt,dtype)
            r = self.dao.set(v)
        except Exception as e:
            msg = f'Cannot set {self.dao.name} to {dtype} of {txt}'
            Win.update_statusBar(msg)
            r = False
        #if r: return value back

    def contextMenuEvent(self,event):
        if self.hasSelectedText():
            QW.QLineEdit.contextMenuEvent(self,event)
        else:
            #print(f'RightClick at lineEdit {self.dao.name}')
            Win.rightClick(self.dao)

class QPushButtonDAO(QW.QPushButton):
    """PushButton associated with the Data Access Object""" 
    def __init__(self, dao, text=None):
        super().__init__()
        self.dao = dao
        if not text:
            #text = self.dao.parName
            text = self.dao.devPar[1]
        self.setText(text)
        #sizeHint = self.sizeHint()
        #print(f'button {self.dao.parName} sizeHint: {sizeHint}')
        #h = sizeHint.width()
        #sizeHint.setWidth(int(h*0.8))
        #print(f'button {self.dao.parName} sizeHint: {sizeHint}')
        #self.resize(sizeHint)
        
        self.setStyleSheet("QPushButton{"
            #"background-color: lightBlue;"
            "background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,"
                "stop: 0 white, stop: 1 lightBlue);"
            #'border: 2px solid blue;'
            "border-style: solid;"
            "border-color: Grey;"
            "border-width: 2px;"
            "border-radius: 10px;}"
            #"font-weight: bold;"
            'QPushButton::pressed{background-color:pink;}'
        )#{+ButtonStyleSheet)
        self.clicked.connect(self.buttonClicked)

    def buttonClicked(self):
        printv(f'Clicked {self.dao.name}')
        self.dao.set(1)

    def contextMenuEvent(self,event):
        try:    hasSelectedText = self.hasSelectedText()
        except: hasSelectedText = False
        if hasSelectedText:
            QW.QLineEdit.contextMenuEvent(self,event)
        else:
            #printv(f'RightClick at lineEdit {self.dao.name}')
            Win.rightClick(self.dao)

class QPushButtonCmd(QW.QPushButton):
    """Pushbutton for launching external applications"""
    def __init__(self,text, cmd):
        self.cmd = cmd
        super().__init__(text)
        self.clicked.connect(self.handleClicked)
        
    def handleClicked(self):
        printv(f'clicked {self.cmd}')
        msg = 'launching `%s`'%str(self.cmd)
        #printv(msg)
        Win.update_statusBar(msg)
        p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, shell=True)

class MyTableWidget(QW.QTableWidget):
    """Modified QTableWidget"""
    def mousePressEvent(self,*args):
        button = args[0].button()
        #print(f'mousePress: {button}')
        item = self.itemAt(args[0].pos())
        try:
            row,col = item.row(),item.column()
        except:
            return
        if button == 2: # right button
            try:
                dao = self.daTable.pos2obj[(row,col)][0]
                #print( f'rclick{row,col}')
                if issubclass(type(dao),DataAccess):
                    #printv(f'RightClick at DAO {dao.name}')
                    Win.rightClick(dao)
            except Exception as e:
                printw(f'Exception in mousePressEvent: {e}')
                pass
        else:
            super().mousePressEvent(*args)

    def set_daTable(self, daTable):
        self.daTable = daTable

    def sizeHint(self):
        hh = self.horizontalHeader()
        vh = self.verticalHeader()
        fw = self.frameWidth() * 2
        return QtCore.QSize(
            hh.length() + vh.sizeHint().width() + fw,
            vh.length() + hh.sizeHint().height() + fw)

class QSliderDAO(QW.QSlider):
    """Slider associated with the Data Access Object"""
    def __init__(self, orientation, dao, opLimits):
        super().__init__()
        self.dao = dao
        o = {'h':QtCore.Qt.Horizontal,'v':QtCore.Qt.Vertical}[orientation[0]]
        self.setOrientation(o)
        self.setTracking(False)
        self.maximum = 100
        self.setMaximum(self.maximum)
        self.setTickPosition(QW.QSlider.TicksBelow)
        self.setTickInterval(10)
        printv(f'slider {orientation} attr:{self.dao.attr}')
        self.lastValue = self.dao.attr['value']
        if opLimits is None:
            opLimits = self.dao.attr.get('opLimits')
            if opLimits is None:
                opLimits = (0, self.maximum)
                printw(f'no oplimits for {self.dao.name}, assumed {opLimits}')
                pass
        self.opLimits = opLimits
        #self.setRange(*opLimits)
        #printi(f'opLimits for {dao.name} set to {opLimits}')
        self.valueChanged.connect(self.handle_value_changed)

    def slider2dao(self, handlePosition):
        v = (self.opLimits[1] - self.opLimits[0])/self.maximum*handlePosition
        return round(self.opLimits[0] + v, 9)

    def dao2slider(self, daoValue):
        opl,oph = self.opLimits
        v = int((daoValue - opl)/(oph - opl)*self.maximum)
        if v < 0:  v = 0
        if v > self.maximum: v = self.maximum
        return v

    def handle_value_changed(self):
        #if not Window.InitializationFinished:
        #    print(f'init not finished')
        #    return
        handlePosition = self.value()
        printv(f'handle_value_change to {handlePosition} from {self.lastValue}')
        if self.lastValue == handlePosition:
            return
        self.lastValue = handlePosition
        value = self.slider2dao(handlePosition)
        if not self.dao.set(value):
            self.setValue(self.lastValue)

    def setValue(self, v):
        #STRANGE# it is callled multiple times in a row
        widgetValue = self.dao2slider(v)
        printv(f'setv {v, widgetValue}')
        self.lastValue = widgetValue# to disable calling handle_value_changed
        super().setValue(widgetValue)
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#''''''''''''''''''Main Window````````````````````````````````````````````````
def currentDaTable():
    return Window.tabWidget.currentWidget().daTable

class Window(QW.QMainWindow):
    """Main window"""
    bottomLine = None
    InitializationFinished = False
    tabWidget = None
    tableWidgets = []

    def __init__(self):
        QW.QWidget.__init__(self)
        self.embeddedProcess = None
        menubar = self.menuBar()

        if pargs.restore:
            self.restorableParameters = []
            menubar.setStyleSheet('QMenuBar {'+StyleSheet_darkBackground+'}')
            fileMenu =  menubar.addMenu('&Snapshots')
            reloadItem = QW.QAction("&Reload", self\
            , triggered = self.reload_table)
            fileMenu.addAction(reloadItem)
            rpaItem = QW.QAction("Restore &all parameters", self\
            , triggered = self.restore_allParameters)
            fileMenu.addAction(rpaItem)
            rpItem = QW.QAction("Restore &selected parameters", self\
            , triggered = self.restore_parameters)
            fileMenu.addAction(rpItem)
        else:
            fileMenu =  menubar.addMenu('&File')
            reloadItem = QW.QAction("&Reload", self\
            , triggered = self.reload_table)
            fileMenu.addAction(reloadItem)

            editItem = QW.QAction("&Edit", self\
            , triggered = self.edit_table)
            fileMenu.addAction(editItem)

            commitItem = QW.QAction("&Commit", self\
            , triggered = self.commit_table)
            fileMenu.addAction(commitItem)

            saveItem = QW.QAction("&Save", self\
            , triggered = self.save_snapshot)
            fileMenu.addAction(saveItem)

            restoreItem = QW.QAction("Rest&ore", self\
            , triggered = self.restore_snapshot)
            fileMenu.addAction(restoreItem)

        self.load_tables()

        Window.tabWidget = detachable_tabs.DetachableTabWidget()
        printv(f'tabWidget created')
        self.setCentralWidget(Window.tabWidget)
        #Window.tabWidget.addTab(self.tableWidget, self.tableWidget.daTable.pypage.title)
        #tab2 = QW.QLabel('Test Widget 2')
        #Window.tabWidget.addTab(tab2, 'Tab2')
        for i,tableWidget in enumerate(Window.tableWidgets):
            title = tableWidget.daTable.pypage.title
            #print(f'Adding tab{i}: {title}')
            Window.tabWidget.addTab(tableWidget, tableWidget.daTable.pypage.title)

        exitItem = QW.QAction("E&xit", self\
        , triggered = self.closeEvent)
        fileMenu.addAction(exitItem)

        viewMenu = menubar.addMenu('&View')
        self.tableHeaders = QW.QAction('&Table headers'\
        , self, checkable=True)
        self.tableHeaders.triggered.connect(self.update_headers)
        viewMenu.addAction(self.tableHeaders)
        self.hideMenubar = QW.QAction('&Hide Menubar and Statusbar'\
        , self, triggered = self.hide_menuBar)
        viewMenu.addAction(self.hideMenubar)
        plotItem = QW.QAction('&Plot selected items', self\
        , triggered = self.plot_selectedAdopars)
        viewMenu.addAction(plotItem)
        corplotItem = QW.QAction('&Correlation plot', self\
        , triggered=partial(self.plot_selectedAdopars, 'Correlation'))
        viewMenu.addAction(corplotItem)

        dataMenu = menubar.addMenu('&Data')
        dataMenu.addSection('Delivery')
        self.deliveryCombo = QW.QComboBox(self)
        #self.deliveryCombo.addItem('Delivery')
        for m in DataDeliveryModes:
            self.deliveryCombo.addItem(m)
        self.deliveryCombo.currentIndexChanged.connect(self.deliveryActionChanged)
        self.deliveryCombo.view().pressed.connect(self.deliveryActionPressed)
        self.objectTest1 = QtCore.QObject()# self is necessary here
        deliveryAction = QW.QWidgetAction(self.objectTest1)
        deliveryAction.setDefaultWidget(self.deliveryCombo)
        dataMenu.addAction(deliveryAction)

        helpMenu = menubar.addMenu('&Help')
        def wikiMenuAct():
            os_system(f'{Browser} https://github.com/ASukhanov/pypeto')
        wikiMenu = QW.QAction(f"About &{AppName}", self\
        , triggered = wikiMenuAct)
        helpMenu.addAction(wikiMenu)
        try:
            pageHelp = self.tableWidget.daTable.pypage.pageHelp
            helpMenu.addSeparator()
            def pageHelpAct():
                os_system(f'{Browser} {pageHelp}')
            pageHelpMenu = QW.QAction("About this &page", self\
            , triggered = pageHelpAct)
            helpMenu.addAction(pageHelpMenu)
        except Exception as e:
            printw(f'in pageHelp menu: {e}')
            pass

        self.update_statusBar(f'{AppName} version {__version__}')
        self.lostConnections = set()
        self.widgetColor = {}

        title = 'pypet '
        if pargs.device:
            title += pargs.device
        else:
            title += ','.join(pargs.files).replace('_pp','')
        self.setWindowTitle(title)
        #Win.resize(350, 300)
        self.screenGeometry = QW.QDesktopWidget().screenGeometry().getRect()
        self.show()
        if pargs.geometry:
            self.move_mainWindow(np.fromstring(pargs.geometry, sep=','))

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.heartBeat)
        self.heartBeatTime = time.time()
        self.timer.start(1000)
        if pargs.restore:
            self.deliveryCombo.setCurrentText('Stopped')

    def move_mainWindow(self, relativeXY):
        wh = self.screenGeometry[2:]
        #print(f'relativeXY:{relativeXY}, {wh}')
        xy = (np.array(relativeXY)*wh).astype('int')
        #print(f'xy = {xy}')
        self.move(*xy)

    def reload_table(self):
        currentMode = dataAccessMonitor.setup_dataDelivery('Stopped')# by some reason the __del__ is not always called in destructor
        self.load_table()
        dataAccessMonitor.setup_dataDelivery(currentMode)

    def load_tables(self):
        """Load table from saved snapshot"""
        # read config file
        #try:    del Window.daTable
        #except: pass
        for f in pargs.files:
            daTable = DaTable(f)
            self.tableWidget = MyTableWidget(*daTable.shape, self)
            self.tableWidget.set_daTable(daTable)
            self.tableWidget.setShowGrid(False)
            self.tableWidget.setSizeAdjustPolicy(
                QW.QAbstractScrollArea.AdjustToContents)
            self.tableWidget.verticalHeader().setVisible(True)
            try:    self.columnAttributes = self.tableWidget.daTable.pypage.columns
            except Exception as e:
                printw(f'exception with columnAttributes {e}')
                self.columnAttributes = {}
            #self.tableWidget.setAlternatingRowColors(True)
            #self.tableWidget.setStyleSheet("alternate-background-color: red; background: lightGrey; color: #6b6d7b; ")

            printv(f'```````````````````````Processing table {daTable.pypage.title}')
            self._process_daTable(daTable)
            printv(',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,')
            self.tableWidget.cellClicked.connect(self.handleCellClicked)
            Window.tableWidgets.append(self.tableWidget)

        if pargs.hidemenubar:
            self.hide_menuBar()
        Window.InitializationFinished = True

    def edit_table(self):
        """Edit page file externally"""
        daTable = currentDaTable()
        cmd = f'xdg-open {daTable.file}'
        printi(f'executing: {cmd}')
        subprocess.Popen(cmd.split())

    def commit_table(self):
        """Commit and push changed page to github"""
        import getpass
        user = getpass.getuser()
        cf = currentDaTable().file
        cmd = (f'cd {pargs.configDir};'
        f' git commit {cf} -m"by {user} using {AppName}";'
        f' git push')
        printi(f'executing: {cmd}')
        os_system(cmd)

    def update_statusBar(self,msg):
        #print(f'update_statusBar:{msg}')
        self.statusBar().showMessage(msg)

    def _process_daTable(self, daTable):
        """Part of the load_table. Build par2objAndPos from pos2obj"""
        rows, columns = daTable.shape
        #print('>_process_daTable}')
        try:    defaultColor = daTable.pypage['color']
        except: defaultColor = 'white'
        for row in range(rows):
          self.tableWidget.setRowHeight(row,20)# This setting has no effect, even for height=1
          #try:  
          #  if daTable.pos2obj[(row,0)][0] is None:
          #          continue
          #except:   continue
          for col in range(columns):
            try: obj,cellAttribute = daTable.pos2obj[(row,col)]
            except Exception as e:
                printv(f'Not an object @{row,col}: {e}')
                continue
            if col == 0:
                #print(f'col0: row{row} {cellAttribute}' )
                height = cellAttribute.get('height')
                if height is not None:
                    self.tableWidget.setRowHeight(row,height)

            for attribute,value in cellAttribute.items():
                #if pargs.verbose: #printv(croppedText(f'handle cellAttributes{row,col}:{attribute,value}'))
                if attribute == 'span':
                    try: spanCol,spanRow = value
                    except: spanRow,spanCol = 1,value
                    #print(f'merging {value} cells starting at {row,col}')
                    self.tableWidget.setSpan(row,col,spanRow,spanCol)

            if obj is None:
                continue
            fgc = 'darkBlue'
            if isinstance(obj,str):
                item = QW.QTableWidgetItem(str(obj))
                #print(f'set cell{row,col} to {obj}')
                flags = item.flags() & ~QtCore.Qt.ItemIsEditable
                item.setFlags(flags)
                item.setBackground(configColor(defaultColor))
                self.set_tableItem(row,col, item,cellAttribute,fgColor=fgc)
                continue
            elif isinstance(obj,list):
                print (f'####rowCol{row,col} is list: {obj}')
                self.set_tableItem(row,col,obj, cellAttribute, fgColor=fgc)
                continue
            if not issubclass(type(obj), DataAccess):
                msg = f'Unknown object@{row,col}: {type(obj)}'
                raise NameError(msg)
                
            #``````the object is DataAccess```````````````````````````````````
            dataAccess = obj
            vslice = dataAccess.vslice
            #printv(f'DA object @{row,col}:{dataAccess.name}, vslice:{vslice}')
            gt = dataAccess.get_guiType(cellAttribute.get('attr'))
            if gt:
                if not 'widget' in cellAttribute:
                    cellAttribute['widget'] = gt

            # store a list of row,col's as the same object may be addressed from several cells
            entry = daTable.par2objAndPos.get(dataAccess.name)
            if entry is None:
                daTable.par2objAndPos[dataAccess.name] = (dataAccess, [((row,col),vslice)])
            else:
                entry[1].append(((row,col),vslice))

            try:
                item = QW.QTableWidgetItem(dataAccess.name)
            except Exception as e:
                printw(f'Could not define Table[{row,col}]: {e}')
                print('Traceback: '+repr(traceback.format_exc()))
                continue
                
            # deduct the cell type from DAO
            self.set_tableItem(row, col, item, cellAttribute, dataAccess)
        #printv(croppedText(f'par2objAndPos: {daTable.par2objAndPos}'))
        self.tableWidget.resizeColumnsToContents()
        #self.tableWidget.setColumnWidth(0,60)
        if self.columnAttributes:
            try:
                #print(f'columnAttributes:{self.columnAttributes}')
                for column,form in self.columnAttributes.items():
                    width = form.get('width')
                    if not width:
                        continue
                    #printv(f'setting columnWidth{type(column),column-1,type(width),width}')
                    self.tableWidget.setColumnWidth(column-1, width)
            except Exception as e:
                printe(f'wrong ColumnWidths: {column,width}')
        self.tableWidget.horizontalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setVisible(False)

    def update_headers(self):
        self.tableWidget.horizontalHeader().setVisible(self.tableHeaders.isChecked())
        self.tableWidget.verticalHeader().setVisible(self.tableHeaders.isChecked())

    def hide_menuBar(self):
        self.menuBar().setVisible(False)
        self.statusBar().setVisible(False)

    def set_tableItem(self,row,col,item,attributes,dataAccess=None,fgColor=None):
        """Set table item according to cell or DAO attributes""" 
        cellName = item.text()
        #printv(f'set_tableItem {cellName}@{row,col}: attributes:{attributes}') 

        # collect item attributes from columnAttributes, and update them with cell attributes
        cattr = self.columnAttributes
        fmt = cattr.get('format')
        try:
            fullAttributes = cattr[col+1].copy()
        except Exception as e:
            fullAttributes = {}
        fullAttributes.update(attributes)
        #if pargs.verbose: #printv(croppedText(f'fullAttr of {cellName}: {fullAttributes}'))

        paintItDark = False
        iValue = '?'
        description = None
        if dataAccess:                
            # overwrite DAO description with the cell description
            try:    dataAccess.attr['desc'] = fullAttributes['desc']
            except: pass

            initial = attributes.get('initial')
            v = dataAccess.attr.get('value')
            if v is None:
                #printv(f'Not settable: {cellName}')
                # should not return here
                pass
            iValue = iterable(v)
            printv(f'initial of {cellName}:{iValue}')
            if pargs.restore:
                writable = 'W' in attributes['features']
                try:
                    if writable:
                        printv(f'initial of {cellName}: {initial}, now:{v}')
                        if initial != v:
                            self.restorableParameters.append((row,col))
                            #print(f'parameter {cellName}={v} differs from snapshot={initial}')
                            paintItDark = True
                except Exception as e:
                    printw(f'in writable initial: {e}')
            if initial is not None:
                iValue = iterable(initial)# 
            txt = v2t(iValue, fmt=fmt)
            units = dataAccess.attr.get('units')
            if units is not None:
                printv(f'units:{units}')
                txt += ' '+units

            # this section is valid only for non-scalar daoPars
            try:
                #print(f'QTableWidgetItem({txt})')
                item = QW.QTableWidgetItem(txt)
                item.setBackground(QtGui.QColor(*rgbColorCode(txt)))
            except Exception as e: 
                printw(f'in re-item {cellName}@{row,col}:{e}')
                pass
            if not dataAccess.is_editable():
                #print(f'item {dataAccess.name} is not editable')
                flags = item.flags() & ~QtCore.Qt.ItemIsEditable
                item.setFlags(flags)

            description = dataAccess.attr.get('desc')
            #print(f'desc of {cellName}: {description}')

        cellFgColor = fullAttributes.get('fgColor')
        if cellFgColor:
            fgColor = cellFgColor
            del fullAttributes['fgColor']
        if fgColor:
            item.setForeground(QtGui.QBrush(QtGui.QColor(fgColor)))

        font = fullAttributes.get('font')
        if font:
            try:
                font = QtGui.QFont(*font)
            except:
                printw(f'font not accepted for {row+1,col+1}:{font}')
                font = None
        isItemWidget = False
        bgColor = attributes.get('color')
        for attribute,value in fullAttributes.items():
            #item.setTextAlignment(QtCore.Qt.AlignCenter)
            if attribute in ('span','width','text', 'font', 'desc',
              'attr', 'initial', 'features', 'opLimits', 'height', 'format'):
              # these are processed in the _process_daTable()
                continue
            elif attribute == 'color':
                item.setBackground(configColor(value))
            elif attribute[:4] == 'just':# justify
                d = {'l':QtCore.Qt.AlignLeft, 'c':QtCore.Qt.AlignCenter\
                , 'r':QtCore.Qt.AlignRight}
                a = d.get(value[0])
                if a:
                    #print(f'justify {cellName} {value}')
                    item.setTextAlignment(a)
            elif attribute == 'launch':
                #print(f'launch@{row,col}: {attributes}')
                isItemWidget = True
                pbutton = QPushButtonCmd(cellName, value)
                pbutton.setStyleSheet(f'background-color:{bgColor}')
                if font:
                    pbutton.setFont(font)
                self.tableWidget.setCellWidget(row, col, pbutton)
                continue
            elif attribute == 'widget':
                isItemWidget = True
                printv(f"widget at {row,col}: {value}, color:{attributes.get('color')}")
                if dataAccess is None:
                    return
                if value == 'spinbox':
                    #print(f'ivalue: {iValue}')
                    #TODO fix for LITE:
                    try:
                        v = iValue[0]
                    except:
                        print('FixMe')
                        v = iValue['value'][0]
                    i = isinstance(v,int)
                    printv(f'>spinbox in {row,col} changed to {("float","int")[i]} {v}')
                    widget = QDoubleSpinBoxDAO(dataAccess,bgColor)
                    bgColor = None
                    #widget.setOpts(format=fmt)# does not work
                    widget.setValue(v)
                elif value == 'combo':
                    widget = QComboBoxDAO(dataAccess)
                    widget.setText(txt)
                elif value == 'lineEdit':
                    printv( f'>lineEdit:{row,col}')
                    widget = QLineEditDAO(dataAccess)
                    widget.setText(v2t(iValue, fmt=fmt))
                elif value == 'button':
                    printv( f">button: {cellName.rsplit(':',1)[-1]}")
                    txt = fullAttributes.get('text')
                    widget = QPushButtonDAO(dataAccess,txt)
                elif value == 'hslider':
                    printv(f'setValue {value} for slider in {row,col}')
                    opLimits = fullAttributes.get('opLimits')
                    widget = QSliderDAO('horizontal',dataAccess, opLimits)
                    widget.setValue(iValue[0])
                elif value == 'vslider':
                    opLimits = fullAttributes.get('opLimits')
                    widget = QSliderDAO('vertical',dataAccess, opLimits)
                    widget.setValue(iValue[0])
                else:
                    printw('Not supported widget(%i,%i):'%(row,col)+value)
                    return
                if paintItDark:
                    widget.setStyleSheet(StyleSheet_darkBackground)
                if font:
                    widget.setFont(font)
                    font = None
                if description is not None:
                    widget.setToolTip(description)
                if bgColor is not None:
                    widget.setStyleSheet(f'background-color:{bgColor}')
                self.tableWidget.setCellWidget(row, col, widget)
            elif attribute == 'embed':
                isItemWidget = True
                self.embed(row, col, value)
            else:
                printw('not supported attribute(%i,%i):'%(row,col)+attribute)

        if font:
            #print(f'setting font {font} for {cellName}')
            item.setFont(font)
            
        #printv('setting item(%i,%i): '%(row,col)+str(item))
        if not isItemWidget:
            self.tableWidget.setItem(row, col, item)
            if description is not None:
                item.setToolTip(description)

    def closeEvent(self,*args):
        """Called when the window is closed"""
        printi('>closeEvent')
        EventExit.set()
        if Win.embeddedProcess:
            try: 
                printi('killing the embedded process')
                Win.embeddedProcess.kill()
            except: pass
        sys.exit(1)

    def handleItemPressed(self, item):
        #printv('pressed[%i,%i]'%(item.row(),item.column()))
        return

    def handleItemDoubleClicked(self, item):
        #print(f'DoubleClicked {item.row(),item.column()}')
        return

    def handleItemClicked(self, item):
        #print(f'Clicked {item.row(),item.column()}')
        self.handleCellClicked(item.row(),item.column())

    def handleCellDoubleClicked(self, x,y):
        #print(f'Cell DoubleClicked {x,y}')
        return

    def handleCellClicked(self, row,column):
        item = self.tableWidget.item(row,column)
        #print(f'Cell clicked {row,column}')

    def update(self,a):
        #printv('window update',a)
        tableItem = self.tableWidget.item(2,1)
        try:
            tableItem.setText(str(a[0]))
        except Exception as e:
            printw('in tableItem.setText:'+str(e))
            
    def rightClick(self, dataAccess):
        attributes = dataAccess.attr
        #print(f'Window. RightClick on {dataAccess.name}, attr:{attributes}')
        d = QW.QMessageBox(self)
        #d.setIcon(QW.QMessageBox.Information)
        d.setStandardButtons(QW.QMessageBox.Cancel)#QW.QMessageBox.Ok)# | )
        devPar = dataAccess.name
        #print(f'selected items:{self.tableWidget.selectedItems()}')
        d.setWindowTitle(f'Info on {devPar}')
        #d.setText(f'Click Show Details to view attributres of \n{devPar}')
        description = attributes.get('desc','')
        from textwrap import fill
        d.setText(devPar+'\n'+fill(description,40))
        l = list(attributes.keys())
        l.remove('value')
        l.append('value')
        l.remove('desc')
        l.insert(0,'desc')
        txt = ''
        for attr in l:
            v = attributes[attr]
            vv = datetime.fromtimestamp(v).strftime('%y-%m-%d_%H:%M:%S')\
              if attr.startswith('timestampS') else v2t(v, 300, fmt='%.12g')
            try:
                if attr == 'value' and len(v) > 1:
                    attr = f'value[{len(v)}]'
            except: pass
            txt += attr+':\t'+vv+'\n'
        d.setDetailedText(txt)
        features = attributes.get('features','RWE')
        if 'R' in features:
            # readable parameter can be plotted
            btPlot = QW.QPushButton('Plot', self)
            #plotType = 'StripChart' if attributes['count'] == 1 else 'Snapshot'
            plotType = None # pvplot is smart enough
            vslice = dataAccess.vslice
            #print(f'pvplot {devPar}, {vslice}')
            if dataAccess.vslice is not None:
                devPar += f'[{vslice[0]}:{vslice[1]}]'
            if len(self.tableWidget.selectedItems()) == 0:
                btPlot.clicked.connect(partial(pvplot, [devPar], plotType, d))
            else:
                btPlot.clicked.connect(self.plot_selectedAdopars)
            d.layout().addWidget(btPlot,0,0)
        if 'W' in features:
            btHistory = QW.QPushButton('History', self)
            btHistory.clicked.connect(partial(self.parameterHistory, d, devPar))
            d.layout().addWidget(btHistory,1,0)
        d.show()

    def heartBeat(self):
        """Heartbeat task, connected to QT timer. It checks if 
        devices are alive by requesting parName device parameter."""
        t = time.time()
        if t - self.heartBeatTime < 10.:
            return
        self.heartBeatTime = t
        #TODO: execute info on all devices
        printv(f'>heartBeat')
        daTable = currentDaTable()
        namespace = get_namespace()
        #print(f'>heartbeat namespace: {namespace}')
        if namespace is None: namespace = DefaultNamespace
        if namespace == 'ADO':
            parName = 'version'
        elif namespace == 'LITE':
            parName = 'run'
        elif namespace in ['EPICS','PVA']:
            #printw('heartbeat for EPICS not yet implemented')
            return
        else:
            printe(f'Not supported namespace: {namespace}')
            return

        for devName,daoDict in daTable.deviceMap.items():
            dao = list(daoDict.values())
            firstDevPar = dao[0].devPar
            #print(f'HB, devName, devPar: {devName,firstDevPar}')
            try:
                access = dao[0].Access
                # check if device is alive
                #TODO: for liteServer we can check time sleepage
                #ts0 = time.time()
                r = access.get((devName,parName), timestamp=False)
                #ts1 = time.time()
                #msg = f'RoundTrip time = {round((ts1-ts0)*1000,2)} ms'
                #Win.update_statusBar(msg)
                if devName in self.lostConnections:
                    printw(f'Heartbeat on {devName} is recovered')
                    self.lostConnections.remove(devName)
                    self.connectionRecovered(devName, daTable)
            except Exception as e:
                if not devName in self.lostConnections:
                    printw(f'No heartbeat from {devName}: {e}')
                    self.lostConnections.add(devName)
                    self.connectionLost(devName, daTable)                        
        #printvv('<heartbeat')

    def connectionLost(self, host, daTable):
        printw(f'Lost connection to {host}')
        for devPar,ObjAndPos in daTable.par2objAndPos.items():
            dev,par = devPar.rsplit(':',1)
            obj,rowCols = ObjAndPos
            if dev == host:
                #print(f'paint it pink: {rowCols}')
                for rowColSlice in rowCols:
                    rowCol,vslice = rowColSlice
                    item = self.tableWidget.item(*rowCol)
                    widget = self.tableWidget.cellWidget(*rowCol)
                    #print(f'item: {item}, widget:{widget}')
                    if widget:
                        #print(f'widget at {rowCol} color:{widget.style()}')
                        widget.setStyleSheet('background-color:pink')
                    else:
                        item.setBackground(QtGui.QColor('pink'))

    def connectionRecovered(self, host, daTable):
        printw(f'Connection to {host} is restored')
        for devPar,ObjAndPos in daTable.par2objAndPos.items():
            dev,par = devPar.rsplit(':',1)
            obj,rowCols = ObjAndPos
            if dev == host:
                #print(f'paint it white: {rowCols}')
                for rowColSlice in rowCols:
                    rowCol,vslice = rowColSlice
                    item = self.tableWidget.item(*rowCol)
                    widget = self.tableWidget.cellWidget(*rowCol)
                    if widget:
                        widget.setStyleSheet('background-color:white')
                    else:
                        item.setBackground(QtGui.QColor('white'))                    

    def embed(self, row, col, program):
        """Embed external program into a cell."""
        if pargs.dont_embed:
            return
        print(f'Executing: "{program}"')
        try:
            self.embeddedProcess = subprocess.Popen(program.split()\
            ,stdout=subprocess.PIPE)
        except Exception as e:
            printe(f'Could not launch process "{program}": {e}')
            sys.exit(0)
        self.embedArgs = (row,col,program)
        self.embedCountdown = 10
        self.embedTimer = QtCore.QTimer()
        self.embedTimer.timeout.connect(self.embed_later)
        self.embedTimer.start(1000)

    def embed_later(self):
        row,col,program = self.embedArgs
        self.embedCountdown -= 1
        #print(f'embed_later({self.embedArgs} {self.embedCountdown})')
        if not self.embedCountdown:
            printe(f'Failed to embed {program}')
            self.embedTimer.stop()
        try:
            # using pid2winid.sh
            #winid_bytes = subprocess.check_output(['pid2winid.sh', f'{self.embeddedProcess.pid}'])
            # using xdotool, much faster:
            winid_bytes = subprocess.check_output(['xdotool','search','--pid',\
            f'{self.embeddedProcess.pid}'])
            printi(f'WinId of the "{program}" identified: {winid_bytes}')
            winid_txt = winid_bytes.decode().replace('\n','')
            #winid = int(winid_txt,16)#pid2winid.sh
            winid = int(winid_txt)            
        except:#Exception as e:
            printi((f'Will try {self.embedCountdown} more times to embed "'\
            f'{program}" to cell {row,col}'))#: {e}')
            return
        embed_window = QtGui.QWindow.fromWinId(winid)
        embed_widget = QW.QWidget.createWindowContainer(embed_window,
          self)#, QtCore.Qt.FramelessWindowHint)
        self.tableWidget.setCellWidget(row, col, embed_widget)
        self.embedTimer.stop()

    def plot_selectedAdopars(self, plotType=None):
        devPars = []
        selecteItems = self.tableWidget.selectedItems()
        daTable = currentDaTable()
        for item in selecteItems:
            row,col = item.row(), item.column()
            dao = daTable.pos2obj[(row,col)][0]
            if not isinstance(dao, DataAccess):
                continue
            devPar = dao.name
            vslice = dao.vslice
            if vslice is None:
                devPars.append(devPar)
            else:
                devPars.append(f'{devPar}[{vslice[0]}:{vslice[1]}]')
        pvplot(devPars, plotType)

    def parameterHistory(self, dialog, devPar):
        """Launch setHistory viewer"""
        printi(f'launch: setHistory {devPar}')
        subprocess.Popen(['setHistory',devPar])
        if dialog:  dialog.accept()

    def deliveryActionChanged(self,*_):
        mode = self.deliveryCombo.currentText()
        #print(f'deliveryActionChanged: {mode, DataAccessMonitor.currentDeliveryMode}')
        dataAccessMonitor.setup_dataDelivery(mode)

    def deliveryActionPressed(self,*_):
        mode = self.deliveryCombo.currentText()
        #print(f'deliveryActionPressed: {mode}')
        if mode == 'Stopped':
            dataAccessMonitor.setup_dataDelivery(mode)

    def get_snapshotDirectory(self):
        snapshotDir = os.path.abspath(pargs.configDir)
        #printv(f'pargs.file:{pargs.file}, pargs.device:{pargs.device}')
        if pargs.files:
            daTable = currentDaTable()
            daTable.file.rsplit('/',1)
            relativeFilename = daTable.file.rsplit('/',1)[-1].replace('_pp.py','')
            snapshotDir += '/Snapshots/' + relativeFilename
            snapshotDir += '/'
        else: # should not happen
            snapshotDir += 'devices/'
        if pargs.device:
            snapshotDir += pargs.device+'/'
        snapshotDir = snapshotDir.replace('.','_')# filename with dot cannot be included
        printv(f'snapshotDir: {snapshotDir}')
        return snapshotDir
        
    def check_path(path):
        """Check if path exists, create it if not"""
        from os import path as os_path, makedirs as os_makedirs
        try:
            if not os_path.exists(path):
                printi(f'check_path created new path:{path}')
                os_makedirs(path)
        except Exception as e:
            printe('in check_path '+path+' error: '+str(e))

    def save_snapshot(self):
        snapshotDir = self.get_snapshotDirectory()
        # module name cannot have dots in the name
        fnamePart = time.strftime(f'pp%Y%m%d_%H%M')
        fname = self.confirm_snapshot(snapshotDir, fnamePart+'_pp.py')
        if fname is None:
            return
        Window.check_path(snapshotDir)
        fname = snapshotDir + fname
        row = []
        rows = [row]
        prevrowNumber, prevcolNumber = 0,0
        daTable = currentDaTable()
        for key, value in daTable.pos2obj.items():
            #print(f'row,col:{key}, obj:{value[0]}, attr:{value}')
            rowNumber,colNumber = key
            if rowNumber > prevrowNumber:
                # append empty rows, if any
                for i in range(prevrowNumber, rowNumber):
                    rows.append([])
                prevrowNumber = rowNumber
                prevcolNumber = 0
            # accumulate cells in the row
            row = rows[-1]
            if colNumber > prevcolNumber:
                # append empty columns, if any
                for i in range(prevcolNumber, colNumber-1):
                    row.append(' ')
                prevcolNumber = colNumber
            obj,attr = value
            # do not need initial values for non-writable parameters
            #print(f'attr: {attr}')
            #features = attr.get('features','RWE')
            features = attr.get('features','')
            writable = 'W' in features
            if writable:
                value = obj.get()
                if isinstance(value,dict):# LITE case
                    value = value['value']
                if True:#try:
                    if obj.vslice is None:
                        attr['initial'] = value
                    else:
                        attr['initial'] = value[vslice[0]:vslice[1]]
                    #print(f"save initial row: {attr['initial']}")
                else:#except:
                    pass
            if not writable:
                #print(f'deleting initial from {obj,attr}')
                try:    del attr['initial']
                except: pass
            txt = value[0] if isinstance(obj,str) else obj.name
            v = {txt:attr}
            #print(f'Appending row {len(row)}: {v}')
            row.append({txt:attr})
            #except Exception as e:
            #    printe(f'in save_snapshot:{e}')
        #except: namespace = DefaultNamespace
        content = (
f'#Saved pypet snapshot.\n'
f'class PyPage():\n'
f'    def __init__(self, **_):\n'
#f'        dev = "{cnsName}"\n'
f'        self.namespace = "{daTable.pypage.namespace}"\n'
f'        self.title = "{fnamePart}"\n'
 '        self.rows = [\n'
    )
        for row in rows:
            content += f'{row},\n'
        content += ']\n'

        try:
            f = open(fname,'w')
            f.write(content)
            f.close()
            printi(f'Snapshot saved to {fname}')
        except Exception as e:
            Win.update_statusBar('ERROR: saving {fname}: {e}')

    def confirm_snapshot(self, dirname, fname):
        d = QW.QMessageBox(self)
        #d.setIcon(QW.QMessageBox.Information)
        d.setStandardButtons(QW.QMessageBox.Save | QW.QMessageBox.Cancel)
        d.setWindowTitle('Confirm snapshot')
        txt = f'Please confirm to save snapshot to directory:\n{dirname}\n'
        txt += 'under following file name:'
        #d.setText(txt)
        lb = QW.QLabel(txt, self)
        d.layout().addWidget(lb,0,0)
        #d.setInformativeText('Please confirm:')
        le = QW.QLineEdit(fname, self)
        d.layout().addWidget(le,1,0)
        ok = d.exec_() == QW.QMessageBox.Save
        return le.text() if ok else None

    def restore_snapshot(self):
        snapshotDir = self.get_snapshotDirectory()
        #print(f'rsnap: {pargs.file}')
        #snapshotDir = ConfigDirectory+'Snapshots/'+pargs.file[:-3]#remove _pp
        x,y,w,h = self.geometry().getRect()
        x += w
        rx = round(x/self.screenGeometry[2],3)
        ry = round(y/self.screenGeometry[3],3)
        cmd = f'python3 -m {AppName} -r -e -g{rx},{ry} -c{snapshotDir}'
        printi(f'cmd: {cmd}')
        subprocess.Popen(cmd.split())#,stdout=subprocess.PIPE)

    def restore_parameters(self):
        selectedParameters = self.tableWidget.selectedItems()
        printi(f'selectedPPars:{selectedParameters}')
        for item in selectedParameters:
            row,col = item.row(), item.column()
            self.restore_parameter(row, col)
        self.reload_table()

    def restore_allParameters(self):
        for row,col  in self.restorableParameters:
            self.restore_parameter(row, col)
        self.reload_table()

    def restore_parameter(self, row, col):
        try:
            dao,attr = Window.daTable.pos2obj[(row,col)]
            devPar = dao.devPar
            val = attr['initial']
            #print(f'restore {devPar, val}')
            #r = Access.set(parName.rsplit(':',1) + [val])
            r = dao.Access.set(list(devPar) + [val])
            widget = self.tableWidget.cellWidget(row,col)
            widget.setStyleSheet(StyleSheet_lightBackground)
        except Exception as e:
            printw(f'in restore_parameter:{e}')
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Reactor on data change`````````````````````````````````````
def MySlot(listOfParNames):
  """Global redirector of the SignalSourceDataReady.
  """
  with Process_data_Lock:
    printv(f'>MySlot received event: {listOfParNames}')
    tableWidget = Window.tabWidget.currentWidget()
    daTable = tableWidget.daTable
    printv(f'daTable: {daTable.pypage.title}')
    if listOfParNames is None:
        daRowCols = daTable.par2objAndPos.values()
    else:
        daRowCols = [daTable.par2objAndPos[i] for i in  listOfParNames] 
    errMsg = ''
    if dataAccessMonitor.Perf: ts = timer()
    for datAccess,rowCols in daRowCols:
      for rowColSlice in rowCols:
        printv(f'dao {datAccess.name}, rowColSlice: {rowColSlice}')
        rowCol,vslice = rowColSlice
        # datAccess is DataAccess object, rowCol is (row,column)
        try:
            currentValue = datAccess.currentValue if vslice is None else\
              datAccess.currentValue[vslice[0]:vslice[1]]
        except:
            #printw(f'currentValue not available for {datAccess.name}')
            continue
        #if pargs.verbose:#do not use #printv here, could be time consuming
        #    print(croppedText(f'updating DA{rowColSlice}: {datAccess.name, currentValue}'))
        try:
            if 'R' not in datAccess.attr['features']:
                #print(f'not readable {datAccess.name}')# cannot rely on this, many parameters are not properly marked
                pass
        except: pass
        if isinstance(datAccess,str):
            printw('logic error')
            continue
        try:
            #val = datAccess.currentValue['v']# 'liteServer
            val = [currentValue]
            #printv('val:%s'%str(val)[:100])
            if val is None:
                try:
                    tableWidget.item(*rowCol).setText('none')
                except:  pass
                continue
            if datAccess.guiType == 'spinbox':
                #print('DAO '+datAccess.name+' is spinbox '+str(val[0]))
                #try:    v = int(val[0])#DNW with QDoubleSpinBox
                #except: v = float(val[0])
                v = val[0]
                if isinstance(v,(list,tuple)):
                    #printw('mySlot: spinbox value is iterable (lite issue)?')
                    v = v[0]
                oldVal = tableWidget.cellWidget(*rowCol).value()
                #print(f'spinbox {datAccess.name} change from {oldVal} to {v}')
                if oldVal == v:
                    #print('no need to change spinbox')
                    continue
                #try:       v = v[0]
                #except:    pass
                tableWidget.cellWidget(*rowCol).setValue(v)
                continue
            elif datAccess.guiType =='bool':
                #printv('DAO '+datAccess.name+' is bool')
                state = tableWidget.item(*rowCol).checkState()
                #printv('DAO '+datAccess.name+' is bool = '+str(val)+', state:'+str(state))
                if val[0] != (state != 0):
                    #print('flip')
                    tableWidget.item(*rowCol).setCheckState(val[0])
                continue

            # get text presentation of the item 
            if len(val) > 1:
                #printv('DAO '+datAccess.name+' is list')
                txt = v2t(val)
            else:
                val = val[0]
                #printv('DAO '+datAccess.name+' is '+str(type(val)))
                obj,cellAttr = daTable.pos2obj[rowCol]
                fmt = cellAttr.get('format')
                txt = v2t(val, fmt=fmt)
                units = datAccess.attr.get('units')
                if units:
                    txt += ' '+units

            widget =  tableWidget.cellWidget(*rowCol)
            if not widget:
                widget = tableWidget.item(*rowCol)
            widget.setText(txt)
            if isinstance(val, str):
                try: widget.setBackground(QtGui.QColor(*rgbColorCode(txt)))#TODO:restore old color
                except: pass
        except Exception as e:
            errMsg = 'MySlot ' + str(e)
            printw(errMsg)
            print('Traceback: '+repr(traceback.format_exc()))
            break
    if dataAccessMonitor.Perf: print('GUI update time: %.4f'%(timer()-ts))    
    #printv(f'<MySlot processed data')
    if errMsg:  Win.update_statusBar('WRN: '+errMsg) #Issue, it could be long delay here
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#````````````````````````````Data provider````````````````````````````````````
class DataAccessMonitor(QtCore.QThread):
    """Data provider. Class attributes:
    Perf:       enables performance monitoring if True.
    SignalSourceDataReady: signal that data ready from the source.
    hostDAOs:   map of host:aggregatedDAO, the aggregatedDAO is a list of all
                data access objects, requested from this host
    """
    Perf = False
    # inheritance from QtCore.QThread is needed for qt signals
    SignalSourceDataReady = QtCore.Signal(object)
    hostDAOs = {}#TODO: why not to use Window.daTable.deviceMap directly
    currentDeliveryMode = 'Stopped'
    def __init__(self):
        # for signal/slot paradigm we need to call the parent init
        super().__init__()
        #printv('connecting to MySlot')
        self.SignalSourceDataReady.connect(MySlot)
        self.pollingInterval = 0.

    def setup_dataDelivery(self, modeTxt:str):
        """modeTxt legal values:
        Asynchronous:  for asynchronous,
        Polling 1 s:    polling with 1 s interval
        Polling 10 s:   polling with 10 s interval
        Polling 1 min:  polling with 1 min interval
        Stopped:        stop data delivery
        """
        #print(f'>setup_dataDelivery {modeTxt}')
        mode = modeTxt[:4]
        if mode not in ['','Stop']:
            #print('Calling _stop')
            self._stop()

        if len(self.hostDAOs) == 0:
            for i,tableWidget in enumerate(Window.tableWidgets):
                #print(f'Adding ado PVs for tab{i}')
                daTable = tableWidget.daTable
                #print(f'setup_dataDelivery: {daTable.deviceMap}')
                self.hostDAOs.update(daTable.deviceMap)
        #print(f'hostDAOs: {self.hostDAOs}')
        self.pollingInterval = DataDeliveryModes[modeTxt]
        func = {'Asyn':self._setup_asyncDelivery,
                'Poll':self._setup_pollingDelivery,
                'Stop':self._stop}.get(mode)
        if func:
            func()
        previousMode = DataAccessMonitor.currentDeliveryMode
        DataAccessMonitor.currentDeliveryMode = modeTxt
        return previousMode

    def _stop(self):
        #print('Call _stop_asyncDelivery from _stop')
        self._stop_asyncDelivery()
        self._stop_pollingDelivery()

    def _setup_asyncDelivery(self):
        #print(f'>_setup_asyncDelivery {list(self.hostDAOs.keys())}')
        self._stop_pollingDelivery()
        #print(self.hostDAOs.items())
        for host,daoDict in self.hostDAOs.items():
            aggregatedDAO = list(daoDict.values())
            for dao in aggregatedDAO:
                #print(f'_setup_asyncDelivery {dao}')
                devPar = dao.devPar
                try:
                    r = dao.Access.subscribe(self._callback, devPar)
                    printv(f'subscribed to {devPar}')
                except Exception as e:
                    printw(f'Could not subscribe for {devPar}: {e}')
                    #sys.exit(1)
        #print('<setup_async')

    def _stop_asyncDelivery(self):
        # cancell all subscriptions
        #print(f'>_stop_asyncDelivery {list(self.hostDAOs.keys())}')
        for host,daoDict in self.hostDAOs.items():
            aggregatedDAO = list(daoDict.values())
            for dao in aggregatedDAO:
                #print(f'_stop_asyncDelivery {dao}')
                if isinstance(dao,str):
                    continue
                try:
                    dao.Access.unsubscribe()#dao.devPar)
                except Exception as e:
                    printw(f'In unsubscribing {dao.devPar}: {e}')
        
    def _callback(self, *args, **kwargs):
        """Note. ADO provides data dictionary as args[0].
        But EPICS - all in kwargs."""
        with Process_data_Lock:
            #printv(croppedText(f'>DataAccessMonitor.cb:{args,kwargs}'))
            if len(args) > 0:# ADO way
                pars = self._process_data(args[0])
            if len(kwargs) > 0:
                pars = self._process_data(kwargs)
            #print(f'>DataAccessMonitor pars:{pars}')
            self.SignalSourceDataReady.emit(pars)
        
    def _setup_pollingDelivery(self):
        # start the receiving thread
        #print('Call stop_asyncDelivery from setup_pollingDelivery')
        self._stop_asyncDelivery()
        thread = threading.Thread(target=self._thread_proc)
        thread.start()

    def _stop_pollingDelivery(self):
        self.pollingInterval = 0.# this will terminate the polling hread_proc
        time.sleep(.1)

    def _thread_proc(self):
        printi(f'>polling delivery thread ------------------------------')
        while not EventExit.is_set() and self.pollingInterval != 0.:
            # collect data from all hosts and fill daTable with data
            dataReceived = True
            for host,daoDict in self.hostDAOs.items():
                # get values of all parameters from the host
                aggregatedDAO = list(daoDict.values())
                try:
                    access = aggregatedDAO[0].Access
                except KeyError:
                    printw(f'in _thread_proc: DAO disappeared')
                    self.pollingInterval = 0.
                    break
                #print(f'host,dao:{host,aggregatedDAO}')
                if DataAccessMonitor.Perf: ts = timer()
                devPars = [i.devPar for i in aggregatedDAO]
                #printv(f'devPars: {devPars}')
                try:
                    r = access.get(*devPars)
                    #print(f'got:{r}'[:300])
                except Exception as e:
                    msg = f'ERR.PP: failed to get parameters from device {host}: {e}'
                    printw(msg)
                    if Win:
                        Win.update_statusBar(msg)
                        Win.connectionLost(host)
                    dataReceived = False
                    break
                if not isinstance(r,dict):
                    printw('ERR.PP. unexpected response: '+str(r)[:80])
                    break
                if DataAccessMonitor.Perf: print('retrieval time from %s = %.4fs'\
                %(host,timer()-ts))
                
                printv('>thread_proc._process_data')
                self._process_data(r)

            if dataReceived:
                #print(f'SignalSourceDataReady')
                self.SignalSourceDataReady.emit(None)
            EventExit.wait(self.pollingInterval)
        printi('<thread_proc')

    def _process_data(self, devDict):
        # update GUI elements
        #print(f'got:\n{devDict}')
        datAccess = []
        for hostDevParTuple,parDict in devDict.items():
            if hostDevParTuple == 'ppmuser':
                continue
            #if pargs.verbose>1: printv(croppedText(f'update GUI objects of {hostDevParTuple,parDict}'))
            # liteServer returns {'host:dev':{par1:{prop1:{},...},...}},
            def update_pv(hostDevPar, valDict):
                """Update data dictionary of the hostDevPar in the daTable.
                Use dict.append to replace old values"""
                #if pargs.verbose: printv(croppedText(f'par,valDict:{hostDevPar,valDict}'))
                try:
                    daTable = currentDaTable()
                    dataAccess = daTable.par2objAndPos[hostDevPar][0]
                    dataAccess.currentValue = valDict
                    dataAccess.attr['value'] = valDict
                    datAccess.append(hostDevPar)
                except KeyError as e:
                    #printv(f'The hostDevPar {e} is not for current tableWidget')
                    return

            if isinstance(hostDevParTuple,tuple):
                hostDevPar = ':'.join(hostDevParTuple)
                valDict = parDict['value']
                update_pv(hostDevPar, valDict)
            else: #liteServer provide data keyed with hostDev, not devPar
                hostDev = hostDevParTuple
                for par, pd in parDict.items():
                    hostDevPar = hostDev+':'+par
                    update_pv(hostDevPar, pd['value'])
        return datAccess
dataAccessMonitor = DataAccessMonitor()
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Data access object`````````````````````````````````````````
class DataAccess():
    """Base class for accessing Data Access Object (aka EPICS PV).
    Exception is thrown if anything gets wrong.
    """
    Access = None
    Namespace = 'None'

    def __init__(self, cnsNameDev, parName='*', vslice=None):
        self.name = ':'.join((cnsNameDev,parName))
        self.devPar = cnsNameDev,parName
        #printv(f'>DataAccess constructor {self.devPar}')
        self.attr = self.info()
        #printv(f'attr of {self.name}: {self.attr}')
        self.vslice = vslice

    def __str__(self):
        return f'DA({self.name})'
 
    def info(self):
        """Return all attributes of the DAO: value, description etc."""
        return {}

    def set(self,val):
        """Set value of the DAO"""
        printv(f'>set {self.name} to {type(val)} {val}')
        if pargs.readonly:
            printw(f'Cannot set {self.name}: readonly mode') 
            return False
        try:
            ok = DataAccess.Access.set(self.name.rsplit(':',1) + [val])
            printv(f'ok={ok}')
        except Exception as e:
            msg = f'in DataAccess:{e}'
            printw(msg)
            Win.update_statusBar('WRN: '+msg)
            ok = False
        return ok

    def get(self):
        """Get value of the DAO"""
        r = DataAccess.Access.get(self.devPar)
        return tuple(next(iter(r.values())).values())[0]

    def get_guiType(self, features=None):
        """Determine GUI type of the Data Access Object"""
        #self.attr.update(features)
        if features:
            self.attr['features'] = features
        self.guiType = None
        try:    
            v = self.attr['value']
        except: 
            return self.guiType
        #print(f'>gui_type of {self.name}={v}')
        iv = iterable(v)
        #printv(croppedText(f'iv:{iv}'))
        if self.is_editable():
            #printv(croppedText(f'guitype attr:{self.name,self.attr}'))
            if iv[0] == None:
                self.guiType = 'button'
            elif 'legalValues' in self.attr:
                self.guiType =  'combo'
            elif type(iv[0]) in (float,int):
                self.guiType =  'spinbox' if len(iv) == 1 else 'lineEdit'
            elif type(iv[0]) == str:
                self.guiType =  'lineEdit'
            elif type(iv[0]) == bool:
                self.guiType =  'bool'
        #print(f'guiType of {self.name}:{self.guiType}')
        return self.guiType
        
    def is_editable(self):
        #printv(croppedText(f"is_ed {self.name}\n{self.attr}"))
        try:
            page_is_editable = DaTable.CurrentPage.page['editable']
        except Exception as e:
            page_is_editable = True
        if not page_is_editable:
            return False
        try:    r = 'E' in self.attr['features']
        except: r = True
        try:
            if self.name[-4:].upper() == '_RBV':
                r = False
        except: pass
        return r

    def is_readable(self):
        r = 'R' in self.attr['features']
        return r

class DataAccess_epics(DataAccess):
    """Access to EPICS namespace"""
    def info(self):
        try:
            from . import cad_epics# This is standard location
        except:
            from cad_epics import epics as cad_epics
        if DataAccess.Access != cad_epics:
            DataAccess.Access = cad_epics
            printi(f'Imported cad_epics {DataAccess.Access.__version__}')
        DataAccess.Namespace = 'EPICS'
        #devParName = self.name.rsplit(':',1)
        devPar = self.devPar
        r = DataAccess.Access.info(devPar)
        #print(f'info:{r}')
        ret = next(iter(r.values()))
        #print(f'ret:{ret}')
        return ret

class DataAccess_pva(DataAccess):
    """Access to EPICS PVAccess namespace"""
    def info(self):
        try:
            from . import cad_pvaccess# This is standard location
        except:
            from cad_pvaccess import pvaccess as cad_pvaccess
        if DataAccess.Access != cad_pvaccess:
            DataAccess.Access = cad_pvaccess
            printi(f'Imported cad_pvaccess {DataAccess.Access.__version__}')
        DataAccess.Namespace = 'PVA'
        devPar = self.devPar
        r = DataAccess.Access.info(devPar)
        ret = next(iter(r.values()))
        return ret

class DataAccess_lite(DataAccess):
    """Access to liteServer parameters through liteAccess.Access"""
    def info(self):
        import liteaccess
        if DataAccess.Access != liteaccess.Access:
            DataAccess.Access = liteaccess.Access
            printi(f'Imported liteaccess {liteaccess.__version__}')
        DataAccess.Access.set_dbg(max(pargs.verbose-1,0))
        if DataAccess.Access.__version__ < '3.0.0':
            print(f'liteAccess version should be > 3.0.0, not {lAccess.__version__}')
            sys.exit(1)
        DataAccess.Namespace = 'LITE'
        try:
            info = DataAccess.Access.info(self.devPar)
        except Exception as e:
            printe(f'exception getting info for {self.devPar}: {e}')
            sys.exit(1)
        if self.devPar[1] != '*':
            # add 'value' to info
            vdict = DataAccess.Access.get(self.devPar)
            v = vdict[self.devPar]['value']
            info[self.devPar[1]]['value'] = v
        printv(croppedText(f'LITE info({self.devPar}):{info}',300))
        #r = info[self.devPar[0]] if self.devPar[1] == '*'\
        #    else info[self.devPar[0]][self.devPar[1]]
        r = info if self.devPar[1] == '*' else info[self.devPar[1]]
        return r

class DataAccess_ado(DataAccess):
    def info(self):
        printe('DataAccess_ado is not supported by pypeto')
        sys.exit(1)
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Data access table``````````````````````````````````````````
class DaTable():
    """DataAccess table maps: parameter to (row,col) and (row,col) to object"""
    def __init__(self, moduleFile):
        self.par2objAndPos = {}# map of {parameterName:dataAccessObject,[(row,col),vslice]}
        self.pos2obj = {}#      map of {(row,col):dataAccessObject}
        self.deviceMap = {}#    map of {deviceName:[dataAccessObject,...]}
        self.pypage = None
        self.file = None

        self._configModule = None
        maxcol = 0
        configDir = pargs.configDir

        #``````````read conguration file into the config dictionary```````````````
        from importlib import import_module, reload
        moduleFile = moduleFile.replace(configDir,'')
        module = moduleFile.replace('/','.')
        if len(module) == 0:
            sys.exit(0)
        
        try:
            if self._configModule is not None:
                self._configModule = reload(self._configModule)
                printi(f'Module {module} reloaded')
            else:
                #printi(f'importing {module}')
                self._configModule = import_module(module)
        except ModuleNotFoundError as e:
            printe(f'Trying to import {configDir}{moduleFile}.py: {e}')
            sys.exit(0)
        self.file = self._configModule.__file__
        printv(f'Importing {self.file}')
        if pargs.instance is None:
            self.pypage = self._configModule.PyPage()
        else:
            self.pypage = self._configModule.PyPage(instance=pargs.instance)
        print('='*79)
        print(f'file: {self.file}')
        if True:#try:
            rows = self.pypage.rows
            title = self.pypage.title
            #print(f'title: {title}')
        else:#except:
            printe('No entry "_Rows" in the config file')
            sys.exit(0)
        printi(f'Imported: {self.file}')
        #,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
        dead_devices = set()
        def evaluate_string(key):
            # detect if it is a data object, return object and attributes
            rdict = {'obj':key, 'attr':{}}
            printv(f'evaluating string:{key}')
            if key == '':
                return rdict

            #prefix = key[:2]
            #di = {'L:':DataAccess_lite, 'E:':DataAccess_epics, 'P:':DataAccess_pva}.get(prefix)
            #print(f'ns: {self.pypage.namespace.upper()}')
            #if di is not None:
            #    key = key[2:]
            #else:
            if True:
                try:
                    ns = self.pypage.namespace.upper()
                    di = {'LITE':DataAccess_lite, 'EPICS':DataAccess_epics,
                    'PVA':DataAccess_pva, 'ADO':DataAccess_ado}[ns]
                except Exception as e:
                    printe(f'Exception in setting namespace. {e}')
                    sys.exit(1)                
            
            # Check if the string refers to a data object
            # The data object string should contain ':' in the middle
            import string            
            lettersAndDigits = string.ascii_letters+string.digits
            specialChars = '_-.:[];!@#$%&?{}'
            isdao = all(e in lettersAndDigits+specialChars for e in key)
            edgeAreOk = not any(e in ':.<>();\'\"' for e in key[0]+key[-1])
            #printv(f'isdao {key}: {isdao}, edgeAreOk {edgeAreOk}')
            isdao = (isdao and edgeAreOk and ':' in key)

            if isdao:
                printv(f'dao:{key}')
                devPar, vslice = split_slice(key)
                dev,par = devPar.rsplit(':',1)
                #printv(f'dev,par,vslice: {dev,par,vslice}')
                if dev in dead_devices:
                    txt = '?'
                    return {'obj':'?', 'attr':{'color':rgbColorCode(txt)}}
                try:
                    #print(f'dev, par, vslice: {dev, par, vslice}')
                    #print(f'di: {di}')
                    obj = di(dev, par, vslice)
                    rdict['obj'] = obj
                    #printv(croppedText(f'ns:{obj.namespace}, obj {obj.name}:{obj}, attr:{obj.attr}'))
                except ConnectionRefusedError:
                    printw(f'connection refused to {key}')
                    #check if whole device is in question
                    printi(f'check for dead device: {dev,par}')
                    try: #if we cannot access the device version then it is assumed dead
                        r = di(dev, 'version')
                    except:
                        dead_devices.add(dev)
                    return {'obj':'?', 'attr':{}}
                except Exception as e:
                    # do not comment the next line or loose an exception
                    printw(f'Could not access object {key}: {e}')
                    try: #if we cannot access the device version then it is assumed dead
                        r = di(dev, 'version')
                    except:
                        dead_devices.add(dev)
                    return {'obj':'?', 'attr':{}}

                # for table we need only obj, desc, initial and features
                value = obj.attr.get('value')
                #print(f'vslice: {vslice}, value:{value}')
                if vslice is not None:
                    initial = value[vslice[0]:vslice[1]]
                else:
                    initial = value
                rdict['attr'] = {
                  'desc': obj.attr.get('desc',''),
                  'initial': initial}
                #print(croppedText(f"ra:{rdict['attr']}, {obj.attr.get('features')}"))
                try:
                    rdict['attr']['features'] = obj.attr['features']
                except: pass
            return rdict

        def evaluate_cell(cell):
            """Evaluate cell detect if it is data access object,
            collect object's features and combine them with the cell's 
            attributes."""
            if isinstance(cell, str):
                return evaluate_string(cell)
            rdict = {'obj':None, 'attr':{}}
            if isinstance(cell, int):   # ignore int
                return rdict
            printv(f'cell:{cell}')
            if not isinstance(cell, dict):
                printw(f'Cell is {type(cell)} not dict: {cell}')
                return rdict

            # cell is  dict
            key,attr = next(iter(cell.items()))
            #printv(f'key,attr:{key,attr}')            
            rdict = evaluate_string(key)
            # combine (and replace if same) with the cell's attributes
            rdict['attr'].update(attr)
            return rdict

        for row,rlist in enumerate(rows):
            if rlist is None:
                continue
            #if pargs.verbose: printv(croppedText(f'row,rlist:{row,rlist}', 500))
            nCols = len(rlist)

            rowAttr = {}
            col = -1
            for cell in rlist: 
                col += 1
                #if pargs.verbose: 
                #printv( croppedText(f'processing cell:{cell}'))
                cdict = evaluate_cell(cell)
                #if pargs.verbose: print(croppedText(f'registered obj{row,col}: {cdict}'))
                obj = cdict['obj']

                if col == 0 and obj == 'ATTRIBUTES':
                    rowAttr = cdict['attr']
                    col -= 1
                    nCols -= 1
                    continue
                
                cellAttr = rowAttr.copy()
                cellAttr.update(cdict['attr'])
                #print(f'cellAttr:{row,col,cellAttr}')
                self.pos2obj[(row,col)] = obj, cellAttr.copy()
                
                if issubclass(type(obj), DataAccess):
                    dev,par = obj.name.rsplit(':',1)

                    # do not request configuration parameters
                    try:
                        printv(f"features:{obj.attr['features']}")
                        f = obj.attr.get('features')
                        if f:
                            if 'C' in f:
                                printi(f'Not requested config parameter {dev,par}')
                                continue
                        if obj.attr['value'] is None:
                            printv(f'Not requested None parameter {dev,par}')
                            continue
                    except Exception as e:
                        printw(f'exception in attr of {dev,par}: {e}')
                        continue

                    #if pargs.verbose: print(croppedText(f'requesting dev.par:{dev,par}, {obj.attr}'))
                    if dev in self.deviceMap:
                        self.deviceMap[dev][obj.name] = obj
                    else: self.deviceMap[dev] = {obj.name:obj}

            maxcol = max(maxcol,nCols)
            row += 1

        self.shape = row,maxcol
        printv( f'daTable created, shape: {self.shape}')
        #for key,value in self.pos2obj.items(): print(f'{key}:{value}')
        printv(croppedText(f'deviceMap:{self.deviceMap}'))

def build_temporary_pvfile(cnsName):
    module = '_Device_pp'
    fname = pargs.configDir+f'{module}.py'
    def open_tmpFile():
        f = open(fname,'w')
        return f
        
    printi('>build_temporary_pvfile')
    printi(f'namespace: {pargs.access} CNS: {cnsName}')
    ns = pargs.access.upper()
    if ns in ['EPICS','PVA']:
        printe('-EPICS does not support device introspection')
        sys.exit(1)
    elif    ns == 'ADO':
        da = DataAccess_ado(cnsName)
        cnsInfo = da.attr
    elif    ns == 'LITE':
        da = DataAccess_lite(cnsName)
        cnsInfo = da.attr
    else:
        printe(f'Not supported data object access interface: {pargs.access}')
        sys.exit(None)
    if len(cnsInfo) == 0:
        printe(f'The {cnsName} is not a valid data object')
        sys.exit(None)
    printv(croppedText(f'cnsInfo: {cnsInfo}'))

    f = open_tmpFile()
    content = (
f'#Automatically created configuration file for {AppName}, Version 3.0.0.\n'
f'class PyPage():\n'
f'    def __init__(self, **_):\n'
f'        dev = "{cnsName}"\n'
 '        self.namespace = "LITE"\n'
f'        self.title = "{cnsName}"\n'
 '        self.columns = {\n'
 '          1: {"justify": "center", "color": [220,220,220]},\n'
 '          2: {"width": 100},\n'
 '        }\n'
 '        self.rows = [\n'
    )
    #ignored = []#('fecName',)
    for parName in cnsInfo:
        #if parName in ignored:
        #    continue
        content += f'["{parName}", dev+":{parName}"],\n'

    content  += ']\n'
    f.write(content)
    f.close()
    printi(f'Temporary module created: {fname}')
    return module
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#`````````````````````````````````````````````````````````````````````````````
def run():
    global Win
    sys.path.append(pargs.configDir)

    # the --zoom should be handled prior to QtWidgets.QApplication
    for i,argv in enumerate(sys.argv):
        if argv.startswith('-z'):
            zoom = argv[2:]
            if zoom == '':
                zoom = sys.argv[i+1]
            print(f'zoom: `{zoom}`')
            os.environ["QT_SCALE_FACTOR"] = zoom
            break
    qApp = QApplication([])

    if pargs.files:
        # add _pp suffix to filenames
        for i,f in enumerate(pargs.files):
            if pargs.files[i][-3:] != '_pp':
                pargs.files[i] += '_pp'
    else:
        if pargs.device:
            printw(('The dao have been provided in the command line,\n'\
            ' local configuration will be build'))
            moduleFile = build_temporary_pvfile(pargs.device)
            pargs.files = [moduleFile]
        else:
            pargs.files = select_files_interactively(pargs.configDir)
            printv(f'pargs.files: {pargs.files}')
            l = len(pargs.configDir)
            if pargs.files[0][:l] == pargs.configDir:
                pargs.files[0] = pargs.files[0][l:]

    # Instantiate the GUI
    Win = Window()

    if pargs.restore:
        #dataAccessMonitor.setup_dataDelivery('Stopped')
        pass
    else:
        dataAccessMonitor.setup_dataDelivery('Asynchronous')

    # arrange keyboard interrupt to kill the program
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    #start GUI
    try:
        qApp.instance().exec_()
        #sys.exit(qApp.exec_())
    except Exception as e:#KeyboardInterrupt:
        # # This exception never happens
        printi('keyboard interrupt: exiting')
    dataAccessMonitor.setup_dataDelivery('Stopped')
    EventExit.set()

