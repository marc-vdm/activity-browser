from ...ui.tables.views import ABDataFrameView
from .mLCA_table_models import ModuleDatabaseModel

from PySide2 import QtWidgets
from PySide2.QtWidgets import QComboBox
from activity_browser.signals import signals


class ModuleDatabaseListWidget(QComboBox):
    """ TODO description
    """
    def __init__(self):
        super(ModuleDatabaseListWidget, self).__init__()
        self.connect_signals()
        self.project_names = None

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        signals.project_selected.connect(self.sync)
        signals.projects_changed.connect(self.sync)

    def sync(self):
        #TODO implement
        pass
        """
        self.clear()
        self.project_names = sorted([project.name for project in projects])
        self.addItems(self.project_names)
        index = self.project_names.index(projects.current)
        self.setCurrentIndex(index)"""

    def on_activated(self, index):
        signals.change_project.emit(self.project_names[index])


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
            lambda p: signals.module_selected.emit(self.model.get_module_name(p))
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