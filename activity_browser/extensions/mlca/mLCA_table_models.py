from ...ui.tables.models import PandasModel
import brightway2 as bw
from activity_browser.signals import signals

from PySide2.QtCore import QModelIndex
import pandas as pd
from activity_browser.bwutils import AB_metadata

from .mLCA_signals import mlca_signals
from .modularsystem import ModularSystemDataManager


class ModuleDatabaseModel(PandasModel):
    """Contain data for all modules in the modular system database."""
    HEADERS = ["Name", "out/chain/cuts", "Outputs", "Cuts", "Chain"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.manager = ModularSystemDataManager()
        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.sync)

    def get_module_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        data = []
        for raw_module in self.manager.open_raw():
            numbers = [len(raw_module['outputs']), len(set(raw_module['chain'])), len(set(raw_module['cuts']))]
            data.append({
                'Name': raw_module['name'],
                'out/chain/cuts': ", ".join(map(str, numbers)),
                'Outputs': ", ".join([o[1] for o in raw_module['outputs']]),
                'Chain': "//".join([bw.get_activity(c)['name'] for c in raw_module['chain']]),
                'Cuts': ", ".join(set([c[2] for c in raw_module['cuts']])),
            })
        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()

class ModuleOutputsModel(PandasModel):
    HEADERS = ["custom name", "quantity", "unit", "product", "name", "location", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.manager = ModularSystemDataManager()
        self.connect_signals()

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)

    def get_activity_key(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), -1]

    def sync(self, module_name: str) -> None:

        for raw_module in self.manager.open_raw():
            if raw_module['name'] == module_name:
                outputs = raw_module['outputs']
                break

        databases = list(set(o[0][0] for o in outputs))
        output_keys = {k: [v1, v2] for k, v1, v2 in outputs}

        data = []
        for database in databases:
            db = AB_metadata.get_database_metadata(database)
            for out_key, out_vals in output_keys.items():
                row = db[db['key'] == out_key]
                data.append({
                    "custom name": out_vals[0],
                    "quantity": out_vals[1],
                    "unit": row['unit'].values[0],
                    "product": row['reference product'].values[0],
                    "name": row['name'].values[0],
                    "location": row['location'].values[0],
                    "key": out_key
                })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()

class ModuleChainModel(PandasModel):
    """Contain data for chain in module."""
    HEADERS = ["product", "name", "location", "unit", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.manager = ModularSystemDataManager()
        self.connect_signals()

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)

    def get_activity_key(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), -1]

    def sync(self, module_name: str) -> None:

        for raw_module in self.manager.open_raw():
            if raw_module['name'] == module_name:
                chain = raw_module['chain']
                break

        databases = list(set(c[0] for c in chain))

        chain_df = pd.DataFrame()
        for database in databases:
            db = AB_metadata.get_database_metadata(database)
            db = db[db['key'].isin(chain)]
            chain_df = pd.concat([chain_df, db])

        chain_df = chain_df[["reference product", "name", "location", "unit", "key"]]
        chain_df.rename(columns={"reference product": "product"}, inplace=True)
        self._dataframe = chain_df

        self.updated.emit()
