from ...ui.tables.models import PandasModel
from activity_browser.signals import signals

from PySide2.QtCore import QModelIndex
import pandas as pd
from pathlib import Path



from .mLCA_signals import mlca_signals
from .modularsystem import ModularSystem





class ModuleDatabaseModel(PandasModel):
    HEADERS = ["Name", "out/chain/cuts", "Outputs", "Cuts", "Chain"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.db_path = None
        self.mlca_db = None

        #signals.module_selected.connect(self.sync)
        #signals.module_changed.connect(self.sync)
        mlca_signals.change_database.connect(self.sync)

    def get_module_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def open_mlca_db(self, path) -> None:
        self.mlca_db = ModularSystem.load_from_file(self, filepath=path)

    def sync(self, db_data):
        pass
        #TODO implement some sync based on old sync below
        # Data should be pulled in here from the right mlca file

        db_path, state = db_data
        f_name = Path(db_path).stem

        if state == 'open':

            # open the db
            self.open_mlca_db(db_path)

            # set current db_path name
            self.db_path = db_path

            print('+++ Opened mLCa database:', f_name)
        elif state == 'new':
            pass

            print('+++ Created new mLCa database:', f_name)
        elif state == 'copy':
            pass

            print('+++ Copied mLCa database:', f_name)
        elif state == 'delete':
            pass

            print('+++ Deleted mLCa database:', f_name)
            # check if current db is being deleted -> make sure table is hidden and DB label reset
            # else: remove the db silently
        else:
            raise Exception('Not implemented error - >{}< keyword is not implemented'.format(state))

        #TODO code here should make table visible from the DB above


        """
        # code below is based on the assumption that bw uses utc timestamps
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
        time_shift = - tz.utcoffset().total_seconds()

        data = []
        for name in natural_sort(bw.databases):
            dt = bw.databases[name].get("modified", "")
            if dt:
                dt = arrow.get(dt).shift(seconds=time_shift).humanize()
            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = project_settings.db_is_readonly(name)
            data.append({
                "Name": name,
                "Depends": ", ".join(bw.databases[name].get("depends", [])),
                "Modified": dt,
                "Records": bc.count_database_records(name),
                "Read-only": database_read_only,
            })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()"""