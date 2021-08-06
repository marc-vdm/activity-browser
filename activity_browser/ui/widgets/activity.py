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
        # the modules list of for activity is shown as a dropdown (ComboBox), which enables users to add this activity to a new module
        self.module_combo = QtWidgets.QComboBox()
        self.populate_module_combo()
        # self.module_combo.currentTextChanged.connect(lambda: self.FUNCTION(self.module_combo.currentText())) #TODO link to proper function
        self.module_combo.setToolTip("Use dropdown menu to start a new or add this unit process to a module")

        # module field
        self.module_field = QtWidgets.QWidget()
        self.module_field_layout = QtWidgets.QHBoxLayout()
        self.assemble_module_field() #TODO link modules here somehow
        self.module_field.setLayout(self.module_field_layout)

        #self.module_field = QtWidgets.QPushButton('Placeholder')
        #self.module_field.clicked.connect(self.mod)
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

    def populate_module_combo(self, items=[]):
        if len(items) == 0: #TODO replace with actual list of relevant modules
            items = ['example']

        items = ['', 'Add to new Module'] + items
        self.module_combo.addItems(items)

    def assemble_module_field(self):
        """ Build the module field with one button/tag per module"""

        modules = []
        for module_name, activities in msc.get_modular_system.affected_activities.items():
            if self.parent.key in activities:
                modules.append(module_name)

                tag = QtWidgets.QPushButton(module_name, self) #TODO add coloring to module buttons
                tag.clicked.connect(partial(self.module_field_tag_clicked, tag.text())) #TODO add useful action
                #tag #TODO add context menu for each module with a 'delete from module' option (perhaps only if the exchange is at the start or end of module)

                self.module_field_layout.addWidget(tag)
        self.module_field_layout.addStretch()

    def module_field_tag_clicked(self, tag_name=None):
        mlca_signals.module_selected.emit(tag_name)

    def connect_signals(self):
        signals.edit_activity.connect(self.update_location_combo)

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

