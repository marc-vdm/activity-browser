# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import brightway2 as bw
from bw2analyzer import ContributionAnalysis

ca = ContributionAnalysis()

from .commontasks import wrap_text
from .metadata import AB_metadata


class MLCA(object):
    """Wrapper class for performing LCA calculations with many functional units and LCIA methods.

    Needs to be passed a brightway ``calculation_setup`` name.

    This class does not subclass the `LCA` class, and performs all
    calculations upon instantiation.

    Initialization creates `self.lca_scores`, which is a NumPy array
    of LCA scores, with rows of functional units and columns of LCIA methods.
    Ordering is the same as in the `calculation_setup`.

    Class adapted from bw2calc.multi_lca.MultiLCA to include also
    CONTRIBUTION ANALYSIS.

    Parameters
    ----------
    cs_name : str
        Name of the calculation setup

    Attributes
    ----------
    func_units_dict
    all_databases
    lca_scores_normalized

    Raises
    ------
    ValueError
        If the given `cs_name` cannot be found in brightway calculation_setups

    """
    def __init__(self, cs_name):
        try:
            cs = bw.calculation_setups[cs_name]
        except KeyError:
            raise ValueError(
                "{} is not a known `calculation_setup`.".format(cs_name)
            )
        # Functional units and related indexes
        self.func_units = cs['inv']
        self.fu_activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.fu_index = {k: i for i, k in enumerate(self.fu_activity_keys)}
        self.rev_fu_index = {v: k for k, v in self.fu_index.items()}

        # Methods and related indexes
        self.methods = cs['ia']
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {v: k for k, v in self.method_index.items()}

        # initial LCA and prepare method matrices
        self.lca = bw.LCA(demand=self.func_units_dict, method=self.methods[0])
        self.lca.lci(factorize=True)
        self.method_matrices = []
        for method in self.methods:
            self.lca.switch_method(method)
            self.method_matrices.append(self.lca.characterization_matrix)

        self.lca_scores = np.zeros((len(self.func_units), len(self.methods)))

        # data to be stored
        (self.rev_activity_dict, self.rev_product_dict, self.rev_biosphere_dict) = self.lca.reverse_dict()

        # Scaling
        self.scaling_factors = dict()

        # Technosphere product flows for a given functional unit
        self.technosphere_flows = dict()
        # Life cycle inventory (biosphere flows) by functional unit
        self.inventory = dict()
        # Inventory (biosphere flows) by activity (e.g. 2000x15000) and functional unit.
        self.inventories = dict()
        # Inventory multiplied by scaling (relative impact on environment) per impact category.
        self.characterized_inventories = dict()

        # Summarized contributions for EF and processes.
        self.elementary_flow_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.biosphere_matrix.shape[0]))
        self.process_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.technosphere_matrix.shape[0]))

        for row, func_unit in enumerate(self.func_units):
            # Do the LCA for the current functional unit
            self.lca.redo_lci(func_unit)

            # Now update the:
            # - Scaling factors
            # - Technosphere flows
            # - Life cycle inventory
            # - Life-cycle inventory (disaggregated by contributing process)
            # for current functional unit
            self.scaling_factors.update({
                str(func_unit): self.lca.supply_array
            })
            self.technosphere_flows.update({
                str(func_unit): np.multiply(self.lca.supply_array, self.lca.technosphere_matrix.diagonal())
            })
            self.inventory.update({
                str(func_unit): np.array(self.lca.inventory.sum(axis=1)).ravel()
            })
            self.inventories.update({
                str(func_unit): self.lca.inventory
            })

            # Now, for each method, take the current functional unit and do inventory analysis
            for col, cf_matrix in enumerate(self.method_matrices):
                self.lca.characterization_matrix = cf_matrix
                self.lca.lcia_calculation()
                self.lca_scores[row, col] = self.lca.score
                self.characterized_inventories[row, col] = self.lca.characterized_inventory.copy()
                self.elementary_flow_contributions[row, col] = np.array(
                    self.lca.characterized_inventory.sum(axis=1)).ravel()
                self.process_contributions[row, col] = self.lca.characterized_inventory.sum(axis=0)

        # TODO: get rid of the below
        self.func_unit_translation_dict = {
            str(bw.get_activity(list(func_unit.keys())[0])): func_unit for func_unit in self.func_units
        }
        self.func_key_dict = {m: i for i, m in enumerate(self.func_unit_translation_dict.keys())}
        self.func_key_list = list(self.func_key_dict.keys())

    @property
    def func_units_dict(self):
        """Return a dictionary of functional units (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    @property
    def all_databases(self):
        """Get all databases linked to the functional units."""
        databases = list()
        for f in self.fu_activity_keys:
            databases.append(f[0])
            databases.extend(bw.databases[f[0]].get('depends', []))
        return set(databases)

    @property
    def lca_scores_normalized(self):
        """Normalize LCA scores by impact assessment method.
        """
        return self.lca_scores / self.lca_scores.max(axis=0)

    def get_all_metadata(self):
        """Populate AB_metadata with relevant database values.

        Set metadata in form of a Pandas DataFrame for biosphere and
        technosphere databases for tables and additional aggregation.
        """
        AB_metadata.add_metadata(self.all_databases)
        # print('Making metadata DataFrame.')
        # dfs = []
        # for db in self.all_databases:
        #     df_temp = pd.DataFrame(bw.Database(db))
        #     df_temp.index = pd.MultiIndex.from_tuples(zip(df_temp['database'], df_temp['code']))
        #     dfs.append(df_temp)
        # self.df_meta = pd.concat(dfs, sort=False)


class Contributions(object):
    """Contribution Analysis built on top of the Multi-LCA class.

    This class requires instantiated MLCA and MetaDataFrame objects.

    Parameters
    ----------
    mlca : `MLCA`
        An instantiated MLCA object

    Attributes
    ----------
    DEFAULT_ACT_FIELDS : list
        Default activity/functional unit column names
    DEFAULT_EF_FIELDS : list
        Default environmental flow column names

    Raises
    ------
    ValueError
        If the given `mlca` object is not an instance of `MLCA`

    """

    DEFAULT_ACT_FIELDS = ['reference product', 'name', 'location', 'unit', 'database']
    DEFAULT_EF_FIELDS = ['name', 'categories', 'type', 'unit', 'database']

    def __init__(self, mlca):
        if not isinstance(mlca, MLCA):
            raise ValueError('Must pass an MLCA object. Passed:', type(mlca))
        self.mlca = mlca
        # Ensure MetaDataFrame is updated.
        self.mlca.get_all_metadata()

        # Set default metadata keys (those not in the dataframe will be eliminated)
        self.act_fields = AB_metadata.get_existing_fields(self.DEFAULT_ACT_FIELDS)
        self.ef_fields = AB_metadata.get_existing_fields(self.DEFAULT_EF_FIELDS)

    def normalize(self, contribution_array):
        """Normalise the contribution array.

        Parameters
        ----------
        contribution_array : `numpy.ndarray`
            A 2-dimensional contribution array

        Returns
        -------
        `numpy.ndarray`
            2-dimensional array of same shape, with scores normalized.

        """
        scores = contribution_array.sum(axis=1)
        return (contribution_array / scores[:, np.newaxis])

    def _build_dict(self, C, FU_M_index, rev_dict, limit, limit_type):
        """Sort the given contribution array on method or functional unit column.

        Parameters
        ----------
        C : `numpy.ndarray`
            A 2-dimensional contribution array
        FU_M_index : dict
            Dictionary which maps the functional units or methods to their
            matching columns
        rev_dict : dict
            'reverse' dictionary used to map correct activity/method to
            its value
        limit : int
            Number of top-contributing items to include
        limit_type : str
            Either "number" or "percent", ContributionAnalysis.sort_array
            for complete explanation

        Returns
        -------
        dict
            Top-contributing flows per method or activity

        """
        topcontribution_dict = dict()
        for fu_or_method, col in FU_M_index.items():
            top_contribution = ca.sort_array(C[col, :], limit=limit, limit_type=limit_type)
            cont_per = dict()
            cont_per.update({
                ('Total', ''): C[col, :].sum(),
                ('Rest', ''): C[col, :].sum() - top_contribution[:, 0].sum(),
                })
            for value, index in top_contribution:
                cont_per.update({rev_dict[index]: value})
            topcontribution_dict.update({fu_or_method: cont_per})
        return topcontribution_dict

    def get_labels(self, key_list, fields=['name', 'reference product', 'location', 'database'],
                   separator=' | ', max_length=False):
        """Generate labels from metadata information.

        Setting max_length will wrap the label into a multi-line string if
        size is larger than max_length.

        Parameters
        ----------
        key_list : `pandas.MultiIndex`
            An index containing 'keys' to be retrieved from the MetaDataFrame
        fields : list
            List of column-names to be included from the MetaDataFrame
        separator : str
            Specific separator to use when joining strings together
        max_length : int
            Allowed character length before string is wrapped over multiple
            lines

        Returns
        -------
        list
            Translated and/or joined (and wrapped) labels matching the keys

        """
        keys = [k for k in key_list]  # need to do this as the keys come from a pd.Multiindex
        translated_keys = []
        for k in keys:
            if k in AB_metadata.index:
                translated_keys.append(separator.join([str(l) for l in list(AB_metadata.get_metadata(k, fields))]))
            else:
                translated_keys.append(separator.join([i for i in k if i != '']))
        if max_length:
            translated_keys = [wrap_text(k, max_length=max_length) for k in translated_keys]
        return translated_keys

    def join_df_with_metadata(self, df, x_fields=None, y_fields=None, special_keys=None):
        """Join a dataframe that has keys on the index with metadata.

        Metadata fields are defined in x_fields.
        If columns are also keys (and not, e.g. method names), they can also
        be replaced with metadata, if y_fields are provided.

        Parameters
        ----------
        df : `pandas.DataFrame`
            Simple DataFrame containing processed data
        x_fields : list
            List of additional columns to add from the MetaDataFrame
        y_fields : list
            List of column keys for the data in the df dataframe
        special_keys : list
            List of specific items to place at the top of the dataframe

        Returns
        -------
        `pandas.DataFrame`
            Expanded and metadata-annotated dataframe

        """

        # replace column keys with labels
        df.columns = self.get_labels(df.columns, fields=y_fields)#, separator='\n')

        # get metadata for rows
        keys = [k for k in df.index if k in AB_metadata.index]
        metadata = AB_metadata.get_metadata(keys, x_fields)

        # join data with metadata
        joined = metadata.join(df, how='outer')

        if special_keys:
            # replace index keys with labels
            try:  # first put Total and Rest to the first two positions in the dataframe
                index_for_Rest_Total = special_keys + keys
                joined = joined.loc[index_for_Rest_Total]
            except:
                print('Could not put Total and Rest on positions 0 and 1 in the dataframe.')
        joined.index = self.get_labels(joined.index, fields=x_fields)
        return joined

    def get_labelled_contribution_dict(self, cont_dict, x_fields=None, y_fields=None):
        """Annotate the contribution dict with metadata.
        """
        df = pd.DataFrame(cont_dict)
        joined = self.join_df_with_metadata(
            df, x_fields=x_fields, y_fields=y_fields, special_keys=[('Total', ''), ('Rest', '')]
        )
        return joined.reset_index(drop=False)

    def inventory_df(self, inventory_type='biosphere'):
        """Returns an inventory dataframe with metadata of the given type.
        """
        if inventory_type == 'biosphere':
            df = pd.DataFrame(self.mlca.inventory)
            df.index = pd.MultiIndex.from_tuples(self.mlca.rev_biosphere_dict.values())
            df.columns = self.get_labels(self.mlca.fu_activity_keys, max_length=30)
            metadata = AB_metadata.get_metadata(list(self.mlca.rev_biosphere_dict.values()), self.ef_fields)
        elif inventory_type == 'technosphere':
            df = pd.DataFrame(self.mlca.technosphere_flows)
            df.index = pd.MultiIndex.from_tuples(self.mlca.rev_activity_dict.values())
            df.columns = self.get_labels(self.mlca.fu_activity_keys, max_length=30)
            metadata = AB_metadata.get_metadata(list(self.mlca.rev_activity_dict.values()), self.act_fields)
        else:
            raise ValueError(
                "Type must be either 'biosphere' or 'technosphere', " + \
                    "'{}' given.".format(inventory_type)
            )

        joined = metadata.join(df)
        joined.reset_index(inplace=True, drop=True)
        return joined

    def lca_scores_df(self, normalized=False):
        """Returns a metadata-annotated DataFrame of the LCA scores.
        """
        scores = self.mlca.lca_scores if not normalized else self.mlca.lca_scores_normalized
        df = pd.DataFrame(
            scores,
            index=pd.MultiIndex.from_tuples(self.mlca.fu_activity_keys),
            columns=self.mlca.methods
        )
        joined = self.join_df_with_metadata(df, x_fields=self.act_fields, y_fields=None)
        return joined.reset_index(drop=False)

    def top_elementary_flow_contributions(self, functional_unit=None, method=None,
                                          limit=5, normalize=False, limit_type="number"):
        """Return top EF contributions for either functional_unit or method.

        * If functional_unit: Compare the unit against all considered impact
        assessment methods.
        * If method: Compare the method against all involved processes.

        Parameters
        ----------
        functional_unit : tuple, optional
            The functional unit to compare all considered methods against
        method : tuple, optional
            The method to compare all considered functional units against
        limit : int
            The number of top contributions to consider
        normalize : bool
            Determines whether or not to normalize the contribution values
        limit_type : str
            The type of limit, either 'number' or 'percent'


        Returns
        -------
        `pandas.DataFrame`
            Annotated top-contribution dataframe

        """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError(
                "It must be either by functional unit or by method. Provided:" + \
                    "\n Functional unit: {} \n Method: {}".format(functional_unit, method)
            )

        if method:
            C = self.mlca.elementary_flow_contributions[:, self.mlca.method_index[method], :]
        elif functional_unit:
            C = self.mlca.elementary_flow_contributions[self.mlca.func_key_dict[functional_unit], :, :]

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        if method:
            top_cont_dict = self._build_dict(
                C, self.mlca.fu_index, self.mlca.rev_biosphere_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(
                top_cont_dict, x_fields=self.ef_fields, y_fields=self.act_fields)
        elif functional_unit:
            top_cont_dict = self._build_dict(
                C, self.mlca.method_index, self.mlca.rev_biosphere_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(
                top_cont_dict, x_fields=self.ef_fields, y_fields=None)

    def top_process_contributions(self, functional_unit=None, method=None, limit=5,
                                  normalize=False, limit_type="number"):
        """Return top process contributions for functional_unit or method

        * If functional_unit: Compare the process against all considered impact
        assessment methods.
        * If method: Compare the method against all involved processes.

        Parameters
        ----------
        functional_unit : tuple, optional
            The functional unit to compare all considered methods against
        method : tuple, optional
            The method to compare all considered functional units against
        limit : int
            The number of top contributions to consider
        normalize : bool
            Determines whether or not to normalize the contribution values
        limit_type : str
            The type of limit, either 'number' or 'percent'

        Returns
        -------
        `pandas.DataFrame`
            Annotated top-contribution dataframe

        """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError(
                "It must be either by functional unit or by method. Provided:" + \
                    "\n Functional unit: {} \n Method: {}".format(functional_unit, method)
            )

        if method:
            C = self.mlca.process_contributions[:, self.mlca.method_index[method], :]
        elif functional_unit:
            C = self.mlca.process_contributions[self.mlca.func_key_dict[functional_unit], :, :]

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        if method:
            top_cont_dict = self._build_dict(
                C, self.mlca.fu_index, self.mlca.rev_activity_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(
                top_cont_dict, x_fields=self.act_fields, y_fields=self.act_fields)
        elif functional_unit:
            top_cont_dict = self._build_dict(
                C, self.mlca.method_index, self.mlca.rev_activity_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(
                top_cont_dict, x_fields=self.act_fields, y_fields=None)
