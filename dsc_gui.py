import sys
import os.path
import datetime

from PySide6.QtWidgets import (QApplication, QPushButton, QMainWindow, QWidget,
        QHBoxLayout, QVBoxLayout, QTableWidget, QListWidget, QPlainTextEdit,
        QLineEdit, QFileDialog, QLabel, QFrame, QLayout, QSizePolicy)
from PySide6.QtCore import (Slot, Signal, Qt)
from PySide6.QtGui import (QAction, QPalette, QColor)
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.widgets as mwidgets

from dsc import parse_tabulated_txt, DSCData
from util import get_encoding_type

# Main Window
class UI_MainWindow(QMainWindow):
    loaded_tab = Signal(DSCData)
    changed_name = Signal(str)

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("PyDSC")
        #self.setWindowIcon()

        self.active_files = []
        self.active_file_name = ""
        self.active_file = None
        self.data = None

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.dsc_button = QPushButton()
        self.tg_button = QPushButton()

        ### Actions
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        self.file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        self.file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_app)
        self.file_menu.addAction(exit_action)

        new_tg_action = QAction("New Tg Analysis", self)
        new_tg_action.setShortcut("Ctrl+T")
        new_tg_action.triggered.connect(self.new_tg_analysis)

        new_peak_action = QAction("New Peak Analysis", self)
        new_peak_action.setShortcut("Ctrl+V")
        new_peak_action.triggered.connect(self.new_peak_analysis)

        del_action = QAction("Delete Selected Analysis", self)
        del_action.setShortcut("Delete")

        ### Central Widget
        self.pydsc = UI_PyDSC()
        self.setCentralWidget(self.pydsc)

        self.loaded_tab.connect(self.pydsc.dscplot.plot)
        self.loaded_tab.connect(self.pydsc.projectinfo.receive_dsc)

        # drag and drop
        # self.setAcceptDrops(True)

    def new_tg_analysis(self, s):
        pass

    def new_peak_analysis(self, s):
        pass

    def save_file(self, s):
        pass

    def open_file(self, s):
        # TODO prompt save
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Tabulated text (*.txt)")
        file_dialog.setViewMode(QFileDialog.Detail)

        if file_dialog.exec():
            self.active_files = file_dialog.selectedFiles()

        if len(self.active_files):
            file_to_open = self.active_files[0]
            self.active_file_name = file_to_open
            self.active_file = open(file_to_open,
                encoding = get_encoding_type(file_to_open))
            text = self.active_file.read()

            self.data = parse_tabulated_txt(text)
            self.data.name = os.path.basename(self.active_file_name)

            self.loaded_tab.emit(self.data)

    def exit_app(self, s):
        QApplication.quit()

class UI_Analyses(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.layout = QVBoxLayout(self)

        # Setup widgets
        self.analysis_list = QListWidget()

        # Layout widgets
        self.layout.addWidget(QLabel("Analysis"))
        self.layout.addWidget(self.analysis_list)

# Read-only results for current analysis item
class UI_Results(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.layout = QVBoxLayout(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        # Setup widgets
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setVerticalHeaderLabels(["Name","Value"])

        # Layout widgets
        self.layout.addWidget(QLabel("Details"))
        self.layout.addWidget(self.table)

    @Slot(dict)
    def update_results(self, data):
        self.table.clearContents()
        items_idx = 0
        for k,v in data.items():
            self.table.insertRow(items_idx)
            self.table.setItem(items_idx, 0, QTableWidgetItem(str(k)))
            self.table.setItem(items_idx, 1, QTableWidgetItem(str(v)))
            items_idx += 1
        pass

class UI_DSCPlot(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)

        self.fig = Figure(constrained_layout=True)
        self.ax = self.fig.add_subplot()
        self.ax.set_xlabel('Tr')
        self.ax.set_ylabel('Heatflow')
        self.layout = QVBoxLayout(self)

        ### XXX Test
        self.selector = mwidgets.RectangleSelector(self.ax,
            lambda eclick, erelease: print(eclick, erelease),
            minspanx = 0.1, minspany = 0.1, useblit = True,
            props={'facecolor':'blue', 'alpha':0.1}, interactive=True)

        # Setup widgets
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Layout widgets
        self.layout.addWidget(QLabel("Plot"))
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)

    def plot(self, data : DSCData):
        self.ax.plot(data.Tr, data.Heatflow)
        self.canvas.draw()
        pass

class UI_ProjectInfo(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.layout = QVBoxLayout(self)
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Setup widgets
        self.open_name = QLabel("")
        self.open_name.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status_bar = QLabel("")
        self.status_bar.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status_bar.setWordWrap(True)
        self.status_bar.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Layout widgets
        self.layout.addWidget(QLabel("Project Info"))
        self.layout.addWidget(QLabel("Name"))
        self.layout.addWidget(self.open_name)
        self.layout.addWidget(QLabel("Notes"))
        self.layout.addWidget(self.note_edit)
        self.layout.addWidget(QLabel("Status"))
        self.layout.addWidget(self.status_bar)
        self.update_status("PyDSC loaded")

    @Slot(DSCData)
    def receive_dsc(self, data : DSCData):
        self.open_name.setText(data.name)
        self.update_status("Loaded "+data.name)
        self.note_edit.setPlainText(data.notes)

    @Slot(str)
    def update_status(self, msg):
        self.status_bar.setText(msg + " | " +
                datetime.datetime.now().strftime('%H:%M:%S'))

# PyDSC Widget (area of most interaction)
class UI_PyDSC(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout(self)

        ### Setup widgets
        # Analyses/Results
        self.analyses_results_frame = QFrame()
        self.analyses_results_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.analyses_results_layout = QVBoxLayout(self.analyses_results_frame)

        self.analyses = UI_Analyses()
        self.results = UI_Results()

        # Matplotlib
        self.dscplot = UI_DSCPlot()

        # Project Info
        self.projectinfo = UI_ProjectInfo()

        ### Layout widgets
        self.analyses_results_layout.addWidget(self.analyses)
        self.analyses_results_layout.addWidget(self.results)
        self.layout.addWidget(self.analyses_results_frame)
        self.layout.addWidget(self.dscplot)
        self.layout.addWidget(self.projectinfo)

        ### Connect signals

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = UI_MainWindow()
    window.resize(1200,600)
    window.show()
    sys.exit(app.exec())
