import sys
import os.path
import datetime
import zlib

from PySide6.QtWidgets import (QApplication, QDialog, QPushButton, QMainWindow,
        QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
        QListWidget, QListWidgetItem, QPlainTextEdit, QLineEdit, QFileDialog,
        QLabel, QFrame, QLayout, QSizePolicy, QHeaderView, QAbstractItemView,
        QSlider, QCheckBox)
from PySide6.QtCore import (Slot, Signal, Qt, QObject, QCoreApplication)
from PySide6.QtGui import (QAction, QPalette, QColor)
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.widgets as mwidgets

from dsc import parse_tabulated_txt, DSCData, SAVGOL_POLYORDER
from util import get_encoding_type
from dsc_analysis import DSCAnalysis
from dsc_serialize import store_dsc, restore_dsc

class LoggingHandle(QObject):
    log_signal = Signal(str)
    def __init__(self):
        QObject.__init__(self)

    @Slot(str)
    def log_slot(self, msg : str):
        self.log_signal.emit(msg)

class ConfirmDialog(QDialog):
    def __init__(self, msg):
        QDialog.__init__(self)
        self.vlayout = QVBoxLayout(self)

        self.buttons_frame = QFrame()
        self.hlayout = QHBoxLayout(self.buttons_frame)
        self.yes_button = QPushButton("Yes")
        self.no_button = QPushButton("No")

        self.hlayout.addWidget(self.yes_button)
        self.hlayout.addWidget(self.no_button)

        self.dialog_msg = QLabel(msg)

        self.vlayout.addWidget(self.dialog_msg)
        self.vlayout.addWidget(self.buttons_frame)

        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)

class PerformSmoothingDialog(QDialog):
    smoothing_changed = Signal(bool, int)

    def __init__(self):
        QDialog.__init__(self)
        self.layout = QHBoxLayout(self)

        self.checkbox = QCheckBox('Savitzky-Golay Filtering (1st Derivative)'
            ' - Window Size:')
        self.slider = QSlider()
        self.slider.setMinimum(SAVGOL_POLYORDER + 1)
        self.slider.setMaximum(SAVGOL_POLYORDER + 7)
        self.slider.setSingleStep(1)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider_label = QLabel(str(self.slider.value()))

        self.slider.valueChanged.connect(self.update_slider_value)
        self.checkbox.stateChanged.connect(self.update_checkbox_value)

        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.slider_label)

    def update_slider_value(self, value : int):
        self.slider_label.setText(str(value))
        self.smoothing_changed.emit(self.checkbox.isChecked(),
            self.slider.value())

    def update_checkbox_value(self, value : int):
        self.smoothing_changed.emit(self.checkbox.isChecked(),
            self.slider.value())

ui_log = LoggingHandle()
def log_ui(msg : str):
    ui_log.log_slot(msg)

