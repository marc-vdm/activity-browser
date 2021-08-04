from ...ui.tables.models.base import (
    PandasModel,
    BaseTreeModel,
    TreeItem)
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
    HEADERS = ["custom name", "quantity", "unit", "product", "name", "location", "database", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.manager = ModularSystemDataManager()
        self.key_col = 0
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

        databases = set()
        output_keys = []
        for output in outputs:
            for key in output[0:-2]:
                databases.add(key[0])
                output_keys.append((key, output[-2], output[-1]))

        databases = list(databases)

        data = []
        for database in databases:
            db = AB_metadata.get_database_metadata(database)
            for out_key, custom_name, quantity in output_keys:
                row = db[db['key'] == out_key]
                data.append({
                    "custom name": custom_name,
                    "quantity": quantity,
                    "unit": row['unit'].values[0],
                    "product": row['reference product'].values[0],
                    "name": row['name'].values[0],
                    "location": row['location'].values[0],
                    "database": out_key[0],
                    "key": out_key
                })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

class ModuleChainModel(PandasModel):
    """Contain data for chain in module."""
    HEADERS = ["product", "name", "location", "unit", "database", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.manager = ModularSystemDataManager()
        self.key_col = 0
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

        chain_df = chain_df[["reference product", "name", "location", "unit", "database", "key"]]
        chain_df.rename(columns={"reference product": "product"}, inplace=True)
        self._dataframe = chain_df
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

class ModuleCutsItem(TreeItem):
    """ Item in ModuleCutsModel."""

    #@classmethod
    #def build_header(cls, header: str, parent: TreeItem) -> 'ModuleCutsItem':
    #    item = cls([header, "", "", ""], parent)
    #    parent.appendChild(item)
    #    return item

    @classmethod
    def build_item(cls, cut, parent: TreeItem) -> 'ModuleCutsItem':
        item = cls(list(cut), parent)
        parent.appendChild(item)
        return item

class ModuleCutsModel(BaseTreeModel):
    """Contain data for chain in module."""
    HEADERS = ["product", "name", "location", "amount", "unit", "database", "key", "cut"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.root = ModuleCutsItem.build_root(self.HEADERS)
        self.manager = ModularSystemDataManager()
        self._dataframe = None
        self.key_col = 0
        self.cut_col = 0

        self.setup_model_data()
        self.connect_signals()

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)

    def setup_model_data(self) -> None:
        """Construct a nested dict of the self._dataframe.

        Trigger this at the start and when a method is added/deleted.
        """
        pass

    def sync(self, module_name: str) -> None:
        self.beginResetModel()
        self.root.clear()
        self.endResetModel()

        for raw_module in self.manager.open_raw():
            if raw_module['name'] == module_name:
                cuts = raw_module['cuts']
                break

        databases = set()
        output_keys = []
        c = 0
        for cut in cuts:
            c += 1
            for key in cut[0:-2]:
                databases.add(key[0])
                output_keys.append((key, str(cut[-2] + '::' + str(c)), cut[-1]))

        databases = list(databases)

        data = []
        for database in databases:
            db = AB_metadata.get_database_metadata(database)
            for cut_key, cut, amount in output_keys:
                row = db[db['key'] == cut_key]
                data.append({
                    "product": row['reference product'].values[0],
                    "name": row['name'].values[0],
                    "location": row['location'].values[0],
                    "amount": amount,
                    "unit": row['unit'].values[0],
                    "database": cut_key[0],
                    "key": cut_key,
                    "cut": cut
                })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.cut_col = self._dataframe.columns.get_loc("cut")

        self.setup_model_data()
        self.updated.emit()
