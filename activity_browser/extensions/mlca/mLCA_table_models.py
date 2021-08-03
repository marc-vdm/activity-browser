from ...ui.tables.models import PandasModel
import brightway2 as bw
from activity_browser.signals import signals

from PySide2.QtCore import QModelIndex, Slot
import pandas as pd
from pathlib import Path



from .mLCA_signals import mlca_signals
from .modularsystem import ModularSystem, ModularSystemDataManager





class ModuleDatabaseModel(PandasModel):
    HEADERS = ["Name", "out/chain/cuts", "Outputs", "Cuts", "Chain"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.db_path = None
        self.mlca_db = ModularSystem()

        self.connect_signals()

    def connect_signals(self):
        mlca_signals.module_selected.connect(self.sync)
        #signals.module_changed.connect(self.sync)

        mlca_signals.change_database.connect(self.sync)

    def get_module_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def open_mlca_db(self, path) -> None:
        self.mlca_db.load_from_file(filepath=path)

    def convert_pandas(self):
        data = []
        for mp_data in self.mlca_db.raw_data:
            numbers = [len(mp_data['outputs']), len(set(mp_data['chain'])), len(set(mp_data['cuts']))]

            print('+++\n', {'chain': "//".join([bw.get_activity(c)['name'] for c in mp_data['chain']])})
            data.append({
                'Name': mp_data['name'],
                'out/chain/cuts': ", ".join(map(str, numbers)),
                'Outputs': ", ".join([o[1] for o in mp_data['outputs']]),
                'Chain': "//".join([bw.get_activity(c)['name'] for c in mp_data['chain']]),
                'Cuts': ", ".join(set([c[2] for c in mp_data['cuts']])),
            })

    @Slot(tuple, name='mlcaDbChanged')
    def sync(self, db_data: tuple) -> None:
        pass
        #TODO implement some sync based on old sync below
        # Data should be pulled in here from the right mlca file
        db_path, state = db_data
        f_name = Path(db_path).stem

        #TODO enable some check that if a current DB is loaded that user is asked to save before just overwriting their stuff
        # this check should give 4 options: discard (throw away changes), save, save as & cancel (stop 'leaving' current db)

        if state == 'open':
            # open the db
            """ We don't check whether the mLCA DB was already open, as the mLCA DB could have been changed outside 
            of AB. As the background (ecoinvent) DB was already opened (and in meta-data store), re-opening the mLCA 
            DB should take very little time."""
            self.open_mlca_db(db_path)

            # make data table-ready
            data = []
            for mp_data in self.mlca_db.raw_data:
                numbers = [len(mp_data['outputs']), len(set(mp_data['chain'])), len(set(mp_data['cuts']))]

                data.append({
                    'Name': mp_data['name'],
                    'out/chain/cuts': ", ".join(map(str, numbers)),
                    'Outputs': ", ".join([o[1] for o in mp_data['outputs']]),
                    'Chain': "//".join([bw.get_activity(c)['name'] for c in mp_data['chain']]),
                    'Cuts': ", ".join(set([c[2] for c in mp_data['cuts']])),
                })
            self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
            # set new db_path name
            self.db_path = db_path

            self.updated.emit()

            print('+++ Opened mLCa database:', f_name)
        elif state == 'new':
            # set new db_path name
            if not db_path.endswith('.pickle') and not db_path.endswith('.mlca'):
                db_path += '.mlca'
            self.db_path = db_path

            print('+++ Created new mLCa database:', self.db_path)

            self.mlca_db = ModularSystem()

            self.sync((self.db_path, 'save'))

        elif state == 'delete':

            # check if current db is being deleted -> make sure table is hidden and DB label reset
            # else: remove the db silently
            if db_path == self.db_path:
                pass
            else:
                pass
            print('+++ Deleted mLCa database:', f_name)

        elif state == 'save':
            self.mlca_db.save_to_file(filepath=db_path)

            # some code to copy the db
            # then just call sync again with open command and new file

            print('+++ Saved mLCa database:', f_name)

            self.updated.emit()

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

class ModuleDatabaseModel(PandasModel):
    """Contain data for all modules in the modular system database"""
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
        for mp_data in self.manager.open_raw():

            numbers = [len(mp_data['outputs']), len(set(mp_data['chain'])), len(set(mp_data['cuts']))]

            print('+++\n', {'chain': "//".join([bw.get_activity(c)['name'] for c in mp_data['chain']])})
            data.append({
                'Name': mp_data['name'],
                'out/chain/cuts': ", ".join(map(str, numbers)),
                'Outputs': ", ".join([o[1] for o in mp_data['outputs']]),
                'Chain': "//".join([bw.get_activity(c)['name'] for c in mp_data['chain']]),
                'Cuts': ", ".join(set([c[2] for c in mp_data['cuts']])),
            })
        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()

class ModuleChainModel(PandasModel):
    HEADERS = ["product", "name", "location", "amount", "unit", "database"]

    def __init__(self, parent=None, module=None):
        super().__init__(parent=parent)

        self.module = module

        self.connect_signals()

    def connect_signals(self):
        pass

    def get_SOMETHING_name(self, proxy: QModelIndex) -> str:
        #TODO replace SOMETHING name
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def open_mlca_db(self, path) -> None:
        self.mlca_db.load_from_file(filepath=path)

    def convert_pandas(self):
        data = []

    @Slot(tuple, name='mlcaDbChanged')
    def sync(self, db_data: tuple) -> None:
        pass