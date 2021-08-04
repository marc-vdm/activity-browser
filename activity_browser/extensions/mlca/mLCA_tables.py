from ...ui.tables.views import ABDataFrameView
from .mLCA_table_models import ModuleDatabaseModel, ModuleChainModel, ModuleOutputsModel
from .mLCA_signals import mlca_signals

from PySide2 import QtWidgets
from activity_browser.signals import signals


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

        self.model = ModuleDatabaseModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        #TODO link these signals


        self.doubleClicked.connect(
            lambda p: mlca_signals.module_selected.emit(self.model.get_module_name(p))
        ) #TODO link this also to graph view opening??

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self) -> None:
        #TODO add context items
        menu = QtWidgets.QMenu(self)

    @property
    def selected_module_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_module_name(self.currentIndex())

class ModuleOutputsTable(ABDataFrameView):
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

        self.model = ModuleOutputsModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        #TODO link these signals
        pass
        #mlca_signals.module_selected.connect(self.update_table)

        self.doubleClicked.connect(
            lambda p: signals.open_activity_tab.emit(self.model.get_activity_key(p))
        )  # TODO link this also to graph view opening??
        self.doubleClicked.connect(
            lambda p: signals.add_activity_to_history.emit(self.model.get_activity_key(p))
        )

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self) -> None:
        #TODO add context items
        menu = QtWidgets.QMenu(self)

    @property
    def selected_module_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_module_name(self.currentIndex())

    def update_table(self):
        pass

class ModuleChainTable(ABDataFrameView):
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

        self.model = ModuleChainModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        #TODO link these signals
        pass
        #mlca_signals.module_selected.connect(self.update_table)

        self.doubleClicked.connect(
            lambda p: signals.open_activity_tab.emit(self.model.get_activity_key(p))
        )  # TODO link this also to graph view opening??
        self.doubleClicked.connect(
            lambda p: signals.add_activity_to_history.emit(self.model.get_activity_key(p))
        )

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self) -> None:
        #TODO add context items
        menu = QtWidgets.QMenu(self)

    @property
    def selected_module_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_module_name(self.currentIndex())

    def update_table(self):
        pass
