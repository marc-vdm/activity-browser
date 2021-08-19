# -*- coding: utf-8 -*-
import itertools
import pickle
import networkx as nx  # TODO: get rid of this dependency
import numpy as np

from .module import Module


class ModularSystem(object):
    """
    A linked modular system holds several interlinked modules. It has methods for:

    * loading / saving linked modular systems
    * returning information, e.g. product and module names, the product-module matrix
    * determining all alternatives to produce a given functional unit
    * calculating LCA results for individual modules
    * calculating LCA results for a demand from the linked modular system (possibly for all alternatives)

    Modules *cannot* contain:
(    * 2 modules with the same name)
    * identical names for products and modules (recommendation is to capitalize module names)

    Args:

    * *module_list* (``[module]``): A list of modules
    """

    def __init__(self, module_list=None) -> None:
        self.module_list = []
        self.map_name_module = {}
        self.map_module_number = {}
        self.map_products_number = {}
        self.map_number_module = {}
        self.map_number_products = {}
        self.name_map = {}  # {activity key: output name}
        self.raw_data = []
        self.has_multi_output_modules = False
        self.has_loops = False
        if module_list:
            self.update(module_list)

    def update(self, module_list: list) -> None:
        """
        Updates the linked modular system every time modules
        are added, modified, or deleted.
        Errors are thrown in case of:

        * identical names for products and modules
        * identical names of different modules
        * if the input is not of type Module()
        """
        product_names, module_names = set(), set()
        for module in module_list:
            if not isinstance(module, Module):
                raise ValueError(u"Input must be of Modules type.")
            try:
                assert module.name not in module_names  # check if module names are unique
                module_names.add(module.name)
                product_names.update(self.get_product_names([module]))
            except AssertionError:
                raise ValueError(u'Module names must be unique.')
        for product in product_names:
            if product in module_names:
                raise ValueError(u'Product and Module names cannot be identical.')
        self.module_list = module_list
        self.map_name_module = dict([(module.name, module) for module in self.module_list])
        self.map_module_number = dict(zip(self.modules, itertools.count()))
        self.map_products_number = dict(zip(self.products, itertools.count()))
        self.map_number_module = {v: k for k, v in self.map_module_number.items()}
        self.map_number_products = {v: k for k, v in self.map_products_number.items()}
        self.update_name_map()
        self.raw_data = [module.module_data for module in self.module_list]
        # multi-output
        self.has_multi_output_modules = False
        for module in self.module_list:
            if module.is_multi_output:
                self.has_multi_output_modules = True
        # check for loops
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        if [c for c in nx.simple_cycles(G)]:
            self.has_loops = True
        else:
            self.has_loops = False

        print('\nmodular system with', len(self.products), 'products and', len(self.modules), 'modules.')
        print('Loops:', self.has_loops, ', Multi-output modules:', self.has_multi_output_modules)

    def update_name_map(self) -> None:
        """
        Updates the name map, which maps product names (outputs or cuts) to activity keys.
        This is used in the Activity Browser to automatically assign a product name to already known activity keys.
        """
        for module in self.module_list:
            for output in module.outputs:
                self.name_map[output[0]] = self.name_map.get(output[0], set())
                self.name_map[output[0]].add(output[1])
            for cut in module.cuts:
                self.name_map[cut[0]] = self.name_map.get(cut[0], set())
                self.name_map[cut[0]].add(cut[2])

    # SHORTCUTS

    @ property
    def modules(self) -> list:
        """Returns all module names."""
        return sorted([module.name for module in self.module_list])

    @ property
    def products(self) -> list:
        """Returns all product names."""
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.module_list])))

    # DATABASE METHODS (FILE I/O, MODULAR SYSTEM MODIFICATION)

    def load_from_file(self, filepath: str, append=False, raw=False) -> None:
        """
        Loads a modular database, makes a Module object from each module and
        adds them to the linked modular system.

        Args:

        * filepath: file path
        * append: adds loaded modules to the existing database if True
        """
        try:
            with open(filepath, 'rb') as infile:
                raw_data = pickle.load(infile)
                if raw:
                    return raw_data
        except:
            raise IOError(u'Could not load file.')
        module_list = [Module(**module) for module in raw_data]
        if append:
            self.add_module(module_list, rename=True)
        else:
            self.update(module_list)

    def save_to_file(self, filepath: str) -> None:
        """Saves data for each module in the modular data format using pickle and updates the linked modular system."""
        with open(filepath, 'wb') as outfile:
            pickle.dump(self.raw_data, outfile)

    def add_module(self, module_list: list, rename=False) -> None:
        """
        Adds modules to the linked modular system.

        *module_list* can contain module objects or the original data format used to initialize modules.
        """
        new_module_list = []
        for module in module_list:
            if not isinstance(module, Module):
                module = Module(**module)
            new_module_list.append(module)
        if rename:
            for module in new_module_list:
                if module.name in self.modules:
                    module.name += '__ADDED'
        self.update(self.module_list + new_module_list)

    def remove_module(self, module_list: list) -> None:
        """
        Remove modules from the linked modular system.

        *module_list* can be a list of module objects or module names.
        """
        for module in module_list:
            if not isinstance(module, Module):
                module = self.get_modules([module])
            self.module_list.remove(module[0])
        self.update(self.module_list)

    # METHODS THAT RETURN DATA FOR A SUBSET OR THE ENTIRE MODULAR SYSTEM

    def get_module(self, module_name: str) -> Module:
        """Return a module with name 'module_name'."""
        if module_name in self.modules:
            return self.map_name_module.get(module_name, None)

    def get_modules(self, module_list=None) -> list:
        """
        Returns a list of modules.

        *module_list* can be a list of module objects or module names.
        """
        # if empty list return all modules
        if not module_list:
            return self.module_list
        else:
            # if name list find corresponding modules
            if not isinstance(module_list[0], Module):
                return [self.map_name_module.get(name, None) for name in module_list if name in self.modules]
            else:
                return module_list

    def get_module_names(self, module_list=None) -> list:
        """Returns a the names of a list of modules."""
        return sorted([module.name for module in self.get_modules(module_list)])

    def get_product_names(self, module_list=None) -> list:
        """Returns the output and input product names of a list of modules.

        *module_list* can be a list of module objects or module names.
        """
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.get_modules(module_list)])))

    def get_output_names(self, module_list=None) -> list:
        """ Returns output product names for a list of modules."""
        return sorted(list(set([name for module in self.get_modules(module_list) for name in module.output_names])))

    def get_cut_names(self, module_list=None) -> list:
        """ Returns cut/input product names for a list of modules."""
        return sorted(list(set([name for module in self.get_modules(module_list) for name in module.cut_names])))

    def product_module_dict(self, module_list=None, module_names=None, product_names=None) -> dict:
        """
        Returns a dictionary that maps modules to produced products (key: product, value: module).
        Optional arguments ``module_list``, ``module_names``, ``product_names`` can used as filters.
        """
        if not module_names:
            module_names = self.modules
        if not product_names:
            product_names = self.products
        product_modules = {}
        for module in self.get_modules(module_list):
            for output in module.outputs:
                output_name = output[1]
                if output_name in product_names and module.name in module_names:
                    product_modules[output_name] = product_modules.get(output_name, [])
                    product_modules[output_name].append(module.name)
        return product_modules

    def edges(self, module_list=None) -> list:
        """
        Returns an edge list for all edges within the linked modular system.

        *module_list* can be a list of module objects or module names.
        """
        edges = []
        for module in self.get_modules(module_list):
            for cut in module.cuts:
                edges.append((cut[2], module.name))
            for output in module.outputs:
                edges.append((module.name, output[1]))
        return edges

    def get_pp_matrix(self, module_list=None) -> tuple:
        """
        Returns the product-module matrix as well as two dictionaries
        that hold row/col values for each product/module.

        *module_list* can be used to limit the scope to the contained modules
        """
        module_list = self.get_modules(module_list)
        matrix = np.zeros((len(self.get_product_names(module_list)), len(module_list)))
        map_module_number = dict(zip(self.get_module_names(module_list), itertools.count()))
        map_products_number = dict(zip(self.get_product_names(module_list), itertools.count()))
        for module in module_list:
            for product, amount in module.pp:
                matrix[map_products_number[product], map_module_number[module.name]] += amount
        return matrix, map_module_number, map_products_number

    # ALTERNATIVE PATHWAYS

    def upstream_products_modules(self, product: str) -> tuple:
        """Returns all upstream products and modules related to a certain product (functional unit)."""
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        product_ancestors = nx.ancestors(G, product)  # set
        product_ancestors.update([product])  # add product (although not an ancestor in a strict sense)
        # split up into products and modules
        ancestor_modules = [a for a in product_ancestors if a in self.modules]
        ancestor_products = [a for a in product_ancestors if a in self.products]
        return ancestor_modules, ancestor_products

    def all_pathways(self, functional_unit: str) -> list:
        """
        Returns all alternative pathways to produce a given functional unit. Data output is a list of lists.
        Each sublist contains one path made up of products and modules.
        The input Graph may not contain cycles. It may contain multi-output modules.

        Args:

        * *functional_unit*: output product
        """
        def dfs(current_node, visited, parents, direction_up=True):
            # print current_node
            if direction_up:
                visited += [current_node]
            if current_node in self.products:
                # go up to all modules if none has been visited previously, else go down
                upstream_modules = list(G.predecessors(current_node))
                if upstream_modules and not [module for module in upstream_modules if module in visited]:
                    parents += [current_node]
                    for module in upstream_modules:
                        dfs(module, visited[:], parents[:])  # needs a real copy due to mutable / immutable
                else:  # GO DOWN or finish
                    if parents:
                        downstream_module = parents.pop()
                        dfs(downstream_module, visited, parents, direction_up=False)
                    else:
                        results.append(visited)
                        # print 'Finished'
            else:  # node = module; upstream = product
                # go to one upstream product, if there is one unvisited, else go down
                upstream_products = G.predecessors(current_node)
                unvisited = [product for product in upstream_products if product not in visited]
                #print 'unvisited:', unvisited
                if unvisited:  # GO UP
                    parents += [current_node]
                    dfs(unvisited[0], visited, parents)
                else:  # GO DOWN or finish
                    if parents:
                        downstream_product = parents.pop()
                        dfs(downstream_product, visited, parents, direction_up=False)
                    else:
                        print('Finished @ module, this should not happen if a product was demanded.')
            return results

        results = []
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        return dfs(functional_unit, [], [])

    # LCA

    def scaling_vector_foreground_demand(self, module_list: list, demand: dict) -> dict:
        """
        Returns a scaling dictionary for a given demand and matrix defined by a list of modules (or names).
        Keys: module names. Values: scaling vector values.

        Args:

        * *module_list*: module objects or names
        * *demand* (dict): keys: product names, values: amount
        """
        # matrix
        matrix, map_modules, map_products = self.get_pp_matrix(module_list)
        try:
            # TODO: define conditions that must be met (e.g. square, single-output); Modules can still have multiple outputs (system expansion)
            assert matrix.shape[0] == matrix.shape[1]  # matrix needs to be square to be invertable!
            # demand vector
            demand_vector = np.zeros((len(matrix),))
            for name, amount in demand.items():
                demand_vector[map_products[name]] = amount
            # scaling vector
            scaling_vector = np.linalg.solve(matrix, demand_vector).tolist()
            scaling_dict = dict([(name, scaling_vector[index]) for name, index in map_modules.items()])
            # # foreground product demand (can be different from scaling vector if diagonal values are not 1)
            # foreground_demand = {}
            # for name, amount in scaling_dict.items():
            #     number_in_matrix = map_modules[name]
            #     product = [name for name, number in map_products.items() if number == number_in_matrix][0]
            #     foreground_demand.update({
            #         product: amount*matrix[number_in_matrix, number_in_matrix]
            #     })
            return scaling_dict  # , foreground_demand
        except AssertionError:
            print("Product-Module Matrix must be square! Currently", matrix.shape[0], 'products and', matrix.shape[1], 'modules.')

    def lca_modules(self, method: tuple, module_names=None, factorize=False) -> dict:
        """Returns a dictionary where *keys* = module name, *value* = LCA score
        """
        return dict([(module.name, module.lca(method, factorize=factorize))
                     for module in self.get_modules(module_names)])

    def lca_linked_modules(self, method: tuple, module_names: list, demand: dict) -> dict:
        """
        Performs LCA for a given demand from a linked modular system.
        Works only for square matrices (see scaling_vector_foreground_demand).

        Returns a dictionary with the following keys:

        * *path*: involved module names
        * *demand*: product demand
        * *scaling vector*: result of the demand
        * *LCIA method*: method used
        * *module contribution*: contribution of each module
        * *relative module contribution*: relative contribution
        * *LCIA score*: LCA result

        Args:

        * *method*: LCIA method
        * *module_names*: selection of modules from the linked modular system (that yields a square matrix)
        * *demand* (dict): keys: product names, values: amount
        """
        scaling_dict = self.scaling_vector_foreground_demand(module_names, demand)
        if not scaling_dict:
            return
        lca_scores = self.lca_modules(method, module_names)
        # multiply scaling vector with module LCA scores
        path_lca_score = 0.0
        module_contribution = {}
        for module, amount in scaling_dict.items():
            module_contribution.update({module: amount*lca_scores[module]})
            path_lca_score = path_lca_score + amount*lca_scores[module]
        module_contribution_relative = {}
        for module, amount in scaling_dict.items():
            module_contribution_relative.update({module: amount*lca_scores[module]/path_lca_score})

        output = {
            'path': module_names,
            'demand': demand,
            'scaling vector': scaling_dict,
            'LCIA method': method,
            'module contribution': module_contribution,
            'relative module contribution': module_contribution_relative,
            'LCA score': path_lca_score,
        }
        return output

    def lca_alternatives(self, method: tuple, demand: dict) -> list:
        """
        Calculation of LCA results for all alternatives in a linked modular system that yield a certain demand.
        Results are stored in a list of dictionaries as described in 'lca_linked_modules'.

        Args:

        * *method*: LCIA method
        * *demand* (dict): keys: product names, values: amount
        """
        if self.has_multi_output_modules:
            print('\nCannot calculate LCAs for alternatives as system contains ' \
                  'loops (', self.has_loops, ') / multi-output modules (', self.has_multi_output_modules, ').')
        else:
            path_lca_data = []
            for _demand in demand.items():
                _demand, amount = _demand
                for path in self.all_pathways(_demand):
                    path_lca_data.append(self.lca_linked_modules(method, path, {_demand: amount}))
            return path_lca_data
