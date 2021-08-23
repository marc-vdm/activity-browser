from ...ui.tables.models.base import (
    PandasModel,
    BaseTreeModel,
    TreeItem)

import brightway2 as bw
from activity_browser.signals import signals

from PySide2.QtCore import QModelIndex, Qt
import pandas as pd
from activity_browser.bwutils import AB_metadata

from .mLCA_signals import mlca_signals
from .modular_system_controller import modular_system_controller as msc


class ModuleDatabaseModel(PandasModel):
    """Contain data for all modules in the modular system database."""
    HEADERS = ["Name", "out/chain/cuts", "Outputs", "Cuts", "Chain"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.sync)
        mlca_signals.module_db_changed.connect(self.sync)

    def get_module_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        data = []

        for raw_module in msc.get_raw_data:
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

class GenericModuleModel(PandasModel):
    HEADERS = []

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.key_col = 0
        self.module_name = None
        self.module = None

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)
        mlca_signals.module_changed.connect(self.optional_sync)

    def optional_sync(self, module_name):
        if module_name == self.module_name:
            self.sync(module_name)

    def get_activity_key(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), -1]

class GenericEditableDragModuleModel(GenericModuleModel):
    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return super().flags(index) | Qt.ItemIsEditable | Qt.ItemIsDragEnabled

