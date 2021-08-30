# -*- coding: utf-8 -*-
from functools import partial

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Slot

from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from activity_browser.extensions.mlca.mlca_icons import mlca_qicons
from .delegates import CheckboxDelegate
from .models import DatabasesModel, ActivitiesBiosphereModel
from .views import ABDataFrameView

from ...extensions.mlca.modular_system_controller import modular_system_controller as msc
from activity_browser.extensions.mlca.mLCA_signals import mlca_signals


class DatabasesTable(ABDataFrameView):
    """ Displays metadata for the databases found within the selected project.

    Databases can be read-only or writable, with users preference persisted
    in settings file.
    - User double-clicks to see the activities and flows within a db
    - A context menu (right click) provides further functionality
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setItemDelegateForColumn(2, CheckboxDelegate(self))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))
        self.relink_action = QtWidgets.QAction(
            qicons.edit, "Re-link database", None
        )
        self.new_activity_action =QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.model = DatabasesModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(
            lambda p: signals.database_selected.emit(self.model.get_db_name(p))
        )
        self.relink_action.triggered.connect(
            lambda: signals.relink_database.emit(self.selected_db_name)
        )
        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.selected_db_name)
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return

        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.delete, "Delete database",
            lambda: signals.delete_database.emit(self.selected_db_name)
        )
        menu.addAction(self.relink_action)
        menu.addAction(
            qicons.duplicate_database, "Copy database",
            lambda: signals.copy_database.emit(self.selected_db_name)
        )
        menu.addAction(self.new_activity_action)
        proxy = self.indexAt(event.pos())
        if proxy.isValid():
            db_name = self.model.get_db_name(proxy)
            self.relink_action.setEnabled(not project_settings.db_is_readonly(db_name))
            self.new_activity_action.setEnabled(not project_settings.db_is_readonly(db_name))
        menu.exec_(event.globalPos())

    def mousePressEvent(self, e):
        """ A single mouseclick should trigger the 'read-only' column to alter
        its value.

        NOTE: This is kind of hacky as we are deliberately sidestepping
        the 'delegate' system that should handle this.
        If this is important in the future: call self.edit(index)
        (inspired by: https://stackoverflow.com/a/11778012)
        """
        if e.button() == QtCore.Qt.LeftButton:
            proxy = self.indexAt(e.pos())
            if proxy.column() == 2:
                # Flip the read-only value for the database
                new_value = not bool(proxy.data())
                db_name = self.model.get_db_name(proxy)
                project_settings.modify_db(db_name, new_value)
                signals.database_read_only_changed.emit(db_name, new_value)
                self.model.sync()
        super().mousePressEvent(e)

    @property
    def selected_db_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_db_name(self.currentIndex())


class ActivitiesBiosphereTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_read_only = True

        self.model = ActivitiesBiosphereModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self.new_activity_action = QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            qicons.copy, "Duplicate activity/-ies", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            qicons.delete, "Delete activity/-ies", None
        )
        self.add_to_module_action = QtWidgets.QAction(
            qicons.add, "Add activity to new module", None
        )

        self.connect_signals()

    @property
    def database_name(self) -> str:
        return self.model.database_name

    @property
    def technosphere(self) -> bool:
        return self.model.technosphere

    def contextMenuEvent(self, event) -> None:
        """ Construct and present a menu.
        """
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activity", self.open_activity_tabs)
        menu.addAction(
            qicons.graph_explorer, "Open in Graph Explorer",
            lambda: signals.open_activity_graph_tab.emit(
                self.model.get_key(self.currentIndex())
            )
        )
        menu.addAction(self.new_activity_action)
        menu.addAction(self.duplicate_activity_action)
        menu.addAction(self.delete_activity_action)
        menu.addAction(
            qicons.duplicate_to_other_database, "Duplicate to other database",
            self.duplicate_activities_to_db
        )

        available_modules = self.generate_module_items(self.model.get_key(self.currentIndex()))
        if len(available_modules) > 0:
            # both available and other modules lists are non-empty, get a sub menu
            menu.addSeparator()
            sub_menu = menu.addMenu(mlca_qicons.modular_system, "Add activity to module")
            sub_menu.addAction(self.add_to_module_action)
            module_actions = []
            # add the relevant modules
            for module_name in available_modules:
                module_actions.append((module_name,
                                       QtWidgets.QAction(
                                           qicons.add, "Add activity to '{}'".format(module_name), None
                                       )))
            for module_data in module_actions:
                module_name, module_action = module_data
                sub_menu.addAction(module_action)
                module_action.triggered.connect(partial(self.module_context_handler, module_name))
        else:
            menu.addAction(self.add_to_module_action)

        menu.exec_(event.globalPos())

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database_name)
        )
        self.duplicate_activity_action.triggered.connect(self.duplicate_activities)
        self.delete_activity_action.triggered.connect(self.delete_activities)
        self.doubleClicked.connect(self.open_activity_tab)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.set_context_menu_policy)
        self.add_to_module_action.triggered.connect(partial(self.module_context_handler, 'new'))

    def generate_module_items(self, key):
        available_modules = set()
        # get relevant modules
        if msc.related_activities and msc.related_activities.get(key, False):
            modules = msc.related_activities[key]
            for module in modules:
                # put in any module that this activity is not already part of
                if key not in msc.affected_activities[module[0]]:
                    available_modules.add(module[0])
        available_modules = list(available_modules) + msc.empty_modules
        return available_modules

    def module_context_handler(self, item_name):
        """Decide what happens based on which context menu option was clicked"""
        key = self.model.get_key(self.currentIndex())
        if item_name == 'new':
            mlca_signals.new_module_from_act.emit(key)
        else:
            modules = msc.related_activities[key]
            for module in modules:
                if module[0] == item_name:
                    break
            if module[1] == 'output':
                mlca_signals.replace_output.emit((module[0], key))
            elif module[1] == 'chain':
                mlca_signals.add_to_chain.emit((module[0], key))

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_key(proxy)

    @Slot(QtCore.QModelIndex, name="openActivityTab")
    def open_activity_tab(self, proxy: QtCore.QModelIndex) -> None:
        key = self.model.get_key(proxy)
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @Slot(name="openActivityTabs")
    def open_activity_tabs(self) -> None:
        for key in (self.model.get_key(p) for p in self.selectedIndexes()):
            signals.open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    @Slot(name="deleteActivities")
    def delete_activities(self) -> None:
        self.model.delete_activities(self.selectedIndexes())

    @Slot(name="duplicateActivitiesWithinDb")
    def duplicate_activities(self) -> None:
        self.model.duplicate_activities(self.selectedIndexes())

    @Slot(name="duplicateActivitiesToOtherDb")
    def duplicate_activities_to_db(self) -> None:
        self.model.duplicate_activities_to_db(self.selectedIndexes())

    def sync(self, db_name: str) -> None:
        self.model.sync(db_name)

    @Slot(name="updateMenuContext")
    def set_context_menu_policy(self) -> None:
        if self.model.technosphere:
            self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.db_read_only = project_settings.db_is_readonly(self.database_name)
            self.update_activity_table_read_only(self.database_name, self.db_read_only)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def search(self, pattern1: str = None, pattern2: str = None,
               logic='AND') -> None:
        self.model.search(pattern1, pattern2, logic)

    @Slot(name="resetSearch")
    def reset_search(self) -> None:
        self.model.sync(self.model.database_name)

    @Slot(str, bool, name="updateReadOnly")
    def update_activity_table_read_only(self, db_name: str, db_read_only: bool) -> None:
        """ [new, duplicate & delete] actions can only be selected for
        databases that are not read-only.

        The user can change state of dbs other than the open one, so check
        if database name matches.
        """
        if self.database_name == db_name:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.duplicate_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)
