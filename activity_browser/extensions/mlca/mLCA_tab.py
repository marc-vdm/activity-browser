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
from .modular_system_controller import modular_system_controller as msc

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

        mlca_signals.import_modular_system.connect(self.import_modules_dialog)
        mlca_signals.export_modules.connect(self.export_modules_dialog)
        mlca_signals.new_module.connect(self.new_module_dialog)
        mlca_signals.new_module_from_act.connect(self.new_module_dialog)
        mlca_signals.del_module.connect(self.del_module_dialog)
        mlca_signals.del_modules.connect(self.del_modules_dialog)
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
            # there are modules
            self.modular_database_widget.label_no_modules.hide()
            self.modular_database_widget.graph_button.show()
            self.modular_database_widget.table.show()
            self.modular_database_widget.export_button.show()
        else:
            # there are no modules
            self.modular_database_widget.label_no_modules.show()
            self.modular_database_widget.graph_button.hide()
            self.modular_database_widget.table.hide()
            self.modular_database_widget.export_button.hide()
            self.module_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
        # TODO revise description
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.modular_database_widget, self.module_widget]
        sizes = [x.sizeHint().height() for x in widgets]
        self.splitter.setSizes(sizes)

    def import_modules_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption='Select module data file',
            filter='mLCA files (*.mlca)'
        )
        if path:
            msc.import_modules(path)

    def export_modules_dialog(self, export_names: list):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption='Export modules to file',
            filter='mLCA files (*.mlca)'
        )
        if path:
            if not path.endswith('.mlca'):
                path += '.mlca'
            msc.export_modules(export_names, path)

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
            ("Are you sure you want to delete module\n'{}'?\nThis action cannot be undone").format(
                module_name)
        )
        if ok == QtWidgets.QMessageBox.Yes:
            msc.del_module(module_name)

    def del_modules_dialog(self, module_names):
        """Dialog to add a new module to the modular system"""
        ok = QtWidgets.QMessageBox.question(
            self.window,
            "Delete modules?",
            ("Are you sure you want to delete MULTIPLE modules? This action cannot be undone")
        )
        if ok == QtWidgets.QMessageBox.Yes:
            for module_name in module_names:
                msc.del_module(module_name, save=False)
            msc.save_modular_system()
            mlca_signals.module_db_changed.emit()

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
                if name != module_name:
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

class ModularDatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = ModuleDatabaseTable()

        # Labels
        self.label_no_modules = QtWidgets.QLabel(
           "Start a New module or Import modules"
        )

        # Buttons
        self.new_module_button = QtWidgets.QPushButton(qicons.add, "New")
        self.new_module_button.setToolTip('Add a new module')

        self.import_button = QtWidgets.QPushButton(mlca_qicons.add_db, "Import")
        self.import_button.setToolTip('Import modules to the modular system')

        self.export_button = QtWidgets.QPushButton(mlca_qicons.save_db, "Export")
        self.export_button.setToolTip('Export the modular system')

        self.graph_button = QtWidgets.QPushButton(qicons.graph_explorer, '')
        self.graph_button.setToolTip('Show the modular system in the graph view\n'
                                     "To see an individual module in the graph view, click the graph button in a Module overview below")

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        self.new_module_button.clicked.connect(mlca_signals.new_module.emit)
        self.import_button.clicked.connect(mlca_signals.import_modular_system.emit)
        self.export_button.clicked.connect(self.exporter)
        self.graph_button.clicked.connect(self.show_modular_system_in_graph)

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Modules:"))
        header_layout.addWidget(self.new_module_button)
        header_layout.addWidget(self.import_button)
        header_layout.addWidget(self.export_button)
        header_layout.addWidget(self.label_no_modules)
        header_layout.addStretch()
        header_layout.addWidget(self.graph_button)
        header_widget.setLayout(header_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def show_modular_system_in_graph(self):
        print('++ Graph view should be opened')

    def exporter(self):
        mlca_signals.export_modules.emit(msc.module_names)

    def update_widget(self):
        self.show()

class ModuleWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ModuleWidget, self).__init__(parent)

        self.outputs_table = ModuleOutputsTable(self)
        self.chain_table = ModuleChainTable(self)
        self.cuts_tree = ModuleCutsTree(self)
        self.module_name = None

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
        self.output_scaling_checkbox = QtWidgets.QCheckBox('Output based scaling')
        self.output_scaling_checkbox.setToolTip('Turn output based scaling on or off (default on)')
        self.output_scaling_checkbox.setChecked(True)

        # graph button
        self.graph_button = QtWidgets.QPushButton(qicons.graph_explorer, '')
        self.graph_button.setToolTip('Show the module in the graph view\n'
                                     "To see the modular system in the graph view, click the graph button above the 'Modules' table")

        self.construct_layout()
        self.connect_signals()
        self.hide()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_widget)
        mlca_signals.del_module.connect(self.reset_widget)
        mlca_signals.rename_module.connect(self.reset_widget)
        mlca_signals.module_selected.connect(self.update_widget)
        mlca_signals.module_color_set.connect(self.update_widget)
        mlca_signals.module_changed.connect(self.update_widget)
        self.module_name_field.editingFinished.connect(self.module_name_change)
        self.module_color_editor.clicked.connect(self.change_module_color)
        self.output_scaling_checkbox.toggled.connect(self.output_based_scaling_editor)
        self.graph_button.clicked.connect(self.show_module_in_graph)

    def construct_layout(self):
        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(self.name_widget)

        tools_layout = QtWidgets.QHBoxLayout()
        tools_layout.addWidget(self.output_scaling_checkbox)
        tools_layout.addStretch()
        tools_layout.addWidget(self.graph_button)
        tools_widget = QtWidgets.QWidget()
        tools_widget.setLayout(tools_layout)
        layout.addWidget(tools_widget)

        self.outputs_label = QtWidgets.QLabel('Outputs')
        self.outputs_label.setToolTip('An output is the product that a module produces. Outputs are required for modular calculations.\n'
                                      'Right click on an activity in the chain to add it as an output.')
        layout.addWidget(self.outputs_label)
        layout.addWidget(self.outputs_table)
        self.chain_label = QtWidgets.QLabel('Chain')
        self.chain_label.setToolTip('The chain is the supply chain required to produce an output.\n'
                                    'A chain must be at least one activity long, but can be longer to connect to different modules with cuts.')
        layout.addWidget(self.chain_label)
        layout.addWidget(self.chain_table)
        self.cuts_label = QtWidgets.QLabel('Cuts')
        self.cuts_label.setToolTip('A cut is where a module replaces the conventional\n'
                                   'activity input with another module as input. Cuts are optional.\n'
                                   'Right click on the activity at the end of the chain to add it as a cut.')
        layout.addWidget(self.cuts_label)
        layout.addWidget(self.cuts_tree)
        self.setLayout(layout)

    def reset_widget(self, deleted_module=None):
        if deleted_module == self.module_name or not deleted_module:
            self.hide()
            self.module_name = None

    def output_based_scaling_editor(self, state):
        mlca_signals.module_set_obs.emit((self.module_name, state))

    def module_name_change(self):
        name = self.module_name_field.text()
        if name not in msc.module_names:
            msc.rename_module(self.module_name, name)
        else:
            if name != self.module_name:
                print("Not possible", "A module with this name already exists.")

    def change_module_color(self):
        mlca_signals.module_set_color.emit(self.module_name_field.text())

    def show_module_in_graph(self):
        print('++ Graph view should be opened')

    def update_widget(self, module_name=''):
        self.module_name = module_name
        self.module_name_field.setText(module_name)
        obs = msc.get_modular_system.get_module(module_name).output_based_scaling
        color = msc.get_modular_system.get_module(module_name).color
        self.output_scaling_checkbox.setChecked(obs)
        self.module_color_editor.setStyleSheet("background-color: {}".format(color))
        if len(self.cuts_tree.model.full_cuts) == 0:
            self.cuts_label.setText('There are no cuts in this module.')
        else:
            self.cuts_label.setText('Cuts')

        self.show()
