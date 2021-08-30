# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from functools import partial

from activity_browser.ui.style import header
from activity_browser.ui.icons import qicons
import brightway2 as bw

from activity_browser.signals import signals

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
        mlca_signals.module_changed.connect(self.update_widgets)

        mlca_signals.import_modular_system.connect(self.import_modules_dialog)
        mlca_signals.export_modules.connect(self.export_modules_dialog)
        mlca_signals.new_module.connect(self.new_module_dialog)
        mlca_signals.new_module_from_act.connect(self.new_module_dialog)
        mlca_signals.del_module.connect(self.del_module_dialog)
        mlca_signals.del_modules.connect(self.del_modules_dialog)
        mlca_signals.rename_module.connect(self.rename_module_dialog)
        mlca_signals.module_set_color.connect(self.change_color_module_dialog)
        mlca_signals.relink_modules.connect(self.relink_module_db_dialog)

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
            self.resize_splitter()
        else:
            # there are no modules
            self.modular_database_widget.label_no_modules.show()
            self.modular_database_widget.graph_button.hide()
            self.modular_database_widget.table.hide()
            self.modular_database_widget.export_button.hide()
            self.module_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
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

    def new_module_dialog(self, activity_key=None):
        """Dialog to add a new module to the modular system."""
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Create new module",
            "Name of new module:" + " " * 25,
        )

        if ok and name:
            if name not in msc.module_names:
                if activity_key:
                    ref_prod = bw.get_activity(activity_key)["reference product"]
                    msc.add_module(module_name=name,
                                   outputs=[(activity_key, ref_prod, 1.0)],
                                   chain=[activity_key])
                else:
                    msc.add_module(name)
                mlca_signals.module_selected.emit(name)
            else:
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible", "A module with this name already exists."
                )

    def del_module_dialog(self, module_name):
        """Dialog to add a new module to the modular system."""
        ok = QtWidgets.QMessageBox.question(
            self.window,
            "Delete module?",
            ("Are you sure you want to delete module\n'{}'?\nThis action cannot be undone").format(
                module_name)
        )
        if ok == QtWidgets.QMessageBox.Yes:
            msc.del_module(module_name)

    def del_modules_dialog(self, module_names):
        """Dialog to add a new module to the modular system."""
        ok = QtWidgets.QMessageBox.question(
            self.window,
            "Delete modules?",
            ("Are you sure you want to delete MULTIPLE modules? This action cannot be undone")
        )
        if ok == QtWidgets.QMessageBox.Yes:
            for module_name in module_names[:-1]:
                msc.del_module(module_name, save=False)
            msc.del_module(module_names[-1])

    def rename_module_dialog(self, module_name):
        """Dialog to rename a module in the modular system."""
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
        color = QtWidgets.QColorDialog().getColor(initial=msc.modular_system.get_module(module_name).color)
        if color.isValid():
            msc.set_module_color(module_name, color.name())

    def relink_module_db_dialog(self, db_data: tuple):
        """Dialog to relink activities in modules being imported to a new database."""
        missing_db, new_raw_data = db_data
        db_list = bw.databases.list
        options = [(db_name, db_list) for db_name in missing_db]
        dialog = RelinkModulesDialog.relink_modules(options, self.window)
        if dialog.exec_() == RelinkModulesDialog.Accepted:
            # Now, start relinking.
            links = dialog.links
            for module in new_raw_data:
                for i, output in enumerate(module['outputs']):
                    if output[0][0] in links.keys():
                        module['outputs'][i] = ((links[output[0][0]], output[0][1]), output[1], output[2])
                for i, chn in enumerate(module['chain']):
                    if chn[0] in links.keys():
                        module['chain'][i] = (links[chn[0]], chn[1])
                for i, cut in enumerate(module['cuts']):
                    if cut[0][0] in links.keys():
                        cut_key1 = (links[cut[0][0]], cut[0][1])
                    else:
                        cut_key1 = cut[0]
                    if cut[1][0] in links.keys():
                        cut_key2 = (links[cut[1][0]], cut[1][1])
                    else:
                        cut_key2 = cut[1]
                    module['cuts'][i] = (cut_key1, cut_key2, cut[2], cut[3])
            msc.add_modules(new_raw_data, rename=True)

class RelinkModulesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Relinking modules")

        self.db_label = QtWidgets.QLabel()
        self.label_choices = []
        self.grid_box = QtWidgets.QGroupBox("Database links:")
        self.grid = QtWidgets.QGridLayout()
        self.grid_box.setLayout(self.grid)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.db_label)
        layout.addWidget(self.grid_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @classmethod
    def construct_dialog(cls, label: str, options: list,
                         parent: QtWidgets.QWidget = None) -> 'RelinkModulesDialog':
        obj = cls(parent)
        obj.db_label.setText(label)
        # Start at 1 because row 0 is taken up by the db_label
        for i, item in enumerate(options):
            label = QtWidgets.QLabel(item[0])
            combo = QtWidgets.QComboBox()
            combo.addItems(item[1])
            combo.setCurrentText(item[0])
            obj.label_choices.append((label, combo))
            obj.grid.addWidget(label, i, 0, 1, 2)
            obj.grid.addWidget(combo, i, 2, 1, 2)
        obj.updateGeometry()
        return obj

    @classmethod
    def relink_modules(cls, options: list,
                      parent=None) -> 'RelinkModulesDialog':
        label = "Some database(s) could not be found in the current project," \
                " attempt to relink the activities in the modules to a different database?"
        return cls.construct_dialog(label, options, parent)

    @property
    def links(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.
        """
        return {
            label.text(): combo.currentText() for label, combo in self.label_choices
        }

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

        # output scaling widget
        self.output_scaling_checkbox = QtWidgets.QCheckBox('Output based scaling')
        self.output_scaling_checkbox.setToolTip('Turn output based scaling on or off (default on)')
        self.output_scaling_checkbox.setChecked(True)

        # graph button
        self.graph_button = QtWidgets.QPushButton(qicons.graph_explorer, '')
        self.graph_button.setToolTip('Show the module in the graph view\n'
                                     "To see the modular system in the graph view, click the graph button above the 'Modules' table")

        # available cuts
        self.available_cuts_widget = QtWidgets.QWidget()
        self.available_cuts_layout = QtWidgets.QHBoxLayout()
        self.available_cuts_widget.setLayout(self.available_cuts_layout)
        self.acww = QtWidgets.QWidget()
        self.acwc = QtWidgets.QHBoxLayout()
        self.acwc.addWidget(self.available_cuts_widget)
        self.acwc.addStretch()
        self.acww.setLayout(self.acwc)

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
        mlca_signals.module_db_changed.connect(self.update_available_cuts)
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

        self.available_cuts_label = QtWidgets.QLabel('Available cuts:')
        self.available_cuts_label.setToolTip(
            'Automatically generate a cut to another module upstream in the supply chain.')

        layout.addWidget(self.available_cuts_label)
        layout.addWidget(self.acww)

        self.setLayout(layout)

    def update_available_cuts(self) -> None:
        if not self.module_name:
            return

        layout = self.available_cuts_layout
        current_active_buttons = {layout.itemAt(i).widget().text(): i for i in range(layout.count())}

        # remove all available cuts buttons
        remove_widgets = []
        for ac in current_active_buttons.keys():
            widget = self.available_cuts_layout.itemAt(current_active_buttons[ac]).widget()
            remove_widgets.append(widget)
        for widget in remove_widgets:
            self.available_cuts_layout.removeWidget(widget)
            widget.deleteLater()

        # add all available cuts
        module = msc.get_modular_system.get_module(self.module_name)
        buttons_added = False
        for key, _output in msc.outputs.items():
            if module.external_edges:
                parents, children, value = zip(*module.external_edges)
                if key in parents:
                    for output_module_name, output in _output:
                        activity = bw.get_activity(key)
                        button = QtWidgets.QPushButton(qicons.add,
                                                       "'{}' to\n'{}'".format(output[1], output_module_name))
                        button.setToolTip("Cut the activity '{}' "
                                          "with product '{}' to module '{}'".format(activity['name'],
                                                                                    output[1],
                                                                                    output_module_name))
                        button.clicked.connect(partial(self.available_cuts_clicked,
                                                       (self.module_name, key, output[1])))
                        self.available_cuts_layout.addWidget(button)
                        buttons_added = True

        # hide the menu if there are no buttons to show
        if buttons_added:
            self.acww.show()
            self.available_cuts_label.show()
        else:
            self.acww.hide()
            self.available_cuts_label.hide()
        self.available_cuts_widget.setLayout(self.available_cuts_layout)

    def available_cuts_clicked(self, module_key_prod=None) -> None:
        module_name, key, product = module_key_prod

        msc.add_to_chain((module_name, key), update=False)
        msc.update_module(module_name)
        msc.add_to_cuts(module_key_prod)

    def reset_widget(self, deleted_module=None):
        if deleted_module == self.module_name or not deleted_module:
            self.hide()
            self.module_name = None
            self.update_available_cuts()

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
        if module_name == '':
            self.hide()
            return

        self.module_name = module_name

        self.module_name_field.setText(module_name)
        obs = msc.get_modular_system.get_module(module_name).output_based_scaling
        color = msc.get_modular_system.get_module(module_name).color
        self.output_scaling_checkbox.setChecked(obs)
        self.module_color_editor.setStyleSheet("background-color: {}".format(color))
        if self.cuts_tree.model.full_cuts[0][0] == 'hide':
            self.cuts_label.setText('There are no cuts in this module.')
        else:
            self.cuts_label.setText('Cuts')

        self.update_available_cuts()

        self.show()
