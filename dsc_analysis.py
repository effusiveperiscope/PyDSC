from PySide6.QtCore import (Slot, Signal, Qt, QObject, QCoreApplication)
class DSCAnalysis(QObject):
    update_current_analysis = Signal(dict)
    add_analysis_display = Signal(dict)
    load_analysis_display = Signal(list)
    del_analysis_display = Signal(int)
    send_change_analysis_name = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.analyses = []
        self.current_analysis = None
        self.current_analysis_index = None
        self.new_analysis_mode = False

        self.tg_analyses_num = 1
        self.peak_analyses_num = 1

    def get_analysis_num(self, mode):
        ret = 0
        if mode == 'tg':
            ret = self.tg_analyses_num
            self.tg_analyses_num += 1
            return ret
        elif mode == 'peak':
            ret = self.peak_analyses_num
            self.peak_analyses_num += 1
            return ret
        else:
            raise Exception('Invalid mode')
    
    def change_analysis_name(self, name : str):
        if self.current_analysis is None:
            return
        self.current_analysis['name'] = name
        self.send_change_analysis_name.emit(
            self.current_analysis_index, name)

    def add_analysis(self, ana : dict):
        self.analyses.append(ana)

        self.current_analysis = self.analyses[-1]
        self.current_analysis_index = len(self.analyses) - 1

        self.update_current_analysis.emit(self.current_analysis)
        self.add_analysis_display.emit(self.current_analysis)

    def load_analysis(self, ana : list):
        self.analyses = ana
        if len(ana) > 0:
            self.current_analysis = self.analyses[0]
            self.current_analysis_index = 0
            self.load_analysis_display.emit(ana)
            self.update_current_analysis.emit(self.current_analysis)

    # Deletes currently selected analysis
    @Slot()
    def del_analysis(self):
        if not len(self.analyses):
            return

        del self.analyses[self.current_analysis_index]
        self.del_analysis_display.emit(self.current_analysis_index)

        if not len(self.analyses):
            self.current_analysis = None
            self.current_analysis_index = None
            self.update_current_analysis.emit(self.current_analysis)
            return
        elif self.current_analysis_index == 0:
            self.current_analysis_index = len(self.analyses) - 1
        else:
            self.current_analysis_index -= 1

        self.current_analysis = self.analyses[self.current_analysis_index]

        self.update_current_analysis.emit(self.current_analysis)

    @Slot(int)
    def switch_analysis(self, index : int):
        #print(index)
        if index == -1:
            self.current_analysis_index = None
            self.current_analysis = None
        else:
            self.current_analysis_index = index
            self.current_analysis = self.analyses[self.current_analysis_index]
        self.update_current_analysis.emit(self.current_analysis)

    @Slot()
    def prepare_new_analysis(self):
        self.new_analysis_mode = True

    @Slot()
    def cancel_new_analysis(self):
        self.new_analysis_mode = False

    @Slot(dict)
    def receive_analysis(self, ana : dict):
        if self.new_analysis_mode:
            self.add_analysis(ana)
            self.new_analysis_mode = False
        else:
            # Preserve name from previous copy of analysis
            preserve_name = self.current_analysis["name"]
            self.analyses[self.current_analysis_index] = ana
            self.analyses[self.current_analysis_index]["name"] = preserve_name
            self.current_analysis = self.analyses[self.current_analysis_index]
            self.update_current_analysis.emit(self.current_analysis)
