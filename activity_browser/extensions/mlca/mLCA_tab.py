# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from activity_browser.ui.style import header
from activity_browser.ui.icons import qicons
from activity_browser.ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
)
from activity_browser.signals import signals


class mLCATab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(mLCATab, self).__init__(parent)
        # main widgets
        self.modular_databases_widget = ModularDatabasesWidget()
        self.modular_database_widget = ModularDatabaseWidget(self)
        self.module_widget = ModuleWidget(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        # self.splitter.addWidget(self.projects_widget)
        self.splitter.addWidget(self.modular_database_widget)
        self.splitter.addWidget(self.module_widget)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.modular_databases_widget)
        self.overall_layout.addWidget(self.splitter)
        self.overall_layout.addStretch()
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_modules = self.modular_database_widget.table.rowCount() == 0

        self.modular_database_widget.update_widget()

        # TODO this hide-show does not seem functional (also in project-manager tab)
        if not no_modules:
            self.modular_database_widget.label_no_module_selected.show()
        else:
            self.modular_database_widget.label_no_module_selected.hide()
            self.module_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.modular_database_widget, self.module_widget]
        sizes = [x.sizeHint().height() for x in widgets]
        self.splitter.setSizes(sizes)


        # print("Widget sizes:", sizes)
        # print("\nSH DB/Act/Bio: {}/{}/{}". format(*[x.sizeHint() for x in widgets]))
        # print("Splitter Sizes:", self.splitter.sizes())
        # print("SH Splitter Height:", self.splitter.height())


class ModularDatabasesWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ModularDatabasesWidget, self).__init__()

        # Buttons
        self.new_database_button = QtWidgets.QPushButton(qicons.add, "New")
        self.copy_database_button = QtWidgets.QPushButton(qicons.copy, "Copy")
        self.delete_database_button = QtWidgets.QPushButton(
            qicons.delete, "Delete"
        )
        # Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(header('Databases:'))
        self.h_layout.addWidget(QtWidgets.QLabel('>>Database chooser goes here<<')) #TODO add mLCA database chooser
        self.h_layout.addWidget(self.new_database_button)
        self.h_layout.addWidget(self.copy_database_button)
        self.h_layout.addWidget(self.delete_database_button)
        self.setLayout(self.h_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        )
        self.connect_signals()

    def connect_signals(self):
        pass
        #self.new_database_button.clicked.connect(signals.new_modular_database.emit)
        #self.delete_database_button.clicked.connect(signals.delete_modular_database.emit)
        #self.copy_database_button.clicked.connect(signals.copy_modular_database.emit)


class ModularDatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = DatabasesTable() #TODO replace with mLCA database table

        # Labels
        self.label_no_module_selected = QtWidgets.QLabel(
            "Select a module (double-click on table)."
        )

        # Buttons
        self.new_module_button = QtWidgets.QPushButton(qicons.add, "New")

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        pass
        #self.new_database_button.clicked.connect(signals.add_database.emit)

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Modules:"))
        header_layout.addWidget(self.new_module_button)
        header_layout.addWidget(self.label_no_module_selected)
        header_widget.setLayout(header_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_widget(self):
        no_modules = self.table.rowCount() == 0
        if no_modules:
            self.new_module_button.hide()
            self.table.hide()
        else:
            self.new_module_button.show()
            self.table.show()


class ModuleWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ModuleWidget, self).__init__(parent)
        self.header = 'Module:'

        self.table = ActivitiesBiosphereTable(self) #TODO replace with module table

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.addWidget(header(self.header))
        self.header_widget.setLayout(self.header_layout)

        self.label_module = QtWidgets.QLabel("[]")
        self.header_layout.addWidget(self.label_module)
        signals.database_selected.connect(self.update_table) #TODO replace with module_selected on right table

        # Overall Layout
        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.v_layout.addWidget(self.header_widget)
        self.v_layout.addWidget(self.table)
        self.setLayout(self.v_layout)

        self.table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_widget)

    # def sizeHint(self):
    #     return self.table.sizeHint()

    def reset_widget(self):
        self.hide()
        self.table.model.clear()

    def update_table(self, db_name=''):
        # print('Updating database table: ', db_name)
        if self.table.database_name:
            self.show()
        self.label_module.setText("[{}]".format(db_name))