# Main Window
class UI_MainWindow(QMainWindow):
    loaded_data = Signal(DSCData)
    changed_name = Signal(str)
    new_analysis = Signal()
    del_analysis = Signal()

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle('PyDSC')
        #self.setWindowIcon()

        self.active_files = []
        self.active_file_name = ''
        self.active_file = None
        self.data = None
        self.dscanalysis = DSCAnalysis()

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('File')
        self.analysis_menu = self.menu.addMenu('Analysis')
        self.dsc_button = QPushButton()
        self.tg_button = QPushButton()

        ### Actions
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        self.file_menu.addAction(open_action)

        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        self.file_menu.addAction(save_action)

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.exit_app)
        self.file_menu.addAction(exit_action)

        new_tg_action = QAction('New Tg Analysis', self)
        new_tg_action.setShortcut('Ctrl+T')
        new_tg_action.triggered.connect(self.new_tg_analysis)
        self.analysis_menu.addAction(new_tg_action)

        new_peak_action = QAction('New Peak Analysis', self)
        new_peak_action.setShortcut('Ctrl+V')
        new_peak_action.triggered.connect(self.new_peak_analysis)
        self.analysis_menu.addAction(new_peak_action)

        del_action = QAction('Delete Selected Analysis', self)
        del_action.setShortcut('Delete')
        del_action.triggered.connect(self.del_analysis)
        self.analysis_menu.addAction(del_action)

        esc_action = QAction('Escape Analysis', self)
        esc_action.setShortcut('Escape')
        esc_action.triggered.connect(self.cancel_analysis)
        self.analysis_menu.addAction(esc_action)

        togg_1deriv_action = QAction('Toggle 1st Derivative Plot', self)
        togg_1deriv_action.setShortcut('Ctrl+1')
        self.analysis_menu.addAction(togg_1deriv_action)

        smooth_action = QAction('Smoothing Dialog', self)
        smooth_action.setShortcut('Ctrl+2')
        smooth_action.triggered.connect(self.smooth_dialog)
        self.analysis_menu.addAction(smooth_action)

        ### Central Widget
        self.pydsc = UI_PyDSC()
        self.setCentralWidget(self.pydsc)

        togg_1deriv_action.triggered.connect(self.pydsc.dscplot.toggle_1deriv)

        self.loaded_data.connect(self.pydsc.dscplot.load_data)
        self.loaded_data.connect(self.pydsc.results.load_data)
        self.loaded_data.connect(self.pydsc.projectinfo.receive_dsc)

        self.new_analysis.connect(self.dscanalysis.prepare_new_analysis)
        self.del_analysis.connect(self.dscanalysis.del_analysis)

        self.pydsc.dscplot.analysis_made.connect(
            self.dscanalysis.receive_analysis)
        self.pydsc.dscplot.canceled_analysis.connect(
            self.dscanalysis.cancel_new_analysis)
        self.pydsc.dscplot.reperform_analyses.connect(
            self.dscanalysis.update_all_analyses)

        self.pydsc.results.analysis_name_changed.connect(
            self.dscanalysis.change_analysis_name)
        self.pydsc.projectinfo.notes_changed.connect(
            self.notes_changed)

        self.dscanalysis.update_current_analysis.connect(
            self.pydsc.dscplot.display_analysis)
        self.dscanalysis.update_current_analysis.connect(
            self.pydsc.dscplot.update_selector)
        self.dscanalysis.update_current_analysis.connect(
            self.pydsc.results.receive_analysis)
        self.pydsc.analyses.analysis_list.currentRowChanged.connect(
            self.dscanalysis.switch_analysis)
        self.dscanalysis.add_analysis_display.connect(
            self.pydsc.analyses.add_analysis_display)
        self.dscanalysis.del_analysis_display.connect(
            self.pydsc.analyses.del_analysis_display)
        self.dscanalysis.send_change_analysis_name.connect(
            self.pydsc.analyses.change_analysis_name)
        self.dscanalysis.load_analysis_display.connect(
            self.pydsc.analyses.load_analysis_display)

        # XXX drag and drop?
        # self.setAcceptDrops(True)

    def notes_changed(self, text : str):
        if self.data is None:
            return
        self.data.notes = text

    def new_tg_analysis(self, s):
        self.pydsc.dscplot.new_selector('tg')
        self.new_analysis.emit()

    def new_peak_analysis(self, s):
        self.pydsc.dscplot.new_selector('peak')
        self.new_analysis.emit()

    def cancel_analysis(self, s):
        self.pydsc.dscplot.update_selector(None)

    def smooth_dialog(self, s):
        dialog = PerformSmoothingDialog()
        dialog.smoothing_changed.connect(self.pydsc.dscplot.update_smoothing)
        dialog.exec()

    def save_file(self, s):
        if self.data is None:
            log_ui('Save attempted with no data loaded')
            return
        save_dialog = QFileDialog()
        save_dialog.setFileMode(QFileDialog.AnyFile)
        save_dialog.setViewMode(QFileDialog.Detail)
        save_dialog.setNameFilter('PyDSC Format (*.pdsc)')

        save_files = []
        if save_dialog.exec():
            save_files = save_dialog.selectedFiles()

        if len(save_files):
            save_file_name = self.save_files[0]
            if not save_files[0].endswith('.pdsc'):
                save_file_name = save_file_name+'.pdsc'
            data_to_write = zlib.compress(store_dsc(self.data,
                self.dscanalysis).encode())
            with open(save_file_name, 'wb') as f:
                f.write(data_to_write)

    def open_file(self, s):
        if self.active_file:
            confirm_dialog = ConfirmDialog(
                "Opening a new file will overwrite current data. Proceed?")
            res = confirm_dialog.exec()
            if res == QDialog.Rejected:
                return
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter('Tabulated text (*.txt);'
            ';PyDSC file (*.pdsc)')
        file_dialog.setViewMode(QFileDialog.Detail)

        if file_dialog.exec():
            self.active_files = file_dialog.selectedFiles()

        if len(self.active_files):
            file_to_open = self.active_files[0]

            if file_to_open.endswith('.txt'):
                self.read_txt(file_to_open)
            elif file_to_open.endswith('.pdsc'):
                self.read_pdsc(file_to_open)

    def read_txt(self, file_to_open : str):
        self.active_file = open(file_to_open,
            encoding = get_encoding_type(file_to_open))
        text = self.active_file.read()
        self.active_file_name = file_to_open

        self.data = parse_tabulated_txt(text)
        self.data.name = os.path.splitext(\
            os.path.basename(self.active_file_name))[0]

        self.loaded_data.emit(self.data)

    def read_pdsc(self, file_to_open : str):
        self.active_file = open(file_to_open, 'rb')
        read_bin = zlib.decompress(self.active_file.read())
        read_data, read_analysis = restore_dsc(read_bin)
        self.active_file_name = file_to_open

        self.data = read_data

        self.loaded_data.emit(self.data)
        self.dscanalysis.load_analysis(read_analysis)

    def exit_app(self, s):
        QApplication.quit()

