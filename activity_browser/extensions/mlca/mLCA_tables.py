from activity_browser.ui.tables.views import ABDataFrameView, ABDictTreeView
from activity_browser.ui.icons import qicons
from .mlca_icons import mlca_qicons

from .mLCA_table_models import (
    ModuleDatabaseModel,
    ModuleChainModel,
    ModuleOutputsModel,
    ModuleCutsModel)
from .mLCA_signals import mlca_signals

from PySide2 import QtWidgets, QtCore
from activity_browser.signals import signals

from activity_browser.ui.tables.delegates import *

class ModuleDatabaseTable(ABDataFrameView):
    """Table that shows all modules in the modular system."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))

        # context menu
        self.delete_module_action = QtWidgets.QAction(
            qicons.delete, "Delete module", None
        )
        self.delete_modules_action = QtWidgets.QAction(
            qicons.delete, "Delete modules", None
        )
        self.copy_module_action = QtWidgets.QAction(
            qicons.copy, "Copy module", None
        )
        self.copy_modules_action = QtWidgets.QAction(
            qicons.copy, "Copy modules", None
        )
        self.rename_module_action = QtWidgets.QAction(
            qicons.edit, "Rename module", None
        )
        self.export_modules_action = QtWidgets.QAction(
            mlca_qicons.save_db, "Export module(s)", None
        )

        self.model = ModuleDatabaseModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self._connect_signals()

        self.table_name = 'modules'

    def _connect_signals(self):
        self.doubleClicked.connect(
            lambda: mlca_signals.module_selected.emit(self.selected_module_name)
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

        # context menu
        self.delete_module_action.triggered.connect(
            lambda: mlca_signals.del_module.emit(self.selected_module_name)
        )
        self.delete_modules_action.triggered.connect(
            lambda: mlca_signals.del_modules.emit(self.selected_modules_names)
        )
        self.copy_module_action.triggered.connect(
            lambda: mlca_signals.copy_module.emit(self.selected_module_name)
        )
        self.copy_modules_action.triggered.connect(
            lambda: mlca_signals.copy_modules.emit(self.selected_modules_names)
        )
        self.rename_module_action.triggered.connect(
            lambda: mlca_signals.rename_module.emit(self.selected_module_name)
        )
        self.export_modules_action.triggered.connect(
            lambda: mlca_signals.export_modules.emit(self.selected_modules_names)
        )

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        if len(self.selectedIndexes()) == 1:
            menu.addAction(self.delete_module_action)
            menu.addAction(self.copy_module_action)
            menu.addAction(self.rename_module_action)
        else:
            menu.addAction(self.delete_modules_action)
            menu.addAction(self.copy_modules_action)
        menu.addAction(self.export_modules_action)

        menu.exec_(event.globalPos())

    @property
    def selected_module_name(self) -> str:
        """ Return the module name of the user-selected index.
        """
        return self.model.get_module_name(self.currentIndex())

    @property
    def selected_modules_names(self) -> list:
        """ Return the module names of the user-selected indexes.
        """
        return [self.model.get_module_name(idx) for idx in self.selectedIndexes()]

    def get_products(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_product_names(proxy)

    def get_units(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_unit_names(proxy)

class GenericModuleTable(ABDataFrameView):
    """Superclass for Outputs and Chain tables."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))

        self.open_activity_action = QtWidgets.QAction(
            qicons.right, "Open activity", None
        )
        self.open_graph_action = QtWidgets.QAction(
            qicons.graph_explorer, "Open in Graph Explorer", None
        )
        self.remove_activity_action = QtWidgets.QAction(
            qicons.delete, "Remove activity from module", None
        )

    def _connect_signals(self):
        self.open_activity_action.triggered.connect(
            lambda: signals.open_activity_tab.emit(self.get_selected_key))
        self.open_graph_action.triggered.connect(
            lambda: signals.open_activity_graph_tab.emit(self.get_selected_key))
        self.remove_activity_action.triggered.connect(self.remove_activity)

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.open_activity_action)
        menu.addAction(self.open_graph_action)
        menu.addAction(self.remove_activity_action)
        menu.exec_(event.globalPos())

    @property
    def get_selected_key(self) -> tuple:
        """ Return the activity key of the current index.
        """
        return self.model.get_activity_key(self.currentIndex())

    def get_key(self, index=None) -> tuple:
        """ Return the activity key of the dragged index (for adding key to calculation setup).
        """
        return self.model.get_activity_key(index)

    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.key_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def remove_activity(self):
        raise NotImplementedError("This function is not implemented")

