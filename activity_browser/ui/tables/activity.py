# -*- coding: utf-8 -*-
from functools import partial

from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from .delegates import *
from .models import (
    BaseExchangeModel, ProductExchangeModel, TechnosphereExchangeModel,
    BiosphereExchangeModel, DownstreamExchangeModel,
)
from .views import ABDataFrameView
from ..icons import qicons
from activity_browser.extensions.mlca.mlca_icons import mlca_qicons
from ...signals import signals

from ...extensions.mlca.modular_system_controller import modular_system_controller as msc
from activity_browser.extensions.mlca.mLCA_signals import mlca_signals

class BaseExchangeTable(ABDataFrameView):
    MODEL = BaseExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

        self.delete_exchange_action = QtWidgets.QAction(
            qicons.delete, "Delete exchange(s)", None
        )
        self.remove_formula_action = QtWidgets.QAction(
            qicons.delete, "Clear formula(s)", None
        )
        self.modify_uncertainty_action = QtWidgets.QAction(
            qicons.edit, "Modify uncertainty", None
        )
        self.remove_uncertainty_action = QtWidgets.QAction(
            qicons.delete, "Remove uncertainty/-ies", None
        )
        self.copy_exchanges_for_SDF_action = QtWidgets.QAction(
            qicons.superstructure, "Exchanges for scenario difference file", None
        )

        self.key = getattr(parent, "key", None)
        self.model = self.MODEL(self.key, self)
        self.downstream = False
        self._connect_signals()

    def _connect_signals(self):
        self.delete_exchange_action.triggered.connect(
            lambda: self.model.delete_exchanges(self.selectedIndexes())
        )
        self.remove_formula_action.triggered.connect(
            lambda: self.model.remove_formula(self.selectedIndexes())
        )
        self.modify_uncertainty_action.triggered.connect(
            lambda: self.model.modify_uncertainty(self.currentIndex())
        )
        self.remove_uncertainty_action.triggered.connect(
            lambda: self.model.remove_uncertainty(self.selectedIndexes())
        )
        self.copy_exchanges_for_SDF_action.triggered.connect(
            lambda: self.model.copy_exchanges_for_SDF(self.selectedIndexes())
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        super().custom_view_sizing()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.setColumnHidden(self.model.exchange_column, True)

    @Slot(name="openActivities")
    def open_activities(self) -> None:
        self.model.open_activities(self.selectedIndexes())

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.exec_(event.globalPos())

    def dragMoveEvent(self, event) -> None:
        """ For some reason, this method existing is required for allowing
        dropEvent to occur _everywhere_ in the table.
        """
        pass

    def dropEvent(self, event):
        source_table = event.source()
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        event.accept()
        signals.exchanges_add.emit(keys, self.key)

    def get_usable_parameters(self):
        return self.model.get_usable_parameters()

    def get_interpreter(self):
        return self.model.get_interpreter()


class ProductExchangeTable(BaseExchangeTable):
    MODEL = ProductExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))
        self.setItemDelegateForColumn(3, FormulaDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "product"

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.remove_formula_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        technosphere exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "technosphere" or
                getattr(source, "technosphere", False) is True):
            event.accept()


class TechnosphereExchangeTable(BaseExchangeTable):
    MODEL = TechnosphereExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(13, FormulaDelegate(self))
        self.setItemDelegateForColumn(14, StringDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "technosphere"

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        super().custom_view_sizing()
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)
        menu.addAction(self.modify_uncertainty_action)
        menu.addSeparator()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.remove_uncertainty_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        available_modules = self.generate_module_items(self.model.get_key(self.currentIndex()))
        if len(available_modules) > 0:
            menu.addSeparator()
            if len(available_modules) > 1:
                sub_menu = menu.addMenu(mlca_qicons.modular_system, "Add activity to module")
            else:
                sub_menu = menu
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

        menu.exec_(event.globalPos())

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

        modules = msc.related_activities[key]
        for module in modules:
            if module[0] == item_name:
                break
        if module[1] == 'output':
            mlca_signals.replace_output.emit((module[0], key))
        elif module[1] == 'chain':
            mlca_signals.add_to_chain.emit((module[0], key))
        signals.show_tab.emit("Modular System")

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        downstream exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "downstream" or
                hasattr(source, "technosphere")):
            event.accept()


class BiosphereExchangeTable(BaseExchangeTable):
    MODEL = BiosphereExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(12, FormulaDelegate(self))
        self.setItemDelegateForColumn(13, StringDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.table_name = "biosphere"

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        super().custom_view_sizing()
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.modify_uncertainty_action)
        menu.addSeparator()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.remove_uncertainty_action)

        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """ Only accept exchanges from a technosphere database table
        """
        if hasattr(event.source(), "technosphere"):
            event.accept()


class DownstreamExchangeTable(BaseExchangeTable):
    """ Downstream table class is very similar to technosphere table, just more
    restricted.
    """
    MODEL = DownstreamExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)
        self.downstream = True
        self.table_name = "downstream"

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)

        available_modules = self.generate_module_items(self.model.get_key(self.currentIndex()))
        if len(available_modules) > 0:
            menu.addSeparator()
            if len(available_modules) > 1:
                sub_menu = menu.addMenu(mlca_qicons.modular_system, "Add activity to module")
            else:
                sub_menu = menu
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

        menu.exec_(event.globalPos())

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

        modules = msc.related_activities[key]
        for module in modules:
            if module[0] == item_name:
                break
        if module[1] == 'output':
            mlca_signals.replace_output.emit((module[0], key))
        elif module[1] == 'chain':
            mlca_signals.add_to_chain.emit((module[0], key))
        signals.show_tab.emit("Modular System")
