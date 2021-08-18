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
    def __init__(self):
        self.project = bw.projects.current
        self.project_folder = bw.projects.dir

        self.modular_system = None
        self.raw_data = None
        self.outputs = None
        self.affected_activities = None
        self.related_activities = None
        self.lca_result = None

        self.modular_system_path
        self.module_names

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.project_change)
        mlca_signals.copy_module.connect(self.copy_module)
        mlca_signals.module_db_changed.connect(self.get_outputs)
        mlca_signals.module_db_changed.connect(self.get_affected_activities)
        mlca_signals.module_db_changed.connect(self.get_related_activities)
        mlca_signals.module_set_obs.connect(self.set_output_based_scaling)

        mlca_signals.add_to_chain.connect(self.add_to_chain)
        mlca_signals.remove_from_chain.connect(self.remove_from_chain)

        mlca_signals.add_to_cut.connect(self.add_to_cut)
        mlca_signals.remove_from_cut.connect(self.remove_from_cut)
        mlca_signals.alter_cut.connect(self.alter_cut)

        mlca_signals.add_to_output.connect(self.add_to_output)
        mlca_signals.remove_from_output.connect(self.remove_from_output)
        mlca_signals.replace_output.connect(self.replace_output)
        mlca_signals.alter_output.connect(self.alter_output)

    def project_change(self):
        """Get project's new modular system location"""
        # update the project/folder now that the old location is saved to
        self.project = bw.projects.current
        self.project_folder = bw.projects.dir
        # reset the data
        self.raw_data = None
        self.modular_system = None

    def save_modular_system(self):
        """Properly save modular system"""
        print('++ Save is _NOT IMPLEMENTED_ currently')
        #self.modular_system.save_to_file(self.modular_system_path)
        pass

    @property
    def get_modular_system(self, path=None, force_open=False) -> ModularSystem:
        """Load modular system from file and return the modular system object."""
        if not path:
            path = self.modular_system_path

        # only load if not loaded already
        if self.modular_system and not force_open:
            return self.modular_system
        else:
            modular_system = ModularSystem()
            modular_system.load_from_file(filepath=path)
            self.modular_system = modular_system
            # load raw data too
            self.raw_data = self.modular_system.raw_data
            # load metadata
            self.get_outputs()
            self.get_affected_activities()
            self.get_related_activities()
            return self.modular_system

    @property
    def get_raw_data(self, path=None, force_open=False):
        """Load raw modular system data and return the raw data."""
        if not path:
            path = self.modular_system_path

        # only load if not loaded already
        if self.raw_data and not force_open:
            return self.raw_data
        else:
            self.raw_data = ModularSystem().load_from_file(filepath=path, raw=True)
            return self.raw_data

    @property
    def get_modular_system_from_raw(self):
        """Generate a modular system from raw data.
        open raw and this function together do the same as the get_modular_system function."""
        if self.raw_data:
            module_list = [Module(**module) for module in self.raw_data]
            self.modular_system = ModularSystem(module_list=module_list)
            return self.modular_system
        else:
            return self.get_modular_system

    def add_module(self, module_name, outputs=[], chain=[], cuts=[], *args, **kwargs):
        """Add module to modular system."""
        # open the file
        if self.raw_data:
            modular_system = self.get_modular_system_from_raw
        else:
            modular_system = self.get_modular_system

        # add the new module
        modular_system.add_module(module_list=[{'name': module_name,
                                        'outputs': outputs,
                                        'chain': chain,
                                        'cuts': cuts
                                            }])
        self.modular_system = modular_system
        self.raw_data = modular_system.raw_data

        # save the updated modular system to disk
        self.save_modular_system()
        mlca_signals.module_db_changed.emit()

    def del_module(self, module_name):
        """Delete module from modular system."""
        # open the file
        if self.raw_data:
            modular_system = self.get_modular_system_from_raw
        else:
            modular_system = self.get_modular_system

        # delete the new module
        modular_system.remove_module([module_name])
        self.modular_system = modular_system
        self.raw_data = modular_system.raw_data

        # save the updated modular system to disk
        self.save_modular_system()
        mlca_signals.module_db_changed.emit()

    def copy_module(self, module_name, copy_name=None):
        """Copy module in modular system, copy name is 'original_COPY'."""
        # get data to copy
        for raw_module in self.raw_data:
            if raw_module['name'] == module_name:
                module = raw_module
                break
        if not copy_name:
            module['module_name'] = module['name'] + '_COPY'
        else:
            module['module_name'] = copy_name
        self.add_module(**module)

    def update_modular_system(self):
        self.modular_system.update(self.modular_system.get_modules())
        # update the raw data
        self.raw_data = self.modular_system.raw_data
        self.save_modular_system()

    def rename_module(self, old_module_name, new_module_name):
        """Rename module in modular system."""
        self.get_modular_system.get_module(old_module_name).name = new_module_name
        self.update_modular_system()
        mlca_signals.module_db_changed.emit()

    def set_module_color(self, module_name, color):
        """Change color of module in modular system."""
        self.get_modular_system.get_module(module_name).color = color
        self.update_modular_system()
        mlca_signals.module_color_set.emit(module_name)

    def set_output_based_scaling(self, module_state):
        """Set the 'output based scaling' to the desired state.

        module_state is a tuple with (module_name and the desired state)"""
        module_name, state = module_state

        self.get_modular_system.get_module(module_name).output_based_scaling = state
        self.update_modular_system()
        mlca_signals.module_changed.emit(module_name)

    def add_to_chain(self, module_key, update=True):
        """Add activity to chain.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        self.get_modular_system.get_module(module_name).chain.add(key)
        if update:
            self.update_modular_system()
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def remove_from_chain(self, module_key):
        """Remove activity from chain.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        # (potentially) remove from outputs
        self.remove_from_output(module_key, update=False)
        # (potentially) remove from cuts
        self.remove_from_cut((module_name, key, 'chain'), update=False)
        # remove from chain
        for chn in self.get_modular_system.get_module(module_name).chain:
            if chn == key:
                self.get_modular_system.get_module(module_name).chain.remove(chn)
                break
        self.update_modular_system()
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def add_to_cut(self, module_key):
        """Add activity to cut.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key

        module = self.get_modular_system.get_module(module_name)

        if not module.internal_edges_with_cuts:
            print("Nothing to cut from.")
        else:
            parents, children, value = zip(*module.internal_edges_with_cuts)
            if key in children:
                print("Cannot add cut. Activity is linked to another activity.")
            else:
                new_cuts = [(key, pcv[1], "Unspecified Input", pcv[2])
                            for pcv in module.internal_scaled_edges_with_cuts if key == pcv[0]]
                for new_cut in new_cuts:
                    self.get_modular_system.get_module(module_name).cuts.append(new_cut)
                    chain = self.get_modular_system.get_module(module_name).chain
                # remove the cut from the chain
                self.get_modular_system.get_module(module_name).remove_cuts_from_chain(chain, new_cuts)

                self.update_modular_system()
                mlca_signals.module_db_changed.emit()
                mlca_signals.module_changed.emit(module_name)

    def remove_from_cut(self, module_key_src, update=True):
        """Remove activity from output.
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
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def alter_cut(self, module_cut_new):
        """Alter cut product in cuts.
        Alters the cut product of a cut based on incoming data

        module_cut_new is a tuple with (module_name, cut, new name)"""
        module_name, old_cut, new_name = module_cut_new

        new_cut = (old_cut[0], old_cut[1], new_name, old_cut[3])
        for i, cut in enumerate(self.get_modular_system.get_module(module_name).cuts):
            if cut == old_cut:
                self.get_modular_system.get_module(module_name).cuts[i] = new_cut

        self.update_modular_system()
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def add_to_output(self, module_key):
        """Add activity to output.

        module_key is a tuple with (module_name, activity key)"""
        module_name, key = module_key
        ref_prod = bw.get_activity(key)["reference product"]
        self.get_modular_system.get_module(module_name).outputs.append((key, ref_prod, 1.0))
        self.update_modular_system()
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def remove_from_output(self, module_out, update=True):
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
            mlca_signals.module_db_changed.emit()
            mlca_signals.module_changed.emit(module_name)

    def replace_output(self, module_key):
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
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def alter_output(self, module_old_new):
        """Alter output activity in outputs.
        Alters the output of an activity based on incoming data

        module_old_new is a tuple with (module_name, old output, new output)
        output consists of: (key, custom_name, amount)"""
        module_name, old_output, new_output = module_old_new

        for i, output in enumerate(self.get_modular_system.get_module(module_name).outputs):
            if output == old_output:
                self.get_modular_system.get_module(module_name).outputs[i] = new_output

        self.update_modular_system()
        mlca_signals.module_db_changed.emit()
        mlca_signals.module_changed.emit(module_name)

    def get_outputs(self):
        """Dict of all output activities in modular system, by key."""
        outputs = {}
        for module in self.get_raw_data:
            _outputs = module['outputs']
            for output in _outputs:
                key = output[0]
                if outputs.get(key, False):
                    outputs[key].append(module['name'])
                else:
                    outputs[key] = [(module['name'], output)]
        self.outputs = outputs

    def get_affected_activities(self):
        """Dict of all activities in module, by module."""
        aa = {}
        for module in self.get_raw_data:
            activities = set(activity for activity in module['chain'])
            aa[module['name']] = list(activities)
        self.affected_activities = aa
        return aa

    def get_related_activities(self):
        """Dict of all activities in and 'next to' module, by activity.

        Each activity that is an input to a part of the module or downstream from an output is in this dict."""
        keys = {}
        _keys = {}
        for module in self.modular_system.get_modules():
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
    def module_names(self):
        if self.modular_system:
            return self.modular_system.modules
        else:
            module_names = []
            for raw_module in self.get_raw_data:
                module_names.append(raw_module['name'])
            return module_names

    @property
    def empty_modules(self):
        return [m['name'] for m in self.get_raw_data if len(m['chain']) == 0]

    @property
    def modular_system_path(self):
        """Return the modular system file, generate one if it does not exist yet"""
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

    def modular_LCA(self, methods, product_amount):
        """Get modular LCA results for all relevant pathways"""
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

    def format_results(self, results):
        data = []
        prod_mods = []

        abs_line_dict = {}
        rel_line_dict = {}
        paths = []
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
            paths.append(readable_path)

            result['path'] = readable_path
        method = result['LCIA method'] # method does not change in one set of results

        # assemble lines

        # pre assembly of products
        product_lines_abs = {}
        product_lines_rel = {}
        for product_name in list(products):
            meta_line_dict = {'method': ', '.join(method),
                              'abs_rel': 'abs',
                              'prod_mod': 'product',
                              'index': product_name,  # product name
                              'reference product': '',  # module product
                              'name': '',  # activity name
                              'location': '',  # activity location
                              'database': '',  # activity database
                              }
            product_paths = dict({p: 0 for p in paths}, **meta_line_dict)
            product_lines_abs[product_name] = product_paths
            meta_line_dict['abs_rel'] = 'rel'
            product_paths = dict({p: 0 for p in paths}, **meta_line_dict)
            product_lines_rel[product_name] = product_paths

        # assembly
        for prod_mod in prod_mods:
            product_name, module_name = prod_mod

            output = [o for o in self.get_modular_system.get_module(module_name).outputs if o[1] == product_name][0]
            activity = bw.get_activity(output[0])
            meta_line_dict = {'method': ', '.join(method),
                              'abs_rel': 'abs',
                              'prod_mod': 'name',
                              'index': module_name,  # module name
                              'reference product': output[1],  # module product
                              'name': activity.get('name'),  # activity name
                              'location': activity.get('location'),  # activity location
                              'database': output[0][0],  # activity database
                              }

            for result in results:
                path = result['path']
                if module_name in path:
                    abs_line_dict[path] = result['module contribution'][module_name]
                    rel_line_dict[path] = result['relative module contribution'][module_name]
                    if product_name in path:
                        product_lines_abs[product_name][path] = result['module contribution'][module_name]
                        product_lines_rel[product_name][path] = result['relative module contribution'][module_name]
                else:
                    abs_line_dict[path] = 0
                    rel_line_dict[path] = 0

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

        return data, paths

modular_system_controller = ModularSystemController()