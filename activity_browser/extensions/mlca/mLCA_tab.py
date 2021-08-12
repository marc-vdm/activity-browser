# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from pathlib import Path

from activity_browser.ui.style import header
from activity_browser.ui.icons import qicons

from activity_browser.signals import signals
from activity_browser.bwutils.commontasks import update_and_shorten_label

from .mLCA_tables import (
    ModuleDatabaseTable,
    ModuleOutputsTable,
    ModuleChainTable,
    ModuleCutsTree
)
from .modularsystem import modular_system_controller as msc

from .mlca_icons import mlca_qicons

from .mLCA_signals import mlca_signals


class mLCATab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(mLCATab, self).__init__(parent)
        self.window = parent

        # main widgets
        self.modular_database_widget = ModularDatabaseWidget(self)
        self.module_widget = ModuleWidget(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.modular_database_widget)
        self.splitter.addWidget(self.module_widget)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.splitter)
        self.overall_layout.addStretch()
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.change_project)
        mlca_signals.module_db_changed.connect(self.update_widgets)
        mlca_signals.module_selected.connect(self.update_widgets)

        mlca_signals.new_module.connect(self.new_module_dialog)
        mlca_signals.new_module_from_act.connect(self.new_module_dialog)
        mlca_signals.del_module.connect(self.del_module_dialog)
        mlca_signals.rename_module.connect(self.rename_module_dialog)
        mlca_signals.module_set_color.connect(self.change_color_module_dialog)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        #TODO revise description
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_modules = self.modular_database_widget.table.rowCount() == 0

        self.modular_database_widget.update_widget()

        if not no_modules:
            self.modular_database_widget.label_no_modules.hide()
            self.modular_database_widget.table.show()
        else:
            self.modular_database_widget.label_no_modules.show()
            self.modular_database_widget.table.hide()
            self.module_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
        # TODO revise description
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.modular_database_widget, self.module_widget]
        sizes = [x.sizeHint().height() for x in widgets]
        self.splitter.setSizes(sizes)

    def new_module_dialog(self, activity=None):
        """Dialog to add a new module to the modular system"""
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Create new module",
            "Name of new module:" + " " * 25,
        )

        if ok and name:
            if name not in msc.module_names:
                if activity:
                    msc.add_module(name, chain=[activity])
                else:
                    msc.add_module(name)
                mlca_signals.module_selected.emit(name)
            else:
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible", "A module with this name already exists."
                )

    def del_module_dialog(self, module_name):
        """Dialog to add a new module to the modular system"""
        ok = QtWidgets.QMessageBox.question(
            self.window,
            "Delete module?",
            ("Are you sure you want to delete module '{}'? This action cannot be undone").format(
                module_name)
        )

        if ok == QtWidgets.QMessageBox.Yes:
            msc.del_module(module_name)

    def rename_module_dialog(self, module_name):
        """Dialog to rename a module in the modular system"""
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Rename module '{}'".format(module_name),
            "New name of module:" + " " * 25
        )

        if ok and name:
            if name not in msc.module_names:
                msc.rename_module(module_name, name)
            else:
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible", "A module with this name already exists."
                )

    def change_color_module_dialog(self, module_name):
        """Dialog to change the color of a module in the modular system"""
        #TODO make this a proper color chooser
        color, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Color module '{}'".format(module_name),
            "New color of module:" + " " * 25
        )

        if ok and color:
            msc.set_module_color(module_name, color)

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
        self.label_no_modules = QtWidgets.QLabel(
            "Start a new module by pressing the 'New' button"
        )

        # Buttons
        self.new_module_button = QtWidgets.QPushButton(qicons.add, "New")
        self.new_module_button.setToolTip('Add a new module')

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        mlca_signals.database_selected.connect(self.db_change)
        self.new_module_button.clicked.connect(mlca_signals.new_module.emit)

    def db_change(self, selected):
        if selected:
            self.update_widget()
        else:
            self.reset_widget()

    def reset_widget(self):
        pass

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Modules:"))
        header_layout.addWidget(self.new_module_button)
        header_layout.addWidget(self.label_no_modules)
        header_widget.setLayout(header_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_widget(self):
        self.show()

class ModuleWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ModuleWidget, self).__init__(parent)

        self.outputs_table = ModuleOutputsTable(self)
        self.chain_table = ModuleChainTable(self)
        self.cuts_tree = ModuleCutsTree(self)
        self.current_module = None

        # Header/name widget
        self.name_widget = QtWidgets.QWidget()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.name_layout.addWidget(header('Module:'))
        self.module_name_field = QtWidgets.QLineEdit()
        self.name_layout.addWidget(self.module_name_field)
        self.module_color_editor = QtWidgets.QPushButton('Color')
        self.module_color_editor.setStyleSheet("background-color: white")
        self.module_color_editor.setToolTip('Change the color of the module')
        self.name_layout.addWidget(self.module_color_editor)
        self.name_widget.setLayout(self.name_layout)

        # output widget
        self.output_scaling_checkbox = QtWidgets.QCheckBox('Output based scaling (default)')
        self.output_scaling_checkbox.setToolTip('Turn output based scaling on or off')
        self.output_scaling_checkbox.setChecked(True)

        self.construct_layout()
        self.connect_signals()
        self.hide()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_widget)
        mlca_signals.del_module.connect(self.reset_widget)
        mlca_signals.rename_module.connect(self.reset_widget)
        mlca_signals.module_selected.connect(self.update_widget)
        mlca_signals.module_color_set.connect(self.update_widget)
        self.module_name_field.editingFinished.connect(self.module_name_change)
        self.module_color_editor.clicked.connect(self.change_module_color)
        #self.output_scaling_checkbox.toggled.connect()

    def construct_layout(self):
        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(self.name_widget)
        layout.addWidget(self.output_scaling_checkbox)
        layout.addWidget(QtWidgets.QLabel('Outputs'))
        layout.addWidget(self.outputs_table)
        layout.addWidget(QtWidgets.QLabel('Chain'))
        layout.addWidget(self.chain_table)
        layout.addWidget(QtWidgets.QLabel('Cuts'))
        layout.addWidget(self.cuts_tree)
        self.setLayout(layout)

    def reset_widget(self, deleted_module=None):
        if deleted_module == self.current_module or not deleted_module:
            self.hide()
            self.current_module = None

    def module_name_change(self):
        name = self.module_name_field.text()
        if name not in msc.module_names:
            msc.rename_module(self.current_module, name)
        else:
            print("Not possible", "A module with this name already exists.")

    def change_module_color(self):
        mlca_signals.module_set_color.emit(self.module_name_field.text())

    def update_widget(self, module_name=''):
        self.current_module = module_name
        self.module_name_field.setText(module_name)
        color = msc.get_modular_system.get_modules([module_name])[0].color
        self.module_color_editor.setStyleSheet("background-color: {}".format(color))
        self.show()