class UI_Analyses(QFrame):

    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.layout = QVBoxLayout(self)

        self.analysis_list = QListWidget()
        self.analysis_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.layout.addWidget(QLabel('Analysis'))
        self.layout.addWidget(self.analysis_list)

    @Slot(int, str)
    def change_analysis_name(self, row : int, name : str):
        if self.analysis_list.item(row) is None:
            return
        self.analysis_list.item(row).setText(name)

    @Slot()
    def clear_analysis_display(self):
        self.analysis_list.clear()

    @Slot(list)
    def load_analysis_display(self, ana : list):
        self.clear_analysis_display()
        for a in ana:
            self.add_analysis_display(a)

    @Slot(dict)
    def add_analysis_display(self, ana : dict):
        item = QListWidgetItem(ana['name'])
        item.setFlags(~Qt.ItemIsEditable)
        self.analysis_list.addItem(item)

    @Slot(int)
    def del_analysis_display(self, row : int):
        self.analysis_list.takeItem(row)

# Read-only results for current analysis item
class UI_Results(QFrame):
    analysis_name_changed = Signal(str)

    def __init__(self):
        QFrame.__init__(self)
        self.layout = QVBoxLayout(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.data = None
        self.editable_name_idx = None

        # Setup widgets
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setVerticalHeaderLabels(['Name','Value'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self.handle_name_change)

        # Layout widgets
        self.layout.addWidget(QLabel('Details'))
        self.layout.addWidget(self.table)

    def load_data(self, data : DSCData):
        self.data = data

    def handle_name_change(self, item):
        if item.row() == self.editable_name_idx and item.column() == 1:
            self.analysis_name_changed.emit(item.text())

    @Slot(dict)
    def receive_analysis(self, ana):
        self.table.clearContents()
        if ana is None:
            return
        row_idx = 0
        ref_ana = self.reformat_analysis(ana)
        self.table.setRowCount(len(ref_ana.items()))
        for k,v in ref_ana.items():
            l_item = QTableWidgetItem(str(k))
            r_item = QTableWidgetItem(str(v))
            l_item.setFlags(~Qt.ItemIsEditable)
            r_item.setFlags(~Qt.ItemIsEditable)
            if (k == 'Name'): # Only name is editable
                r_item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.editable_name_idx = row_idx
            self.table.setItem(row_idx, 0, l_item)
            self.table.setItem(row_idx, 1, r_item)
            row_idx += 1

    def reformat_analysis(self, ana : dict):
        ret = {}
        ret['Name'] = ana['name']
        ret['Mode'] = 'Glass transition' if ana['mode'] == 'tg' else \
               'Peak analysis'
        if ana['mode'] == 'tg':
            ret['Mode'] = 'Glass transition'
            tg = ana['tg']
            ret['Inflection temperature [C]'] = self.data[tg['tig_idx']][0]
            ret['Inflection heatflow [mW]'] = self.data[tg['tig_idx']][1]
            ret['Extrapolated onset temperature [C]'] = \
                    self.data[tg['tf_idx']][0]
            ret['Extrapolated onset heatflow [mW]'] = \
                    self.data[tg['tf_idx']][1]
            ret['Midpoint temperature [C]'] = self.data[tg['tm_idx']][0]
            ret['Midpoint heatflow [mW]'] = self.data[tg['tm_idx']][1]
        elif ana['mode'] == 'peak':
            pk = ana['peak']
            ret['Mode'] = 'Peak analysis'
            ret['Peak temperature [C]'] = self.data[pk['peak_idx']][0]
            ret['Peak heatflow [mW]'] = self.data[pk['peak_idx']][1]
            ret['Onset temperature [C]'] = self.data[pk['onset_Tr_idx']][0]
            ret['Onset heatflow [mW]'] = self.data[pk['onset_Tr_idx']][1]
            ret['Offset temperature [C]'] = self.data[pk['offset_Tr_idx']][0]
            ret['Offset heatflow [mW]'] = self.data[pk['offset_Tr_idx']][1]
            ret['Enthalpy [mW]'] = pk['enthalp_area']
        return ret

class UI_DSCPlot(QFrame):
    analysis_made = Signal(dict)
    canceled_analysis = Signal()
    reperform_analyses = Signal(DSCData)

    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)

        self.fig = Figure(constrained_layout=True)
        self.ax = self.fig.add_subplot()
        self.ax.set_xlabel('Tr')
        self.ax.set_ylabel('Heatflow')

        self.layout = QVBoxLayout(self)

        self.data = None

        self.tg_analyses_num = 1
        self.peak_analyses_num = 1

        self.plot_lines = None
        self.plot1deriv_lines = None
        self.overlay_lines = []

        self.mode = 'tg'

        self.selector = mwidgets.RectangleSelector(self.ax, self.selector_hook,
            useblit = True, interactive=True)
        self.selector.set_active(False) # Selector is inactive by default
        self.update_selector_props()

        # Setup widgets
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plot_label = QLabel('Plot')

        self.plot_label.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.canvas.mpl_connect('motion_notify_event', self.motion_notify_hook)

        # Layout widgets
        self.layout.addWidget(self.plot_label)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)

    def update_smoothing(self, active : bool, window : int):
        if self.data is None:
            return
        print(active, window)
        self.data.savgol_1_enabled = active
        self.data.savgol_1_window = window
        self.data.prepare_extra()

        # Replot all lines
        plot1deriv = True if self.plot1deriv_lines else False
        self.clear_graph()
        self.ax.plot(self.data.Tr, self.data.Heatflow)
        if plot1deriv:
            self.plot1deriv_lines = self.ax.plot(
                self.data.Tr, self.data.Heatflow1Deriv)

        # Re-perform all analyses
        self.reperform_analyses.emit(self.data)

        self.canvas.draw()
        pass

    def toggle_1deriv(self):
        if self.data is None:
            return
        if self.plot1deriv_lines is None:
            self.plot1deriv_lines = self.ax.plot(
                self.data.Tr, self.data.Heatflow1Deriv)
            self.canvas.draw()
        else:
            l = self.plot1deriv_lines.pop(0)
            l.remove()
            self.plot1deriv_lines = None
            self.canvas.draw()

    # Sets mode but does not position selector
    def new_selector(self, mode : str):
        self.mode = mode
        self.selector.set_active(True)

    # Sets mode and positions selector according to extents
    def update_selector(self, ana : dict):
        if ana is None:
            self.mode = None
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.canvas.draw()
            return
        self.selector.extents = ana['extents']
        self.mode = ana['mode']
        self.selector.set_active(True)
        self.selector.set_visible(True)
        self.canvas.draw()

    def selector_hook(self, eclick, erelease):
        extents = self.selector.extents
        try:
            if not self.data:
                raise Exception('No data to select')
            if self.mode == 'tg':
                tg = self.data.tg_detect2(extents[0], extents[1])
                self.analysis_made.emit({'name': 'Glass Transition Analysis',
                    'mode':self.mode, 'extents':extents, 'tg':tg})
            elif self.mode == 'peak':
                pk = self.data.peak_detect(extents[0], extents[1])
                self.analysis_made.emit({'name': 'Peak Analysis',
                    'mode':self.mode, 'extents':extents, 'peak':pk})
        except Exception as e:
            self.canceled_analysis.emit()
            log_ui('Selection failed: '+str(e))
            raise

    def update_selector_props(self):
        if self.mode == 'tg':
            self.selector.set_props(facecolor='blue', alpha=0.1)
        elif self.mode == 'peak':
            self.selector.set_props(facecolor='green', alpha=0.1)

    def clear_overlay_lines(self):
        for line in self.overlay_lines:
            l = line.pop(0)
            l.remove()
        self.overlay_lines = []

    def display_analysis(self, ana : dict):
        self.clear_overlay_lines()
        if ana is None:
            return
        if ana['mode'] == 'tg':
            tg = ana['tg']
            self.overlay_lines += self.ax.plot(
                self.data[tg['tig_idx']][0],
                self.data[tg['tig_idx']][1], 'ro')
            self.overlay_lines += self.ax.plot(
                self.data[tg['tf_idx']][0],
                self.data[tg['tf_idx']][1], 'go')
            self.overlay_lines += self.ax.plot(
                self.data[tg['tm_idx']][0],
                self.data[tg['tm_idx']][1], 'bo')
        elif ana['mode'] == 'peak':
            pk = ana['peak']
            self.overlay_lines += self.ax.plot(
                self.data[pk['peak_idx']][0],
                self.data[pk['peak_idx']][1], 'ro')
            self.overlay_lines += self.ax.plot(
                self.data[pk['offset_Tr_idx']][0],
                self.data[pk['offset_Tr_idx']][1], 'go')
            self.overlay_lines += self.ax.plot(
                self.data[pk['onset_Tr_idx']][0],
                self.data[pk['onset_Tr_idx']][1], 'go')

    def motion_notify_hook(self, event):
        if self.selector.active: # Draw rectangle
            self.canvas.draw()

    def clear_graph(self):
        if self.plot_lines:
            l = self.plot_lines.pop(0)
            l.remove()
            self.plot_lines = None
        if self.plot1deriv_lines:
            l = self.plot1deriv_lines.pop(0)
            l.remove()
            self.plot1deriv_lines = None
        self.clear_overlay_lines()

    def load_data(self, data : DSCData):
        self.clear_graph()

        data.prepare_extra()
        self.data = data
        self.plot_obj = self.ax.plot(data.Tr, data.Heatflow)
        self.canvas.draw()

