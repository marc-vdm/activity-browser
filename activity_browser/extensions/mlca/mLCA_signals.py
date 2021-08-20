from PySide2.QtCore import QObject, Signal


class MlcaSignals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # db management
    import_modular_system = Signal()
    export_modules = Signal(list)

    # modules
    new_module = Signal()
    new_module_from_act = Signal(tuple)
    del_module = Signal(str)
    del_modules = Signal(list)
    copy_module = Signal(str)
    copy_modules = Signal(list)
    rename_module = Signal(str)
    module_db_changed = Signal()
    module_selected = Signal(str)

    # changes to modules
    module_changed = Signal(tuple)
    module_set_obs = Signal(tuple)
    module_set_color = Signal(str)
    module_color_set = Signal(str)
    add_to_chain = Signal(tuple)
    remove_from_chain = Signal(tuple)
    add_to_cuts = Signal(tuple)
    remove_from_cuts = Signal(tuple)
    alter_cut = Signal(tuple)
    add_to_outputs = Signal(tuple)
    remove_from_outputs = Signal(tuple)
    replace_output = Signal(tuple)
    alter_output = Signal(tuple)

mlca_signals = MlcaSignals()