# -*- coding: utf-8 -*-
import brightway2 as bw
from peewee import DoesNotExist
from bw2data.utils import recursive_str_to_unicode
import itertools
import numpy as np
import uuid


class Module(object):
    """A description of one or several modules from a life cycle inventory database.
     It has the following characteristics:

    * It produces one or several output products
    * It has at least one module from an inventory database
    * It has one or several scaling activities that are linked to the output of the system. They are calculated automatically based on the product output (exception: if output_based_scaling=False, see below).
    * Inputs may be cut-off. Cut-offs are remembered and can be used in a linked module to recombine modules to form supply chains (or several, alternative supply chains).

    Args:
        * *name* (``str``): Name of the module
        * *outputs* (``[(key, str, optional float)]``): A list of products produced by the module. Format is ``(key into inventory database, product name, optional amount of product produced)``.
        * *chain* (``[key]``): A list of inventory modules in the supply chain (not necessarily in order).
        * *cuts* (``[(parent_key, child_key, str, float)]``): A set of linkages in the supply chain that should be cut. These will appear as **negative** products (i.e. inputs) in the module-product table. The float amount is determined automatically. Format is (input key, output key, product name, amount).
        * *output_based_scaling* (``bool``): True: scaling activities are scaled by the user defined product outputs. False: the scaling activities are set to 1.0 and the user can define any output. This may not reflect reality or original purpose of the inventory modules.

    """
    # TODO: introduce UUID for modules?

    # INTERNAL METHODS FOR CONSTRUCTING MODULES

    def __init__(self, name: str, outputs: list,
                 chain: list, cuts: list,
                 output_based_scaling=True, color='white', **kwargs) -> None:
        self.key = None  # created when module saved to a DB
        self.name = name
        self.cuts = cuts
        self.output_based_scaling = output_based_scaling
        self.chain = self.remove_cuts_from_chain(chain, self.cuts)
        self.filtered_database = self.getFilteredDatabase(self.chain)
        self.edges = self.construct_graph(self.filtered_database)
        self.scaling_activities, self.isSimple = self.getScalingActivities(self.chain, self.edges)
        self.outputs = self.pad_outputs(outputs)
        self.mapping, self.demand, self.matrix, self.supply_vector = \
            self.get_supply_vector(self.chain, self.edges, self.scaling_activities, self.outputs)
        self.get_edge_lists
        self.pad_cuts
        self.color = color
        # a bit of convenience for users
        self.output_names = [o[1] for o in self.outputs]
        self.output_keys = [o[0] for o in self.outputs]
        self.cut_names = [c[2] for c in self.cuts]
        self.is_multi_output = len(self.outputs) > 1

    @property
    def update_module(self) -> None:
        """Update the module if changes were written to data like cuts, chain or outputs."""
        self.chain = self.remove_cuts_from_chain(list(self.chain), self.cuts)
        self.filtered_database = self.getFilteredDatabase(self.chain)
        self.edges = self.construct_graph(self.filtered_database)
        self.scaling_activities, self.isSimple = self.getScalingActivities(self.chain, self.edges)
        self.outputs = self.pad_outputs(self.outputs)
        self.mapping, self.demand, self.matrix, self.supply_vector = \
            self.get_supply_vector(self.chain, self.edges, self.scaling_activities, self.outputs)
        self.get_edge_lists
        self.pad_cuts

        self.output_names = [o[1] for o in self.outputs]
        self.output_keys = [o[0] for o in self.outputs]
        self.cut_names = [c[2] for c in self.cuts]
        self.is_multi_output = len(self.outputs) > 1

    def remove_cuts_from_chain(self, chain: list, cuts: list) -> set:
        """Remove chain items if they are the parent of a cut. Otherwise this leads to unintended LCIA results."""
        for cut in cuts:
            if cut[0] in chain:
                chain.remove(cut[0])
                print("MODULE WARNING: Cut removed from chain: " + str(cut[0]))

        return set(chain)

    def getFilteredDatabase(self, chain: set) -> dict:
        """Extract the supply chain for this module from larger database.

        Args:
            * *nodes* (set): The datasets to extract (keys in db dict)
            * *db* (dict): The inventory database, e.g. ecoinvent

        Returns:
            A filtered database, in the same dict format

        """
        chain_exc = {}
        for act_key in chain:
            try:
                activity = bw.get_activity(act_key)
            except DoesNotExist:
                print('activity does not exist in Brightway:', act_key)
                return

            chain_exc[act_key] = {'exchanges': [e for e in activity.technosphere()]}
        return chain_exc

    def construct_graph(self, db: dict) -> list:
        """Construct a list of edges (excluding self links, e.g. an electricity input to electricity production).

        Args:
            * *db* (dict): The supply chain database

        Returns:
            A list of (in, out, amount) edges.

        """
        return list(itertools.chain(*[[(tuple(e["input"]), k, e["amount"])
                    for e in v["exchanges"] if e["type"] != "production" and e["input"] != k] for k, v in db.items()]))

    def getScalingActivities(self, chain: set, edges: list) -> list:
        """Which are the scaling activities (at least one)?

        Calculate by filtering for modules which are not used as inputs.

        Args:
            * *chain* (set): The supply chain modules
            * *edges* (list): The list of supply chain edges

        Returns:
            Boolean isSimple, List heads.

        """
        used_inputs = [x[0] for x in edges if x[0] in chain]
        heads = set([tuple(x[1]) for x in edges if x[1] not in used_inputs])
        isSimple = len(heads) == 1
        return list(heads), isSimple

    def pad_outputs(self, outputs: list) -> list:
        """If not given, adds default values to outputs:

        * output name: "Unspecified Output"
        * amount: 1.0

        Args:
            * *outputs* (list): outputs

        Returns:
            Padded outputs
        """
        padded_outputs = []
        for i, output in enumerate(outputs):  # add default name and quantity if necessary
            try:
                output_name = output[1]
            except IndexError:
                output_name = "Output " + str(i)
            try:
                output_quantity = float(output[2])
            except IndexError:
                output_quantity = 1.0
            except ValueError:
                print("ValueError in output quantity. Set to 1.0")
                output_quantity = 1.0
            padded_outputs.append((output[0], output_name, output_quantity))
        # add outputs that were not specified
        for sa in self.scaling_activities:
            if sa not in [o[0] for o in outputs]:
                print("MODULE: Adding an output that was not specified: " + str(sa))
                padded_outputs.append((sa, "Unspecified Output", 1.0))
        # remove outputs that were specified, but are *not* outputs
        for o in outputs:
            if o[0] not in self.scaling_activities:
                print("MODULE: Removing a specified output that is *not* actually an output: " + str(o[0]))
                padded_outputs.remove(o)
        return padded_outputs

    def get_supply_vector(self, chain: set, edges: list,
                          scaling_activities: list, outputs: list) -> tuple:
        """Construct supply vector (solve linear system) for the supply chain of this simplified product system.

        Args:
            * *chain* (list): Nodes in supply chain
            * *edges* (list): List of edges
            * *scaling_activities* (key): Scaling activities

        Returns:
            Mapping from module keys to supply vector indices
            Supply vector (as list)

        """
        mapping = dict(*[zip(sorted(chain), itertools.count())])
        reverse_mapping = dict(*[zip(itertools.count(), sorted(chain))])

        # MATRIX (that relates to modules in the chain)
        # Diagonal values (usually 1, but there are exceptions)
        M = len(chain)
        matrix = np.zeros((M, M))
        for m in range(M):
            key = reverse_mapping[m]
            if key in self.scaling_activities and not self.output_based_scaling:
                print('\nDid not apply output based scaling to:', self.name)
                print("(This means that the scaling activity set to 1.0, while the output can be anything. " \
                      "It is up to the user to check that output quantities makes sense.)")
                diagonal_value = 1.0
            else:
                try:
                    # amount does not work for ecoinvent 2.2 multioutput as co-products are not in exchanges
                    diagonal_value = [exc.as_dict().get('amount', '') for exc in bw.get_activity(key).exchanges() if
                                      exc.as_dict()['type'] == 'production'][0]
                except IndexError:
                    print("\nNo production exchange (output) found. Output is set to 1.0 for:", self.name)
                    print("--> This may be an ecoinvent 2.2 multi-output activity. " \
                          "Manual control is necessary to insure correctness.")
                    diagonal_value = 1.0
            matrix[m, m] = diagonal_value
        # Non-diagonal values
        # Only add edges that are within our system, but allow multiple links to same product (simply add them)
        for in_, out_, a in [x for x in edges if x[0] in chain and x[1] in chain]:
            matrix[
                mapping[in_],
                mapping[out_]
            ] -= a
        # DEMAND VECTOR
        demand = np.zeros((M,))
        for sa in scaling_activities:
            if not self.output_based_scaling:
                demand[mapping[sa]] = 1.0
            else:
                for o in [output for output in outputs if output[0] == sa]:
                    demand[mapping[sa]] += o[2]
        return mapping, demand, matrix, np.linalg.solve(matrix, demand).tolist()

    @property
    def get_edge_lists(self) -> None:
        """Get lists of external and internal edges with original flow values or scaled to the module."""
        self.external_edges = \
            [x for x in self.edges if (x[0] not in self.chain and x[:2] not in set([y[:2] for y in self.cuts]))]
        self.internal_edges = \
            [x for x in self.edges if (x[0] in self.chain and x[:2] not in set([y[:2] for y in self.cuts]))]
        self.internal_edges_with_cuts = \
            [x for x in self.edges if (x[0] in self.chain or x[:2] in set([y[:2] for y in self.cuts]))]
        # scale these edges
        self.external_scaled_edges = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.external_edges]
        self.internal_scaled_edges = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.internal_edges]
        self.internal_scaled_edges_with_cuts = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.internal_edges_with_cuts]

    @property
    def pad_cuts(self) -> None:
        """Makes sure that each cut includes the amount that is cut. This is retrieved from self.internal_scaled_edges_with_cuts."""
        for i, c in enumerate(self.cuts):
            for e in self.internal_scaled_edges_with_cuts:
                if c[:2] == e[:2]:
                    try:
                        self.cuts[i] = (c[0], c[1], c[2], e[2])
                    except IndexError:
                        print("Problem with cut data: " + str(c))

    # METHODS THAT RETURN MODULE DATA

    @property
    def module_data(self) -> dict:
        """Returns a dictionary of module data as specified in the data format."""
        module_data_dict = {
            'name': self.name,
            'outputs': self.outputs,
            'chain': list(self.chain),
            'cuts': self.cuts,
            'output_based_scaling': self.output_based_scaling,
            'color': self.color,
        }
        return module_data_dict

    def get_product_inputs_and_outputs(self) -> list:
        """Returns a list of product inputs and outputs."""
        return [(cut[2], -cut[3]) for cut in self.cuts] + [(output[1], output[2]) for output in self.outputs]

    @property
    def pp(self) -> list:
        """Property shortcut for returning a list of product inputs and outputs."""
        return self.get_product_inputs_and_outputs()

    # LCA

    def get_background_lci_demand(self, foreground_amount: float) -> dict:
        demand = {}  # dictionary for the brightway2 LCA object {activity key: amount}
        for sa in self.scaling_activities:
            demand.update({sa: self.demand[self.mapping[sa]]*foreground_amount})
        for cut in self.cuts:
            demand.update({cut[0]: -cut[3]*foreground_amount})
        return demand

    def lca(self, method: tuple, amount=1.0, factorize=False) -> float:
        """Calculates LCA results for a given LCIA method and amount. Returns the LCA score."""
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        if hasattr(self, "calculated_lca"):
            self.calculated_lca.switch_method(method)
            self.calculated_lca.lcia()
        else:
            demand = self.get_background_lci_demand(amount)
            self.calculated_lca = bw.LCA(demand, method=method)
            self.calculated_lca.lci()
            if factorize:
                self.calculated_lca.decompose_technosphere()
            self.calculated_lca.lcia()
        return self.calculated_lca.score

    def lci(self, amount=1.0) -> bw.LCA.lci:
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        demand = self.get_background_lci_demand(amount)
        self.calculated_lca = bw.LCA(demand={self.key: amount})
        return self.calculated_lca.lci()

    # SAVE AS REGULAR ACTIVITY

    def save_as_bw2_dataset(self, db_name="MODULE default", unit=None,
            location=None, categories=[], save_aggregated_inventory=False) -> None:
        """Save simplified module to a database.

        Creates database if necessary; otherwise *adds* to existing database. Uses the ``unit`` and ``location`` of ``self.scaling_activities[0]``, if not otherwise provided. Assumes that one unit of the scaling activity is being produced.

        Args:
            * *db_name* (str): Name of Database
            * *unit* (str, optional): Unit of the simplified process
            * *location* (str, optional): Location of the simplified process
            * *categories* (list, optional): Category/ies of the scaling activity
            * *save_aggregated_inventory* (bool, optional): Saves in output minus input style by default (True), otherwise aggregated inventory of all inventories linked within the module

        """
        db = bw.Database(db_name)
        if db_name not in bw.databases:
            db.register()
            data = {}
        else:
            data = db.load()
        # GATHER DATASET INFORMATION
        # self.key = (unicode(db_name), unicode(uuid.uuid4().urn[9:]))  # in Python 3 all strings are in unicode
        self.key = (db_name, uuid.uuid4().urn[9:])
        activity = self.scaling_activities[0]
        metadata = bw.Database(activity[0]).load()[activity]
        # unit: if all scaling activities have the same unit, then set a unit, otherwise 'several'
        if self.scaling_activities != 1:
            units_set = set([bw.Database(sa[0]).load()[sa].get(u'unit', '') for sa in self.scaling_activities])
            if len(units_set) > 1:
                unit = 'several'  # if several units, display nothing
            else:
                unit = units_set.pop()
        # EXCHANGES
        exchanges = []
        if not save_aggregated_inventory:  # save inventory as scaling activities - cuts
            # scaling activities
            for sa in self.scaling_activities:
                exchanges.append({
                    "amount": self.demand[self.mapping[sa]],
                    "input": sa,
                    "type": "biosphere" if sa[0] in (u"biosphere", u"biosphere3") else "technosphere",
                })
            # cuts
            for cut in self.cuts:
                exchanges.append({
                    "amount": -cut[3],
                    "input": cut[0],
                    "type": "biosphere" if cut[0] in (u"biosphere", u"biosphere3") else "technosphere",
                })
        else:  # save aggregated inventory of all modules in chain
            exchanges = [{
                "amount": exc[2],
                "input": exc[0],
                "type": "biosphere" if exc[0][0] in (u"biosphere", u"biosphere3") else "technosphere",
            } for exc in self.external_scaled_edges]
        # Production amount
        exchanges.append({
            # Output value unless several outputs, then 1.0
            "amount": self.outputs[0][2] if len(self.outputs) == 1 else 1.0,
            "input": self.key,
            "type": "production"
        })
        # WRITE DATASET INFORMATION
        data[self.key] = {
            "name": self.name,
            "unit": unit or metadata.get(u'unit', ''),
            "location": location or metadata.get(u'location', ''),
            "categories": categories,
            "type": "process",
            "exchanges": exchanges,
        }

        # TODO: Include uncertainty from original databases. Can't just scale
        # uncertainty parameters. Maybe solution is to use "dummy" modules
        # like we want to do to separate inputs of same flow in any case.
        # data = db.relabel_data(data, db_name)
        db.write(recursive_str_to_unicode(data))
        db.process()