class ModuleOutputsTable(GenericModuleTable):
    """Table for module outputs."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = ModuleOutputsModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self._connect_signals()

        self.remove_output_action = QtWidgets.QAction(
            qicons.delete, "Remove activity as output", None
        )
        self.remove_output_action.triggered.connect(self.remove_output)

        # make table editable
        self.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))

        self.table_name = 'module outputs'

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.open_activity_action)
        menu.addAction(self.open_graph_action)
        menu.addAction(self.remove_output_action)
        menu.exec_(event.globalPos())

    def remove_output(self):
        output = self.model.get_output_data(self.currentIndex())
        mlca_signals.remove_from_outputs.emit((self.model.module_name, output))

class ModuleChainTable(GenericModuleTable):
    """Table for module chain."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = ModuleChainModel(parent=self)
        self._connect_signals()

        self.add_output_action = QtWidgets.QAction(
            qicons.add, "Add activity as output", None
        )
        self.add_output_action.triggered.connect(self.add_output)

        self.add_cut_action = QtWidgets.QAction(
            mlca_qicons.cut, "Add activity as cut", None
        )
        self.add_cut_action.triggered.connect(self.add_cut)

        self.table_name = 'module chain'

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.open_activity_action)
        menu.addAction(self.open_graph_action)
        menu.addAction(self.add_output_action)

        # check if 'add to cut' should be enabled
        module = self.model.module
        key = self.get_selected_key
        if module.internal_edges_with_cuts:
            parents, children, value = zip(*module.internal_edges_with_cuts)
            if key not in children:
                menu.addAction(self.add_cut_action)
        menu.addAction(self.remove_activity_action)
        menu.exec_(event.globalPos())

    def add_output(self):
        mlca_signals.add_to_outputs.emit((self.model.module_name, self.get_selected_key))

    def add_cut(self):
        mlca_signals.add_to_cuts.emit((self.model.module_name, self.get_selected_key))

    def remove_activity(self):
        mlca_signals.remove_from_chain.emit((self.model.module_name, self.get_selected_key))

class ModuleCutsTree(ABDictTreeView):
    """Tree view for module cuts."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))

        self.model = ModuleCutsModel(parent=self)
        self.setModel(self.model)

        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.expandAll)
        self.model.updated.connect(self.update_tree)

        self.remove_cut_action = QtWidgets.QAction(
            qicons.delete, "Remove activity as cut", None
        )
        self.remove_cut_action.triggered.connect(self.remove_cut)

        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()
        self.doubleClicked.connect(self.on_double_click)

    def on_double_click(self):
        index = self.currentIndex()
        col = index.column()
        tree_level = self.tree_level()
        if tree_level[0] == 'root' and col == 0:
            # make cell editable
            self.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
        else:
            self.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

    @property
    def get_selected_key(self) -> str:
        """ Return the activity key of the user-selected index.
        """
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            return tree_level[1]

    @property
    def get_selected_cut(self) -> tuple:
        """ Return the cut of the user-selected index.
        """
        tree_level = self.tree_level(index=-1)
        if tree_level[0] == 'leaf':
            return tree_level[1]

    def tree_level(self, index=-2, indexes=None) -> tuple:
        """Return tuple of (tree level, content)."""
        if not indexes:
            indexes = self.selectedIndexes()
        if indexes[1].data() != '':
            index = self.get_any_index(index)
            return 'leaf', index.data()
        else:
            return 'root', indexes[0].data()

    def get_any_index(self, index):
        # unhide and rehide 'key' column to extract the activity key
        self.setColumnHidden(self.model.key_col, False)
        self.setColumnHidden(self.model.cut_col, False)
        indexes = self.selectedIndexes()
        self.setColumnHidden(self.model.key_col, True)
        self.setColumnHidden(self.model.cut_col, True)
        return indexes[index]

    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.key_col, True)
        self.setColumnHidden(self.model.cut_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def contextMenuEvent(self, event) -> None:
        if self.get_selected_key:
            menu = QtWidgets.QMenu(self)
            menu.addAction(
                qicons.right, "Open activity",
                lambda: signals.open_activity_tab.emit(
                    self.get_selected_key)
            )
            menu.addAction(
                qicons.graph_explorer, "Open in Graph Explorer",
                lambda: signals.open_activity_graph_tab.emit(
                    self.get_selected_key)
            )
            menu.addAction(self.remove_cut_action)
            menu.exec_(event.globalPos())

    def remove_cut(self):
        mlca_signals.remove_from_cuts.emit((self.model.module_name, self.get_selected_cut, 'cut tree view'))

    def update_tree(self):
        pass
        if len(self.model.full_cuts) == 0:
            self.hide()
        else:
            self.show()
