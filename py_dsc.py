import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QTableWidget, QListWidget, QPlainTextEdit, QLineEdit,
    QFileDialog)
from PySide6.QtCore import (Slot, Signal, QStringList)

# Main Window
class UI_MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("PyDSC")
        #self.setWindowIcon()

        self.open_file = QStringList()

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        ### Actions
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        self.file_menu.addAction(open_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_app)
        self.file_menu.addAction(exit_action)

        # drag and drop
        # self.setAcceptDrops(True)

    @Slot()
    def open_file(self, checked):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Tabulated text (*.txt)")
        file_dialog.setViewMode(QFileDialog.Detail)
        if file_dialog.exec():
            self.open_file = file_dialog.selectedFiles()

    @Slot()
    def exit_app(self, checked):
        QApplication.quit()

class UI_Analyses(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Setup widgets
        self.analysis_list = QListWidget()

        # Layout widgets
        self.layout.addWidget(QLabel("Analysis")
        self.layout.addWidget(self.analysis_list)

# Read-only results for current analysis item
class UI_Results(QWidget):
    def __init__(self)
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Setup widgets
        self.table = QTableWidget()
        self.table.setColumnCount(2)

        # Layout widgets
        self.layout.addWidget(QLabel("Details"))
        self.layout.addWidget(self.table)

    @Slot(dict)
    def update_results(self, data):
        self.table.clear()
        items_idx = 0
        for k,v in data.items():
            self.table.insertRow(items_idx)
            self.table.setItem(items_idx, 0, QTableWidgetItem(str(k)))
            self.table.setItem(items_idx, 1, QTableWidgetItem(str(v)))
            items_idx += 1
        pass

class UI_ProjectData(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Setup widgets
        self.name_edit = QLineEdit()
        self.text_edit = QPlainTextEdit()

        # Layout widgets
        self.layout.addWidget(QLabel("Project Data"))
        self.layout.addWidget(QLabel("Name"))
        self.layout.addWidget(self.name_edit)
        self.layout.addWidget(self.text_edit)

# PyDSC Widget (area of most interaction)
class UI_PyDSC(QWidget):
    def __init__(self)
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        ### Setup widgets
        # Analyses/Results
        self.analyses = UI_Analyses()
        self.results = UI_Details()
        # TODO Connect analyses selection/change in item to results
        # TODO Connect analyses selection/change in item to matplotlib

        # Matplotlib
        # Project Data
        self.project_data = UI_ProjectData()

        ### Layout widgets
        self.layout.addWidget(self.analyses)
        self.layout.addWidget(self.results)
        self.layout.addWidget(self.project_data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pydsc = UI_PyDSC()
    window = UI_MainWindow()
    window.resize(800,600)
    window.show()
    sys.exit(app.exec())
