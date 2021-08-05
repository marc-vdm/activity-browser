from PySide2.QtCore import QObject, Signal


class MlcaSignals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # mlca db change
    change_database = Signal(tuple) # carries tuple of db_name (path) and the command (open/new/copy/delete)
    database_selected = Signal(bool)

    # modules
    new_module = Signal()
    del_module = Signal(str)
    copy_module = Signal(str)
    module_db_changed = Signal()
    module_selected = Signal(str)

mlca_signals = MlcaSignals()