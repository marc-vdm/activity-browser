# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from pathlib import Path

from activity_browser.ui.style import header
from activity_browser.ui.icons import qicons
from activity_browser.ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
) #TODO remove when all three tables have been removed
from activity_browser.signals import signals
from activity_browser.bwutils.commontasks import update_and_shorten_label

from .modularsystem import ModularSystem
from .mLCA_tables import (
    ModuleDatabaseTable,
    ModuleChainTable
)
from .mlca_icons import mlca_qicons

from .mLCA_signals import mlca_signals

#TODO: when no DB is open, hide the databases section
#TODO: when an empty DB is open, show toolbar but no table
#TODO: when a DB with items is open, show table (and tools??)
#TODO: also disable table refreshing when required!

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
        mlca_signals.change_database.connect(self.change_database)
        #signals.project_selected.connect(self.change_project)
        #signals.database_selected.connect(self.update_widgets)
        pass

    @QtCore.Slot(tuple, name='mlcaDbChanged')
    def change_database(self, db_data: tuple) -> None:

        db_name, state = db_data
        print('+++ signal was connected ', db_name, state)

        #mlca_signals.change_database.emit((db_name, state))

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
        self.delete_database_button = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.delete_database_button.setToolTip('Delete the modular database')
        self.save_database_button = QtWidgets.QPushButton(mlca_qicons.save_db, "Save")
        self.save_database_button.setToolTip('Save the modular database')
        self.save_database_button.setVisible(False)
        self.saveas_database_button = QtWidgets.QPushButton(mlca_qicons.save_db, "Save as")
        self.saveas_database_button.setToolTip('Save the modular database to a different file')
        self.saveas_database_button.setVisible(False)

        self.db_name = None
        self.db_name_default_label = 'Open a Modular Database or start a new one'
        self.db_name_widget = QtWidgets.QLabel('[{}]'.format(self.db_name_default_label))

        self.mlca_file_types = 'mLCA files (*.pickle *.mlca)'

        self.connect_signals()
        self.construct_layout()

    def connect_signals(self):
        pass
        self.open_database_button.clicked.connect(self.open_mLCA_db)
        self.new_database_button.clicked.connect(self.new_mLCA_db)
        self.delete_database_button.clicked.connect(self.delete_mLCA_db)
        self.save_database_button.clicked.connect(self.save_mLCA_db)
        self.saveas_database_button.clicked.connect(self.saveas_mLCA_db)

    def update_state_mLCA_db(self, path, state):
        if path:
            self.db_name = Path(path).stem

            update_and_shorten_label(self.db_name_widget, self.db_name)
            mlca_signals.change_database.emit((path, state))
        else:
            # the loading was either canceled or failed somehow
            if self.db_name:
                update_and_shorten_label(self.db_name_widget, self.db_name)
            else:
                update_and_shorten_label(self.db_name_widget, self.db_name_default_label, enable=False)

        if self.db_name:
            self.save_database_button.setVisible(True)
            self.saveas_database_button.setVisible(True)
        else:
            self.save_database_button.setVisible(False)
            self.saveas_database_button.setVisible(False)

        if state == 'delete':
            mlca_signals.database_selected.emit(False)
        else:
            mlca_signals.database_selected.emit(True)

    def open_mLCA_db(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption='Select mLCA module database file',
            filter=self.mlca_file_types)
        #TODO set default folder with 'dir=..' argument when we have one

        self.update_state_mLCA_db(path, 'open')

    def new_mLCA_db(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption='Create a new mLCA module database file',
            filter=self.mlca_file_types)

        self.update_state_mLCA_db(path, 'new')

    def delete_mLCA_db(self):
        # TODO dialog to delete file somehow
        #TODO should ask for confirmation
        pass
        path = 'WARNING: NOT IMPLEMENTED'
        print('+++ deleting mLCa database:', path)
        mlca_signals.change_database.emit((self.db_name, 'delete'))

    def save_mLCA_db(self):
        self.update_state_mLCA_db(self.db_name, 'save')

    def saveas_mLCA_db(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption='Save your mLCA module database file',
            filter=self.mlca_file_types)

        # send same signal to save, as only path is required to be different
        self.update_state_mLCA_db(path, 'save')

    def construct_layout(self):
        # header
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(header('Database:'))
        header_layout.addWidget(self.db_name_widget)
        header_layout.addStretch(1)
        header_widget.setLayout(header_layout)

        # buttons
        button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.open_database_button)
        button_layout.addWidget(self.new_database_button)
        button_layout.addWidget(self.delete_database_button)
        button_layout.addWidget(self.save_database_button)
        button_layout.addWidget(self.saveas_database_button)
        button_layout.addStretch(1)
        button_widget.setLayout(button_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(button_widget)
        self.setLayout(layout)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        )


class ModularDatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = ModuleDatabaseTable()

        # Labels
        self.label_no_module_selected = QtWidgets.QLabel(
            "Select a module (double-click on table)."
        )

        # Buttons
        self.new_module_button = QtWidgets.QPushButton(qicons.add, "New")
        self.new_module_button.setToolTip('Add a new module')

        self.toolbar = QtWidgets.QLabel('Toolbar goes here')

        self._construct_layout()
        self._connect_signals()
        self.hide()

    def _connect_signals(self):
        pass
        mlca_signals.database_selected.connect(self.db_change)
        #self.new_module_button.clicked.connect(mlca_signals.new_module.emit)

    def db_change(self, selected):
        if selected:
            self.update_widget()
        else:
            self.reset_widget()

    def reset_widget(self):
        self.hide()
        self.table.model.clear()

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
        layout.addWidget(self.toolbar)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_widget(self):
        self.show()
        no_modules = self.table.rowCount() == 0
        if no_modules:
            self.toolbar.hide()
            self.table.hide()
        else:
            self.toolbar.show()
            self.table.show()

class ModuleWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ModuleWidget, self).__init__(parent)

        self.outputs_table = ActivitiesBiosphereTable(self) #TODO replace with module outputs table
        #self.chain_table = ModuleChainTable(self)  # TODO replace with module chain table
        self.chain_table = ActivitiesBiosphereTable(self)  # TODO replace with module chain table
        self.cuts_table = ActivitiesBiosphereTable(self)  # TODO replace with module cuts table/tree

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.addWidget(header('Module:'))
        self.header_widget.setLayout(self.header_layout)

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
        self.hide()

    def connect_signals(self):
        pass
        mlca_signals.database_selected.connect(self.reset_widget)

        mlca_signals.module_selected.connect(self.update_table)

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
