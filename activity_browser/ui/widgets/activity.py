# -*- coding: utf-8 -*-
from functools import partial

from PySide2 import QtCore, QtWidgets
from PySide2.QtWidgets import QMessageBox

from activity_browser.extensions.mlca.modularsystem import modular_system_controller as msc
from activity_browser.extensions.mlca.mLCA_signals import mlca_signals

from .line_edit import SignalledLineEdit, SignalledComboEdit
from ..icons import qicons
from ...settings import project_settings
from ...signals import signals
from ...bwutils import AB_metadata


class DetailsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, label, widget):
        super().__init__(label)
        self.widget = widget
        self.setCheckable(True)
        self.toggled.connect(self.showhide)
        self.setChecked(False)
        self.setStyleSheet("QGroupBox { border: none; }")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widget)
        layout.setContentsMargins(0, 22, 0, 5)
        self.setLayout(layout)
        if isinstance(self.widget, QtWidgets.QTableWidget):
            self.widget.itemChanged.connect(self.toggle_empty_table)
        # The model will have an 'updated' signal that is emitted whenever
        # a change is made to the underlying data.
        if hasattr(self.widget, "model"):
            self.widget.model.updated.connect(self.toggle_empty_table)

    @QtCore.Slot(name="showHideTable")
    def showhide(self):
        self.widget.setVisible(self.isChecked())

    @QtCore.Slot(name="toggleEmptyTable")
    def toggle_empty_table(self) -> None:
        # Workaround so that the downstream table is only toggled by users.
        if self.title() == "Downstream Consumers:":
            return
        self.setChecked(bool(self.widget.rowCount()))


