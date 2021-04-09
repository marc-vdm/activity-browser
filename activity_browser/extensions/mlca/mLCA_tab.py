# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
import os

from activity_browser.ui.style import header
from activity_browser.ui.icons import qicons
from activity_browser.ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
) #TODO remove when all three tables have been removed
from activity_browser.signals import signals
from .linkedmetaprocess import LinkedMetaProcessSystem
from .mLCA_tables import (
    ModuleDatabaseListWidget,
    ModuleDatabaseTable,
)


class mLCATab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(mLCATab, self).__init__(parent)
        # main widgets
        self.modular_databases_widget = ModularDatabasesWidget()
        self.modular_database_widget = ModularDatabaseWidget(self)
        self.module_widget = ModuleWidget(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
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
        #TODO revise signals
        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        #TODO revise description
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_modules = self.module_widget.outputs_table.rowCount() == 0

        self.modular_database_widget.update_widget()

        if not no_modules:
            self.modular_database_widget.label_no_module_selected.hide()
        else:
            self.modular_database_widget.label_no_module_selected.show()
            self.module_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
        # TODO revise description
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.modular_database_widget, self.module_widget]
        sizes = [x.sizeHint().height() for x in widgets]
        self.splitter.setSizes(sizes)


class ModularDatabasesWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ModularDatabasesWidget, self).__init__()

        # Buttons
        self.open_database_button = QtWidgets.QPushButton(qicons.import_db, "Open")
        self.open_database_button.setToolTip('Open an existing modular database')
        self.new_database_button = QtWidgets.QPushButton(qicons.add, "New")
        self.new_database_button.setToolTip('Add a new modular database')
        self.copy_database_button = QtWidgets.QPushButton(qicons.copy, "Copy")
        self.copy_database_button.setToolTip('Copy the modular database')
        self.delete_database_button = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.delete_database_button.setToolTip('Delete the modular database')

        self.db_name_widget = QtWidgets.QLabel('Open a Modular Database or Start a new one')

        self.connect_signals()
        self.construct_layout()

    def connect_signals(self):
        pass
        self.open_database_button.clicked.connect(self.open_mLCA_db)
        #self.new_database_button.clicked.connect(signals.new_modular_database.emit) #TODO this should just start an empty ModuleDatabaseTable from ModularDatabaseWidget
        #self.delete_database_button.clicked.connect(signals.delete_modular_database.emit)
        #self.copy_database_button.clicked.connect(signals.copy_modular_database.emit) #TODO should allow re-name

    def open_mLCA_db(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select mLCA module database file')
        #TODO should I link to a 'manager' instead?

        f_name, _ = os.path.splitext(path)
        print('+++', f_name)
        #TODO how does this path look and how to extract only the name on all OS?
        self.db_name_widget.setText(path)
        LinkedMetaProcessSystem.load_from_file(self, filepath=path)

    def construct_layout(self):
        h_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(header('Databases:'))
        h_layout.addWidget(self.db_name_widget)
        h_layout.addWidget(self.open_database_button)
        h_layout.addWidget(self.new_database_button)
        h_layout.addWidget(self.copy_database_button)
        h_layout.addWidget(self.delete_database_button)
        h_widget.setLayout(h_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(h_widget)
        self.setLayout(layout)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        )


class ModularDatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = DatabasesTable() #TODO replace with ModuleDatabaseTable

        # Labels
        self.label_no_module_selected = QtWidgets.QLabel(
            "Select a module (double-click on table)."
        )

        # Buttons
        self.new_module_button = QtWidgets.QPushButton(qicons.add, "New")
        self.new_module_button.setToolTip('Add a new module')

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        pass
        #self.new_module_button.clicked.connect(signals.add_module.emit)

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

        self.outputs_table = ActivitiesBiosphereTable(self) #TODO replace with module outputs table
        self.chain_table = ActivitiesBiosphereTable(self)  # TODO replace with module chain table
        self.cuts_table = ActivitiesBiosphereTable(self)  # TODO replace with module cuts table/tree

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.addWidget(header('Module:'))
        self.header_widget.setLayout(self.header_layout)

        signals.database_selected.connect(self.update_table) #TODO replace database_selected with module_selected on right table

        # name widget
        self.name_widget = QtWidgets.QWidget()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.name_layout.addWidget(QtWidgets.QLabel('Name:'))
        self.name_layout.addWidget(QtWidgets.QLineEdit())
        self.name_widget.setLayout(self.name_layout)

        # output widget
        self.output_scaling_checkbox = QtWidgets.QCheckBox('Output based scaling (default)')
        self.output_scaling_checkbox.setToolTip('Turn output based scaling on or off')
        self.output_scaling_checkbox.setChecked(True)
        #TODO link signal below

        self.construct_layout()
        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_widget)

    def construct_layout(self):
        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(self.header_widget)
        layout.addWidget(self.name_widget)
        layout.addWidget(self.output_scaling_checkbox)
        layout.addWidget(QtWidgets.QLabel('Outputs'))
        layout.addWidget(self.outputs_table)
        layout.addWidget(QtWidgets.QLabel('Chain'))
        layout.addWidget(self.chain_table)
        layout.addWidget(QtWidgets.QLabel('Cuts'))
        layout.addWidget(self.cuts_table) #TODO treeview instead of table??
        self.setLayout(layout)

        self.outputs_table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )
        self.chain_table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )
        self.cuts_table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def reset_widget(self):
        self.hide()
        self.outputs_table.model.clear()
        self.chain_table.model.clear()
        self.cuts_table.model.clear()

    def update_table(self, db_name=''):
        if self.outputs_table.database_name: #TODO how to do this with three tables?
            self.show()
        #TODO fix label_module missing
        #self.label_module.setText("[{}]".format(db_name))
