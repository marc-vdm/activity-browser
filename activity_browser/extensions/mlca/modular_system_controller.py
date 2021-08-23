import os

import brightway2 as bw
import pandas as pd

from .module import Module
from .modularsystem import ModularSystem
from .mLCA_signals import mlca_signals
from activity_browser.signals import signals


class ModularSystemController(object):
    """Manages the data of the modular system.
    Controller takes care of saving data to the right place, opening the right modular systems and editing any data."""
    def __init__(self) -> None:
        self.project = bw.projects.current
        self.project_folder = bw.projects.dir

        self.modular_system_path
        self.modular_system = None
        self.raw_data = None
        self.get_modular_system
        self.module_names

        self.outputs = None
        self.affected_activities = None
        self.related_activities = None
        self.lca_result = None

        self.connect_signals()

    def connect_signals(self) -> None:
        signals.project_selected.connect(self.project_change)
        mlca_signals.copy_module.connect(self.copy_module)
        mlca_signals.copy_modules.connect(self.copy_modules)
        mlca_signals.module_db_changed.connect(self.get_affected_activities)
        mlca_signals.module_db_changed.connect(self.get_related_activities)
        mlca_signals.module_set_obs.connect(self.set_output_based_scaling)

        mlca_signals.add_to_chain.connect(self.add_to_chain)
        mlca_signals.remove_from_chain.connect(self.remove_from_chain)

        mlca_signals.add_to_cuts.connect(self.add_to_cuts)
        mlca_signals.remove_from_cuts.connect(self.remove_from_cuts)
        mlca_signals.alter_cut.connect(self.alter_cut)

        mlca_signals.add_to_outputs.connect(self.add_to_outputs)
        mlca_signals.remove_from_outputs.connect(self.remove_from_outputs)
        mlca_signals.replace_output.connect(self.replace_output)
        mlca_signals.alter_output.connect(self.alter_output)

        signals.exchange_modified.connect(self.db_exchange_modified)
        signals.exchanges_deleted.connect(self.db_exchange_deleted)
        signals.activity_modified.connect(self.db_activity_modified)
        signals.activity_deleted.connect(self.db_activity_deleted)

    def project_change(self) -> None:
        """Get projects new modular system location, resets class data."""
        # update the project/folder now that the old location is saved to
        self.project = bw.projects.current
        self.project_folder = bw.projects.dir

        # reset the class data
        self.reset_modular_system(full_system=True)
        mlca_signals.module_db_changed.emit()

    # RETRIEVE OR SAVE DATA FROM/TO DISK

    def save_modular_system(self, modular_system=None, path=None) -> None:
        """Properly save modular system."""
        if not path:
            path = self.modular_system_path
        if not modular_system:
            modular_system = self.modular_system

        modular_system.save_to_file(path)

    def import_modules(self, path: str) -> None:
        """Import modules from path."""
        modular_system = self.get_modular_system
        modular_system.load_from_file(filepath=path, append=True)
        self.modular_system = modular_system
        self.raw_data = self.modular_system.raw_data

        self.save_modular_system()
        mlca_signals.module_db_changed.emit()

    def export_modules(self, export_names: list, path: str) -> None:
        """Export list of modules to path."""
        if export_names == self.module_names:
            # export the entire modular system
            self.save_modular_system(path=path)
        else:
            # get the modules to be exported and export them
            export_modules = [module for module in self.raw_data if module['name'] in export_names]
            export_system = self.get_modular_system_from_raw(export_modules)
            self.save_modular_system(modular_system=export_system, path=path)

    @property
    def get_modular_system(self, path=None) -> ModularSystem:
        """Load modular system from file and return the modular system object."""
        if not path:
            path = self.modular_system_path

        # only load if not loaded already
        if self.modular_system:
            return self.modular_system
        elif type(self.raw_data) == list:
            self.modular_system = self.get_modular_system_from_raw(self.raw_data)
            self.get_outputs
            return self.modular_system
        else:
            modular_system = ModularSystem()
            modular_system.load_from_file(filepath=path)
            self.modular_system = modular_system
            # update raw data
            self.raw_data = self.modular_system.raw_data
            # metadata is updated through signals in individual functions

            self.get_outputs
            return self.modular_system

    @property
    def get_raw_data(self, path=None) -> list:
        """Load raw modular system data and return the raw data."""
        if not path:
            path = self.modular_system_path

        # only load if not loaded already
        if type(self.raw_data) == list:
            return self.raw_data
        else:
            self.raw_data = ModularSystem().load_from_file(filepath=path, raw=True)
            return self.raw_data

    def get_modular_system_from_raw(self, raw_data: list) -> ModularSystem:
        """Generate a modular system from raw data.

        Open raw and this function together do the same as the get_modular_system function."""

        module_list = [Module(**module) for module in raw_data]
        return ModularSystem(module_list=module_list)

    def reset_modular_system(self, full_system=False) -> None:
        """Completely reset class data for the modular system."""
        self.modular_system = None
        self.raw_data = None

        self.outputs = None
        self.affected_activities = None
        self.related_activities = None
        self.lca_result = None

        self.get_raw_data
        if full_system:
            self.get_modular_system_from_raw(self.raw_data)
        self.get_outputs
        self.get_affected_activities()
        self.get_related_activities()

    # EDITING FULL MODULES
    # create/remove/copy entire modules

    def add_module(self, module_name: str, outputs=[], chain=[], cuts=[], save=True, *args, **kwargs) -> None:
        """Add module to modular system."""
        # get modular system
        modular_system = self.get_modular_system

        # add the new module
        modular_system.add_module(module_list=[{'name': module_name,
                                                'outputs': outputs,
                                                'chain': chain,
                                                'cuts': cuts
                                                }])
        self.modular_system = modular_system
        self.raw_data = modular_system.raw_data

        if save:
            # save the updated modular system to disk
            self.save_modular_system()
            self.get_outputs
            mlca_signals.module_db_changed.emit()

    def del_module(self, module_name: str, save=True) -> None:
        """Delete module from modular system."""
        # delete the module
        self.get_modular_system.remove_module([module_name])
        self.raw_data = self.modular_system.raw_data

        if save:
            # save the updated modular system to disk
            self.save_modular_system()
            self.get_outputs
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_selected.emit('')

    def copy_module(self, module_name: str, copy_name=None, save=True) -> None:
        """Copy module in modular system, default copy name is 'original_COPY'."""
        # get data to copy
        for raw_module in self.raw_data:
            if raw_module['name'] == module_name:
                module = raw_module
                break
        if not copy_name:
            module['module_name'] = module['name'] + '_COPY'
        else:
            module['module_name'] = copy_name

        self.add_module(**module, save=save)

    def copy_modules(self, module_names):
        """Copy multiple modules in modular system."""
        for module_name in module_names:
            self.copy_module(module_name, save=False)
        self.save_modular_system()
        self.get_outputs
        mlca_signals.module_db_changed.emit()

    # EDITING DATA IN MODULES - FROM ACTIVITY CHANGES
    # change modules due to changes made to activities (like removing an exchange)

    def db_activity_modified(self, key: tuple, field: str, value: object) -> None:
        """Edit references to edited activities in modules."""
        self.activity_modify(self.module_names, key)

    def db_activity_deleted(self, key: tuple) -> None:
        """Remove references to deleted activities in modules."""
        self.activity_delete(self.module_names, key)

    def db_exchange_modified(self, exchange: object, field: str, value: object) -> None:
        """Edit references to edited activities in modules."""
        check_modules = set()
        key_in = exchange.input.key
        key_out = exchange.output.key
        for module_name in self.module_names:
            if key_out in self.affected_activities.get(module_name, False):
                check_modules.add(module_name)
        self.activity_modify(list(check_modules), key_in)

    def db_exchange_deleted(self, exchanges: list) -> None:
        """Remove references to deleted activities in modules."""
        check_modules = set()
        for exchange in exchanges:
            key_in = exchange.input.key
            key_out = exchange.output.key
            for module_name in self.module_names:
                if key_out in self.affected_activities.get(module_name, False):
                    check_modules.add(module_name)
            self.activity_delete(list(check_modules), key_in)

    def activity_modify(self, module_names, key):
        """Determine if the changed activity requires changes to the modular system, and perform them."""
        for module_name in module_names:
            if key in self.affected_activities.get(module_name, False):
                self.update_module(module_name)
                self.get_outputs
                mlca_signals.module_changed.emit(module_name)

    def activity_delete(self, module_names, key):
        """Determine if the deleted activity requires changes to the modular system, and perform them."""
        for module_name in module_names:
            if key in self.affected_activities.get(module_name, False):
                self.remove_from_chain((module_name, key))

    # EDITING DATA IN MODULES
    # make changes to chain/outputs/cuts or other module data

    def update_module(self, module_name) -> None:
        """Update a single module after making changes that do not affect other modules.

        Updates to modules are only required when making changes to Outputs, Chain or Cuts
        This function is called after changes are made to a module and the module data needs to be updated.
        Should be called after updating the whole modular system."""
        self.modular_system.get_module(module_name).update_module

    def update_modular_system(self) -> None:
        """Update the modular system after making changes to a module.

        This function is called after changes are made to a module and the modular system needs to be updated.
        Should be called before updating individual modules."""
        self.modular_system.update(self.modular_system.get_modules())
        # update the raw data
        self.raw_data = self.modular_system.raw_data
        self.save_modular_system()

    def rename_module(self, old_module_name: str, new_module_name: str) -> None:
        """Rename module in modular system."""
        self.get_modular_system.get_module(old_module_name).name = new_module_name

        self.update_modular_system()
        self.get_outputs
        mlca_signals.module_db_changed.emit()

    def set_module_color(self, module_name: str, color: str) -> None:
        """Set color of module in modular system."""
        self.get_modular_system.get_module(module_name).color = color

        self.update_modular_system()
        mlca_signals.module_color_set.emit(module_name)

    def set_output_based_scaling(self, module_state: tuple) -> None:
        """Set the 'output based scaling' to the desired state.

        module_state is a tuple with (module_name and the desired state)"""
        module_name, state = module_state

        self.get_modular_system.get_module(module_name).output_based_scaling = state
        self.update_modular_system()
        mlca_signals.module_changed.emit(module_name)

    def add_to_chain(self, module_key: tuple, update=True) -> None:
        """Add activity to chain.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        self.get_modular_system.get_module(module_name).chain.add(key)

        if update:
            self.update_modular_system()
            self.update_module(module_name)
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def remove_from_chain(self, module_key: tuple) -> None:
        """Remove activity from chain.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        # (potentially) remove from outputs
        self.remove_from_outputs(module_key, update=False)
        # (potentially) remove from cuts
        self.remove_from_cuts((module_name, key, 'chain'), update=False)
        # remove from chain
        for chn in self.get_modular_system.get_module(module_name).chain:
            if chn == key:
                self.get_modular_system.get_module(module_name).chain.remove(chn)
                break

        self.update_modular_system()
        self.update_module(module_name)
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def add_to_cuts(self, input_data: tuple) -> None:
        """Add activity to cut.

        module_key is a tuple with (module_name, activity key)"""
        if len(input_data) == 2:
            module_name, key = input_data
            product_name = "Unspecified Input"
        if len(input_data) == 3:
            module_name, key, product_name = input_data

        module = self.get_modular_system.get_module(module_name)

        if not module.internal_edges_with_cuts:
            print("Nothing to cut from.")
        else:
            parents, children, value = zip(*module.internal_edges_with_cuts)
            if key in children:
                print("Cannot add cut. Activity is linked to another activity.")
            else:
                new_cuts = [(key, pcv[1], product_name, pcv[2])
                            for pcv in module.internal_scaled_edges_with_cuts if key == pcv[0]]  # pcv = parents, children, value
                self.get_modular_system.get_module(module_name).cuts = module.cuts + new_cuts

                # update the chain
                new_chain = module.remove_cuts_from_chain(list(module.chain), new_cuts)
                self.get_modular_system.get_module(module_name).chain = new_chain

                self.update_modular_system()
                self.update_module(module_name)
                mlca_signals.module_db_changed.emit()
                mlca_signals.module_changed.emit(module_name)

    def remove_from_cuts(self, module_key_src: tuple, update=True) -> None:
        """Remove activity from cuts.

        Adds the 'cut' activity to the chain if the key is not being removed from the chain.
        module_key_src is a tuple with (module_name, activity key OR cut, source info)"""
        module_name, key_or_cut, src_info = module_key_src
        for cut in self.get_modular_system.get_module(module_name).cuts:
            # in 'cut', [0] is the key of the external activity, [1] is the module activity
            if cut[1] == key_or_cut and src_info == 'chain':
                # the activity is being deleted in chain, remove all cuts with this activity
                self.get_modular_system.get_module(module_name).cuts.remove(cut)
            elif cut == key_or_cut:
                self.add_to_chain((module_name, cut[0]), update=False)
                self.get_modular_system.get_module(module_name).cuts.remove(cut)

        if update:
            self.update_modular_system()
            self.update_module(module_name)
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def alter_cut(self, module_cut_new: tuple) -> None:
        """Alter cut product in cuts.

        Alters the cut product of a cut based on incoming data
        module_cut_new is a tuple with (module_name, cut, new name)"""
        module_name, old_cut, new_name = module_cut_new

        new_cut = (old_cut[0], old_cut[1], new_name, old_cut[3])
        for i, cut in enumerate(self.get_modular_system.get_module(module_name).cuts):
            if cut == old_cut:
                self.get_modular_system.get_module(module_name).cuts[i] = new_cut

        self.update_modular_system()
        self.update_module(module_name)
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def add_to_outputs(self, module_key: tuple) -> None:
        """Add activity to output.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        ref_prod = bw.get_activity(key)["reference product"]
        self.get_modular_system.get_module(module_name).outputs.append((key, ref_prod, 1.0))

        self.update_modular_system()
        self.update_module(module_name)
        self.get_outputs
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def remove_from_outputs(self, module_out: tuple, update=True) -> None:
        """Remove activity from output.

        module_out is a tuple with (module_name, output)"""
        module_name, _output = module_out
        for output in self.get_modular_system.get_module(module_name).outputs:
            if output == _output:
                self.get_modular_system.get_module(module_name).outputs.remove(_output)
            else:
                return

        if update:
            self.update_modular_system()
            self.update_module(module_name)
            self.get_outputs
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def replace_output(self, module_key: tuple) -> None:
        """Replace output activity in outputs.

        Removes the output and replaces with an activity 'downstream' from the output
        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        self.get_modular_system.get_module(module_name).chain.add(key)

        exchanges = [ex['input'] for ex in bw.get_activity(key).technosphere()]
        for i, output in enumerate(self.get_modular_system.get_module(module_name).outputs):
            if output[0] in exchanges:
                _, custom_name, amount = output
                self.get_modular_system.get_module(module_name).outputs[i] = (key, custom_name, amount)

        self.update_modular_system()
        self.update_module(module_name)
        self.get_outputs
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def alter_output(self, module_old_new: tuple) -> None:
        """Alter output activity in outputs.

        Alters the output (name or amount) of an activity based on incoming data
        module_old_new is a tuple with (module_name, old output, new output)
        output consists of: (key, custom_name, amount)"""
        module_name, old_output, new_output = module_old_new

        for i, output in enumerate(self.get_modular_system.get_module(module_name).outputs):
            if output == old_output:
                self.get_modular_system.get_module(module_name).outputs[i] = new_output

        self.update_modular_system()
        self.update_module(module_name)
        self.get_outputs
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    # RETRIEVING DATA
    # retrieve data about the modular system

    @property
    def get_outputs(self) -> None:
        """Dict of all output activities in modular system, by key.

        Intended to be called after changes to module outputs or the modular system (adding/removing modules)
        {key: [(module name, output)]}"""
        outputs = {}
        for module in self.get_raw_data:
            _outputs = module['outputs']
            for output in _outputs:
                key = output[0]
                _output = (module['name'], output)
                if outputs.get(key, False):
                    outputs[key].append(_output)
                else:
                    outputs[key] = [_output]
        self.outputs = outputs

    def get_affected_activities(self) -> dict:
        """Dict of all activities in module, by module.

        An activity is 'affected' by a module if the activity is part of the chain or cuts."""
        aa = {}
        for module in self.get_raw_data:
            activities = set(activity for activity in module['chain'])
            activities = activities.union(set(cut[0] for cut in module['cuts']))
            aa[module['name']] = list(activities)
        self.affected_activities = aa
        return aa

    def get_related_activities(self) -> dict:
        """Dict of all activities in and 'next to' module, by activity.

        Each activity that is an input to a part of the module or downstream from an output is in this dict."""
        keys = {}
        _keys = {}
        for module in self.get_modular_system.get_modules():
            # check for upstream processes
            for act_key in module.chain:
                activity = bw.get_activity(act_key)
                for exchange in activity.technosphere():
                    exch_key = exchange['input']
                    if keys.get(exch_key, False) \
                            and module.name not in _keys[exch_key]:
                        keys[exch_key].append((module.name, 'chain'))
                    else:
                        _keys[exch_key] = module.name
                        keys[exch_key] = [(module.name, 'chain')]
            # check for downstream processes
            for act_key, _, _ in module.outputs:
                activity = bw.get_activity(act_key)
                for exchange in activity.upstream():
                    exch_key = exchange['output']
                    if keys.get(exch_key, False) \
                            and module.name not in _keys[exch_key]:
                        keys[exch_key].append((module.name, 'output'))
                    else:
                        _keys[exch_key] = module.name
                        keys[exch_key] = [(module.name, 'output')]

        self.related_activities = keys
        return keys

    @property
    def module_names(self) -> list:
        """Return all module names of modules in the modular system."""
        if self.modular_system:
            return self.modular_system.modules
        else:
            module_names = []
            for raw_module in self.get_raw_data:
                module_names.append(raw_module['name'])
            return module_names

    @property
    def empty_modules(self) -> list:
        """Return all module names of modules with empty chain."""
        return [m['name'] for m in self.get_raw_data if len(m['chain']) == 0]

    @property
    def modular_system_path(self) -> str:
        """Return the modular system file, generate one if it does not exist yet."""
        # ms = modular system
        ms_dir = os.path.join(self.project_folder, 'modular_system')
        ms_file = os.path.join(ms_dir, 'modular_system.mlca')

        # check if folder exists, if not, generate it
        if not os.path.isdir(ms_dir):
            os.makedirs(ms_dir, exist_ok=True)

        # check if file exists, if not, generate it
        if not os.path.isfile(ms_file):
            ModularSystem().save_to_file(filepath=ms_file)
        return ms_file

    # LCA
    # calculate LCA results for a modular system

    def modular_LCA(self, methods: list, product_amount: list) -> pd.DataFrame:
        """Get modular LCA results for all relevant pathways.

        LCA is done on a list of methods, and PRODUCTS.
        This means all possible paths are calculated for a given product, not a module

        Dataframe consists of metadata columns and then one column for each entry in results (path)
        metadata columns are:
            method = the method used: str
            abs_rel = absolute or relative result: str (abs, rel)
            prod_mod = product or module indication: str (product, name)
            index = module or product name, depends on prod_mod: str
            reference product = str
            name = str
            location = str
            database = str
        Final four metadata columns are empty if product, filled for activity if module
        Each row is an entry result, with the method, abs_rel, prod_mod and index as identifiers.
        Each actual data column (path) contains the LCA score value for that module/product in the given path (column)
        """
        demand = {}
        for module, amount in product_amount:
            demand[module] = amount

        data = []
        for method in methods:

            results = self.get_modular_system.lca_alternatives(method, demand)
            _data, paths = self.format_results(results)
            data += _data

        meta_headers = ['method',
                        'abs_rel',
                        'prod_mod',
                        'index',
                        'reference product',
                        'name',
                        'location',
                        'database']
        headers = meta_headers + paths
        df = pd.DataFrame(data, columns=headers).sort_values(['index', 'reference product'])

        self.lca_result = df

    def format_results(self, results: list) -> tuple:
        """Prepare formatting of results to be put in a Pandas dataframe.

        >> The data is only a list, ready to be put in a dataframe, not a dataframe <<
        See def modular_lca above for dataframe formatting.
        """
        data = []
        prod_mods = []

        abs_line_dict = {}
        rel_line_dict = {}
        r_paths = []
        products = set()

        # get some required data
        for result in results:
            readable_path = ''
            for i in range(0, len(result['path']), 2):
                readable_path += result['path'][i + 1] + ' - ' + result['path'][i] + ' | '
                product_name = result['path'][i]
                module_name = result['path'][i + 1]
                prod_mod = (product_name, module_name)
                products.add(product_name)
                if prod_mod not in prod_mods:
                    prod_mods.append(prod_mod)
            r_paths.append(readable_path)
            result['readable path'] = readable_path

        method = result['LCIA method']  # method does not change in one set of results

        # assemble lines

        # pre assembly of products
        product_lines_abs = {}
        product_lines_rel = {}
        for product_name in list(products):
            meta_line_dict = {'method': ', '.join(method),  # method
                              'abs_rel': 'abs',  # absolute or relative result
                              'prod_mod': 'product',  # 'product' indicates this is a module_product row
                              'index': product_name,  # product name
                              'reference product': '',  # empty for product
                              'name': '',  # empty for product
                              'location': '',  # empty for product
                              'database': '',  # empty for product
                              }
            product_paths = dict({p: 0 for p in r_paths}, **meta_line_dict)
            product_lines_abs[product_name] = product_paths
            meta_line_dict['abs_rel'] = 'rel'
            product_paths = dict({p: 0 for p in r_paths}, **meta_line_dict)
            product_lines_rel[product_name] = product_paths

        # assembly
        for prod_mod in prod_mods:
            product_name, module_name = prod_mod

            output = [o for o in self.get_modular_system.get_module(module_name).outputs if o[1] == product_name][0]
            activity = bw.get_activity(output[0])
            meta_line_dict = {'method': ', '.join(method),  # method
                              'abs_rel': 'abs',  # absolute or relative result
                              'prod_mod': 'name',  # 'name' indicates this is a module_name row
                              'index': module_name,  # module name
                              'reference product': output[1],  # module product
                              'name': activity.get('name'),  # activity name
                              'location': activity.get('location'),  # activity location
                              'database': output[0][0],  # activity database
                              }

            for result in results:
                path = result['path']
                r_path = result['readable path']
                if module_name in path:
                    abs_line_dict[r_path] = result['module contribution'][module_name]
                    rel_line_dict[r_path] = result['relative module contribution'][module_name]
                    if product_name in path:
                        product_lines_abs[product_name][r_path] = result['module contribution'][module_name]
                        product_lines_rel[product_name][r_path] = result['relative module contribution'][module_name]
                else:
                    abs_line_dict[r_path] = 0
                    rel_line_dict[r_path] = 0

            # create the absolute line
            line_dict = dict(meta_line_dict, **abs_line_dict)
            data.append(line_dict)
            # create the relative line
            meta_line_dict['abs_rel'] = 'rel'
            line_dict = dict(meta_line_dict, **rel_line_dict)
            data.append(line_dict)

        # add the product lines
        for product_name in products:
            data.append(product_lines_abs[product_name])
            data.append(product_lines_rel[product_name])

        return data, r_paths

modular_system_controller = ModularSystemController()