class ActivityDataGrid(QtWidgets.QWidget):
    """ Displayed at the top of each activity panel to show the user basic data related to the activity
    Expects to find the following data for each activity displayed: name, location, database
    Includes the read-only checkbox which enables or disables user-editing of some activity and exchange data
    Exchange data is displayed separately, below this grid, in tables.
    """
    def __init__(self, parent, read_only=True):
        super(ActivityDataGrid, self).__init__(parent)

        self.read_only = read_only
        self.parent = parent

        self.name_box = SignalledLineEdit(
            key=parent.key,
            field="name",
            parent=self,
        )
        # self.name_box.setPlaceholderText("Activity name")

        # location combobox
        self.location_combo = SignalledComboEdit(
            key=parent.key,
            field="location",
            parent=self,
            contents=parent.activity.get('location', '')
        )
        self.location_combo.setToolTip("Select an existing location from the current activity database."
                                          " Or add new location")
        self.location_combo.setEditable(True)  # always 'editable', but not always 'enabled'

        # database label
        self.database_label = QtWidgets.QLabel('Database')
        self.database_label.setToolTip("Select a different database to duplicate activity to it")

        # database combobox
        # the database of the activity is shown as a dropdown (ComboBox), which enables user to change it
        self.database_combo = QtWidgets.QComboBox()
        self.database_combo.currentTextChanged.connect(
            lambda target_db: self.duplicate_confirm_dialog(target_db))
        self.database_combo.setToolTip("Use dropdown menu to duplicate activity to another database")

        # module label
        self.module_label = QtWidgets.QLabel('Modules')
        self.module_label.setToolTip("Start a new or add this unit process to a module")

        # module combobox
        # the modules list of for activity is shown as a dropdown (ComboBox), which enables users to add this activity to a new or existing module
        self.module_combo = QtWidgets.QComboBox()
        self.populate_module_combo()
        self.module_combo.setToolTip("Add this activity to a module")

        # module field
        self.module_field = QtWidgets.QWidget()
        self.module_field_layout = QtWidgets.QHBoxLayout()
        self.assemble_module_field()
        self.module_field.setLayout(self.module_field_layout)
        self.module_field.setToolTip("All modules attached to this activity will be displayed here as buttons/labels")

        # arrange widgets for display as a grid
        self.grid = QtWidgets.QGridLayout()

        self.setContentsMargins(0, 0, 0, 0)
        self.grid.setContentsMargins(5, 5, 0, 5)
        self.grid.setSpacing(6)
        self.grid.setAlignment(QtCore.Qt.AlignTop)

        self.grid.addWidget(QtWidgets.QLabel('Name'), 1, 1)
        self.grid.addWidget(self.name_box, 1, 2, 1, 3)
        self.grid.addWidget(QtWidgets.QLabel('Location'), 2, 1)
        self.grid.addWidget(self.location_combo, 2, 2, 1, -1)
        self.grid.addWidget(self.database_combo, 3, 2, 1, -1)
        self.grid.addWidget(self.database_label, 3, 1)
        self.grid.addWidget(self.module_label, 4, 1)
        self.grid.addWidget(self.module_combo, 4, 2)
        self.grid.addWidget(self.module_field, 4, 3)

        self.setLayout(self.grid)

        self.populate()

        # do not allow user to edit fields if the ActivityDataGrid is read-only
        self.set_activity_fields_read_only()
        self.connect_signals()

    def connect_signals(self):
        signals.edit_activity.connect(self.update_location_combo)
        mlca_signals.module_db_changed.connect(self.update_module_field)
        mlca_signals.module_db_changed.connect(self.populate_module_combo)
        mlca_signals.module_color_set.connect(self.update_module_field)
        self.module_combo.activated.connect(self.module_combo_option_selected)

    def populate_module_combo(self):
        self.module_combo.clear()
        items = []
        if msc.related_activities and msc.related_activities.get(self.parent.key, False):
            modules = msc.related_activities[self.parent.key]
            for module in modules:
                # put in any module that this activity is not already part of
                if self.parent.key not in msc.affected_activities[module[0]] and module[0] not in items:
                    items.append(module[0])
        items = ['', 'Add to new Module'] + items
        self.module_combo.addItems(items)

    def module_combo_option_selected(self):
        option = self.module_combo.currentText()
        if option == '':
            return
        elif option == 'Add to new Module':
            mlca_signals.new_module_from_act.emit(self.parent.key)
            signals.show_tab.emit("mLCA")
        else:
            modules = msc.related_activities[self.parent.key]
            for module in modules:
                if module[0] == option:
                    break
            if module[1] == 'output':
                mlca_signals.replace_output.emit((module[0], self.parent.key))
            elif module[1] == 'chain':
                mlca_signals.add_to_chain.emit((module[0], self.parent.key))
            signals.show_tab.emit("mLCA")

        self.module_combo.setCurrentIndex(0)

    def generate_module_tag(self, module_name):
        tag = QtWidgets.QPushButton(module_name, self)
        color = msc.get_modular_system.get_modules([module_name])[0].color
        stylesheet = "background-color: {};" \
                     "border-radius: 15px;" \
                     "border: 1px solid black".format(color)
        tag.setStyleSheet(stylesheet)
        tag.clicked.connect(partial(self.module_field_tag_clicked, tag.text()))
        #tag #TODO add context menu for each module with a 'delete from module' option (perhaps only if the exchange is at the start or end of module)
        #TODO find way to change colors after making module_field
        self.module_field_layout.addWidget(tag)

    def assemble_module_field(self):
        self.module_field_layout.addWidget(QtWidgets.QLabel('Included in:'))
        msc.get_modular_system
        for module_name, activities in msc.affected_activities.items():
            if self.parent.key in activities:
                self.generate_module_tag(module_name)

    def update_module_field(self):
        mf = self.module_field_layout
        current_active_modules = {mf.itemAt(i).widget().text(): i for i in range(1, mf.count())}

        msc.get_modular_system
        for module_name in current_active_modules.keys():
            widget = self.module_field_layout.itemAt(current_active_modules[module_name]).widget()

            # remove modules that are do not contain activity anymore
            if module_name not in msc.module_names or \
                    self.parent.key not in msc.affected_activities[module_name]:
                # either module does not exist anymore or activity not in module anymore
                self.module_field_layout.removeWidget(widget)
                widget.deleteLater()

            # re-write tag-color
            color = msc.get_modular_system.get_modules([module_name])[0].color
            stylesheet = "background-color: {};" \
                         "border-radius: 15px;" \
                         "border: 1px solid black".format(color)
            widget.setStyleSheet(stylesheet)

        # add new modules if there are any
        for module_name, activities in msc.affected_activities.items():
            if module_name not in current_active_modules and \
                    self.parent.key in activities:
                # add module tag if not present already and valid to activity
                self.generate_module_tag(module_name)

    def module_field_tag_clicked(self, tag_name=None):
        mlca_signals.module_selected.emit(tag_name)
        signals.show_tab.emit("mLCA")

    def populate(self):
        # fill in the values of the ActivityDataGrid widgets
        self.name_box.setText(self.parent.activity.get('name', ''))
        self.name_box._key = self.parent.activity.key

        self.populate_location_combo()
        self.populate_database_combo()

    def populate_location_combo(self):
        """ acts as both of: a label to show current location of act, and
                auto-completes with all other locations in the database, to enable selection """
        self.location_combo.blockSignals(True)
        location = str(self.parent.activity.get('location', ''))
        self.location_combo.addItem(location)
        self.location_combo.setCurrentText(location)
        self.location_combo.blockSignals(False)

    def update_location_combo(self):
        """Update when in edit mode"""
        self.location_combo.blockSignals(True)
        location = str(self.parent.activity.get('location', 'unknown'))
        self.location_combo._before = location

        # get all locations in db
        self.location_combo.clear()
        db = self.parent.activity.get('database', '')
        locations = sorted(AB_metadata.get_locations(db))
        locations.append("unknown")
        self.location_combo.insertItems(0, locations)
        self.location_combo.setCurrentIndex(locations.index(location))
        self.location_combo.blockSignals(False)

    def populate_database_combo(self):
        """ acts as both: a label to show current db of act, and
                allows copying to others editable dbs via populated drop-down list """
        # clear any existing items first
        self.database_combo.blockSignals(True)
        self.database_combo.clear()

        # first item in db combo, shown by default, is the current database
        current_db = self.parent.activity.get('database', 'Error: db of Act not found')
        self.database_combo.addItem(current_db)

        # other items are the dbs that the activity can be duplicated to: find them and add
        available_target_dbs = list(project_settings.get_editable_databases())
        if current_db in available_target_dbs:
            available_target_dbs.remove(current_db)

        for db_name in available_target_dbs:
            self.database_combo.addItem(qicons.duplicate_activity, db_name)
        self.database_combo.blockSignals(False)

    def duplicate_confirm_dialog(self, target_db):
        """ Get user confirmation for duplication action """
        title = "Duplicate activity to new database"
        text = "Copy {} to {} and open as new tab?".format(
            self.parent.activity.get('name', 'Error: Name of Act not found'), target_db)

        user_choice = QMessageBox.question(self, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if user_choice == QMessageBox.Yes:
            signals.duplicate_activity_to_db.emit(target_db, self.parent.activity)
        # todo: give user more options in the dialog:
        #   * retain / delete version in current db
        #   * open / don't open new tab

        # change selected database item back to original (index=0), to avoid confusing user
        # block and unblock signals to prevent unwanted extra emits from the automated change
        self.database_combo.blockSignals(True)
        self.database_combo.setCurrentIndex(0)
        self.database_combo.blockSignals(False)

    def set_activity_fields_read_only(self, read_only=True):
        """ called on init after widgets instantiated
            also whenever a user clicks the read-only checkbox """
        # user cannot edit these fields if they are read-only
        self.read_only = read_only
        self.name_box.setReadOnly(self.read_only)
        self.location_combo.setEnabled(not self.read_only)

    def hide_show_module_data(self, toggled=False):
        self.module_label.setVisible(toggled)
        self.module_combo.setVisible(toggled)
        self.module_field.setVisible(toggled)

