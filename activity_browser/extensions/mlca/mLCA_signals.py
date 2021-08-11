from PySide2.QtCore import QObject, Signal


class MlcaSignals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # mlca db change
    change_database = Signal(tuple) # carries tuple of db_name (path) and the command (open/new/copy/delete)
    database_selected = Signal(bool)

    # modules
    new_module = Signal()
    new_module_from_act = Signal(tuple)
    del_module = Signal(str)
    copy_module = Signal(str)
    rename_module = Signal(str)
    module_db_changed = Signal()
    module_selected = Signal(str)

    # changes to modules
    module_changed = Signal(tuple)
    module_set_color = Signal(str)
    module_color_set = Signal(str)
    add_to_chain = Signal(tuple)
    remove_from_chain = Signal(tuple)
    add_to_cut = Signal(tuple)
    remove_from_cut = Signal(tuple)
    add_to_output = Signal(tuple)
    remove_from_output = Signal(tuple)
    replace_output = Signal(tuple)

mlca_signals = MlcaSignals()