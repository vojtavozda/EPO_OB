from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtWidgets import QMainWindow
from epo_ob import EPOGUI

import sys

if __name__ == '__main__':

    app_context = ApplicationContext()       # 1. Instantiate ApplicationContext

    qapp = QApplication(sys.argv)
    qapp.setStyle(QStyleFactory.create("Cleanlooks"))
    qapp.setStyle('Fusion')

    csv_filepath = app_context.get_resource('test_event.csv')

    window = EPOGUI(csv_filepath)

    exit_code = app_context.app.exec()      # 2. Invoke appctxt.app.exec()
    sys.exit(exit_code)