class ModuleOutputsModel(GenericEditableDragModuleModel):
    """Contain data for outputs in module."""
    HEADERS = ["module product", "amount", "name", "unit", "location", "reference product", "database", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.connect_signals()

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Whenever data is changed, call an update to the relevant exchange
                or activity.
                """
        key = self.get_activity_key(index)
        module_product = self._dataframe.iat[index.row(), 0]
        amount = self._dataframe.iat[index.row(), 1]
        old_output = (key, module_product, amount)

        header = self._dataframe.columns[index.column()]
        if header == self.HEADERS[0]:
            module_product = value
        elif header == self.HEADERS[1]:
            amount = value

        new_output = (key, module_product, amount)

        if old_output != new_output:
            module_old_new = (self.module_name, old_output, new_output)
            mlca_signals.alter_output.emit(module_old_new)
        return True

    def sync(self, module_name: str) -> None:
        if module_name == '':
            self.updated.emit()
            return
        self.module_name = module_name
        for raw_module in msc.get_raw_data:
            if raw_module['name'] == module_name:
                outputs = raw_module['outputs']
                break

        output_keys = []
        for output in outputs:
            for key in output[0:-2]:
                output_keys.append((key, output[-2], output[-1]))

        data = []
        for out_key, module_product, amount in output_keys:
            db = AB_metadata.get_database_metadata(out_key[0])
            row = db[db['key'] == out_key]
            data.append({
                "module product": module_product,
                "amount": amount,
                "name": row['name'].values[0],
                "unit": row['unit'].values[0],
                "location": row['location'].values[0],
                "reference product": row['reference product'].values[0],
                "database": out_key[0],
                "key": out_key
            })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

    def get_output_data(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        output_data = (self._dataframe.iat[idx.row(), -1],
                       self._dataframe.iat[idx.row(), 0],
                       self._dataframe.iat[idx.row(), 1]
                       )
        return output_data

class ModuleChainModel(GenericModuleModel):
    """Contain data for chain in module."""
    HEADERS = ["reference product", "name", "unit", "location", "database", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.connect_signals()

    def sync(self, module_name: str) -> None:
        if module_name == '':
            self.updated.emit()
            return
        self.module_name = module_name
        self.module = msc.get_modular_system.get_module(module_name)
        for raw_module in msc.get_raw_data:
            if raw_module['name'] == module_name:
                chain = raw_module['chain']
                break

        databases = list(set(c[0] for c in chain))

        # check if there is data, otherwise, make empty df
        if len(databases) == 0:
            self._dataframe = pd.DataFrame([], columns=self.HEADERS)
        else:
            chain_df = pd.DataFrame()
            for database in databases:
                db = AB_metadata.get_database_metadata(database)
                db = db[db['key'].isin(chain)]
                chain_df = pd.concat([chain_df, db])

            chain_df = chain_df[self.HEADERS]
            self._dataframe = chain_df

        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

class ModuleCutsItem(TreeItem):
    """ Item in ModuleCutsModel."""
    @classmethod
    def build_item(cls, cut, parent: TreeItem) -> 'ModuleCutsItem':
        item = cls(list(cut), parent)
        parent.appendChild(item)
        return item

class ModuleCutsModel(BaseTreeModel):
    """Contain data for chain in module."""
    HEADERS = ["product", "amount", "name", "unit", "location", "database", "key", "cut"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.root = ModuleCutsItem.build_root(self.HEADERS)
        self._dataframe = None
        self.key_col = 0
        self.cut_col = 0
        self.full_cuts = []
        self.module_name = None

        self.setup_model_data()
        self.connect_signals()

    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return super().flags(index) | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Whenever data is changed, call an update to the cut name."""
        # go to the first child of the root(cut name), and get product/name/location/amt and filter DF to get cut
        cut = self._dataframe[(self._dataframe["product"] == index.child(0, 0).data()) &
                              (self._dataframe["amount"] == index.child(0, 1).data()) &
                              (self._dataframe["name"] == index.child(0, 2).data()) &
                              (self._dataframe["location"] == index.child(0, 4).data())]['cut'].to_list()[0]
        mlca_signals.alter_cut.emit((self.module_name, cut, value))
        return True

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)
        mlca_signals.module_changed.connect(self.optional_sync)

    def optional_sync(self, module_name):
        if module_name == self.module_name:
            self.sync(module_name)

    def setup_model_data(self) -> None:
        """Construct a nested dict of the self._dataframe.

        Trigger this at the start and when a method is added/deleted.
        """
        for cut in self.full_cuts:
            # set first branch level as name
            prod_branch = ['' for i in range(len(self.HEADERS)-2)]  # change 2 to as many columns are hidden
            prod_branch[0] = cut[2]
            prod_branch = ModuleCutsItem.build_item(prod_branch, self.root)
            # set leaves with data
            data = self._dataframe[self._dataframe["cut"] == cut]
            for _, row in data.iterrows():
                ModuleCutsItem.build_item(row.to_list(), prod_branch)

    def sync(self, module_name: str) -> None:
        if module_name == '':
            cuts = []
        else:
            self.module_name = module_name

            # get data
            for raw_module in msc.get_raw_data:
                if raw_module['name'] == module_name:
                    cuts = raw_module['cuts']
                    break

        # check if there are cuts, if not, update to empty tree
        if len(cuts) == 0:
            # the tree actually needs items on first generation, otherwise it does not update on consecutive updates
            cut = ('hide', None, '')
            self.full_cuts = [cut]
            data = [{header: '' for header in self.HEADERS}]
            data[0]['cut'] = cut
        else:
            output_keys = []
            full_cuts = set()
            for cut in cuts:
                for key in cut[0:-2]:
                    output_keys.append((key, cut, cut[-1]))  # (key, unique id for every cut, amount)
                    full_cuts.add(cut)
            self.full_cuts = list(full_cuts)

            data = []
            for cut_key, cut, amount in output_keys:
                db = AB_metadata.get_database_metadata(cut_key[0])
                row = db[db['key'] == cut_key]
                data.append({
                    "product": row['reference product'].values[0],
                    "amount": amount,
                    "name": row['name'].values[0],
                    "unit": row['unit'].values[0],
                    "location": row['location'].values[0],
                    "database": cut_key[0],
                    "key": cut_key,
                    "cut": cut
                })

        # move data to dataframe
        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.cut_col = self._dataframe.columns.get_loc("cut")

        # clear old tree
        self.beginResetModel()
        self.root.clear()
        self.endResetModel()

        # make tree
        self.setup_model_data()
        self.updated.emit()