class UI_ProjectInfo(QFrame):
    notes_changed = Signal(str)

    def __init__(self):
        QFrame.__init__(self)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.layout = QVBoxLayout(self)
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Setup widgets
        self.open_name = QLabel('')
        self.open_name.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status_bar = QLabel('')
        self.status_bar.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status_bar.setWordWrap(True)
        self.status_bar.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Layout widgets
        self.layout.addWidget(QLabel('Project Info'))
        self.layout.addWidget(QLabel('Name'))
        self.layout.addWidget(self.open_name)
        self.layout.addWidget(QLabel('Notes'))
        self.layout.addWidget(self.note_edit)
        self.layout.addWidget(QLabel('Status'))
        self.layout.addWidget(self.status_bar)
        self.update_status('PyDSC loaded')

        self.note_edit.textChanged.connect(self.notes_changed_slot)
        ui_log.log_signal.connect(self.update_status)

    @Slot()
    def notes_changed_slot(self):
        self.notes_changed.emit(self.note_edit.toPlainText())

    @Slot(DSCData)
    def receive_dsc(self, data : DSCData):
        self.open_name.setText(data.name)
        self.update_status('Loaded '+data.name)
        self.note_edit.setPlainText(data.notes)

    @Slot(str)
    def update_status(self, msg):
        self.status_bar.setText(msg + ' | ' +
                datetime.datetime.now().strftime('%H:%M:%S'))

# Central Widget
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

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = UI_MainWindow()
    window.resize(1600,800)
    window.show()
    sys.exit(app.exec())
