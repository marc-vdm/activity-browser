from ...ui.tables.models import PandasModel
from activity_browser.signals import signals

from PySide2.QtCore import QModelIndex
import pandas as pd


class ModuleDatabaseModel(PandasModel):
    HEADERS = ["Name", "out/chain/cuts", "Outputs", "Cuts", "Chain"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.module_selected.connect(self.sync)
        signals.module_changed.connect(self.sync)

    def get_module_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        pass
        #TODO implement some sync based on old sync below
        # Data should be pulled in here from the right mlca file
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