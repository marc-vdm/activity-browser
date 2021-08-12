from activity_browser.ui.tables.views import ABDataFrameView, ABDictTreeView
from activity_browser.ui.icons import qicons
from .mLCA_table_models import (
    ModuleDatabaseModel,
    ModuleChainModel,
    ModuleOutputsModel,
    ModuleCutsModel)
from .mLCA_signals import mlca_signals

from PySide2 import QtWidgets
from activity_browser.signals import signals

#from .delegates import *
from activity_browser.ui.tables.delegates import *

class ModuleDatabaseTable(ABDataFrameView):
    """ TODO description
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))

        # context menu
        self.delete_module_action = QtWidgets.QAction(
            qicons.delete, "Delete module", None
        )
        self.copy_module_action = QtWidgets.QAction(
            qicons.copy, "Copy module", None
        )
        self.rename_module_action = QtWidgets.QAction(
            qicons.edit, "Rename module", None
        )

        self.model = ModuleDatabaseModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        #TODO link these signals


        self.doubleClicked.connect(
            lambda: mlca_signals.module_selected.emit(self.selected_module_name)
        ) #TODO link this also to graph view opening??

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

        # context menu
        self.delete_module_action.triggered.connect(
            lambda: mlca_signals.del_module.emit(self.selected_module_name)
        )
        self.copy_module_action.triggered.connect(
            lambda: mlca_signals.copy_module.emit(self.selected_module_name)
        )
        self.rename_module_action.triggered.connect(
            lambda: mlca_signals.rename_module.emit(self.selected_module_name)
        )

    def contextMenuEvent(self, event) -> None:
        #TODO add context items
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.delete_module_action)
        menu.addAction(self.copy_module_action)
        menu.addAction(self.rename_module_action)

        menu.exec_(event.globalPos())

    @property
    def selected_module_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_module_name(self.currentIndex())

class GenericModuleTable(ABDataFrameView):
    """ TODO description
        """
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
        #TODO link these signals
        pass
        #mlca_signals.module_selected.connect(self.update_table)

        self.open_activity_action.triggered.connect(
            lambda: signals.open_activity_tab.emit(self.selected_activity_key))
        self.open_graph_action.triggered.connect(
            lambda: signals.open_activity_graph_tab.emit(self.selected_activity_key))
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
    def selected_activity_key(self) -> str:
        """ Return the activity name of the user-selected index.
        """
        return self.model.get_activity_key(self.currentIndex())

    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.key_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def remove_activity(self):
        raise NotImplementedError("This function is not implemented")

    def update_table(self):
        pass

class ModuleOutputsTable(GenericModuleTable):
    """ TODO description
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = ModuleOutputsModel(parent=self)
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
        mlca_signals.remove_from_output.emit((self.model.module_name, self.selected_activity_key))


class ModuleChainTable(GenericModuleTable):
    """ TODO description
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = ModuleChainModel(parent=self)
        self._connect_signals()

        self.add_output_action = QtWidgets.QAction(
            qicons.add, "Add activity as output", None
        )
        self.add_output_action.triggered.connect(self.add_output)

        self.add_cut_action = QtWidgets.QAction(
            qicons.add, "Add activity as cut", None
        )
        self.add_cut_action.triggered.connect(self.add_cut)

        # allow double click to open the activity
        self.doubleClicked.connect(
            lambda: signals.open_activity_tab.emit(self.selected_activity_key)
        )
        self.doubleClicked.connect(
            lambda: signals.add_activity_to_history.emit(self.selected_activity_key)
        )

        self.table_name = 'module chain'

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.open_activity_action)
        menu.addAction(self.open_graph_action)
        menu.addAction(self.add_output_action)
        menu.addAction(self.add_cut_action)
        menu.addAction(self.remove_activity_action)
        menu.exec_(event.globalPos())

    def add_output(self):
        mlca_signals.add_to_output.emit((self.model.module_name, self.selected_activity_key))

    def add_cut(self):
        mlca_signals.add_to_cut.emit((self.model.module_name, self.selected_activity_key))

    def remove_activity(self):
        mlca_signals.remove_from_chain.emit((self.model.module_name, self.selected_activity_key))

class ModuleCutsTree(ABDictTreeView):
    """ TODO description
    """
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

        self.doubleClicked.connect(
            lambda: signals.open_activity_tab.emit(
                self.selected_activity_key)
                                   )

    @property
    def selected_activity_key(self) -> str:
        """ Return the activity name of the user-selected index.
        """
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            return tree_level[1]

    def tree_level(self, index=-1) -> tuple:
        """Return tuple of (tree level, content)."""
        indexes = self.selectedIndexes()
        if indexes[1].data() != '':
            # unhide and rehide 'key' column to extract the activity key
            self.setColumnHidden(self.model.key_col, False)
            indexes = self.selectedIndexes()
            self.setColumnHidden(self.model.key_col, True)
            return 'leaf', indexes[index].data()
        else:
            return 'root', indexes[0].data()

    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.key_col, True)
        self.setColumnHidden(self.model.cut_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def contextMenuEvent(self, event) -> None:
        if self.selected_activity_key:
            menu = QtWidgets.QMenu(self)
            menu.addAction(
                qicons.right, "Open activity",
                lambda: signals.open_activity_tab.emit(
                    self.selected_activity_key)
            )
            menu.addAction(
                qicons.graph_explorer, "Open in Graph Explorer",
                lambda: signals.open_activity_graph_tab.emit(
                    self.selected_activity_key)
            )
            menu.addAction(self.remove_cut_action)
            menu.exec_(event.globalPos())

    def remove_cut(self):
        amt = self.tree_level(index=3)
        mlca_signals.remove_from_cut.emit((self.model.module_name, self.selected_activity_key, amt[1]))

    def update_tree(self):
        pass
        if len(self.model.cut_products) == 0:
            self.hide()
        else:
            self.show()