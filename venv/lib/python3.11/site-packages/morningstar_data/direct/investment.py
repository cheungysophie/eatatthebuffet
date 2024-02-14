from operator import inv
import warnings
from pandas import DataFrame
from typing import Optional, List, Dict, Any, Union
from . import _decorator
from .._base import _logger
from ._data_objects import Investments, InvestmentType, DataPoints, DataPointsType
from .data_type import TimeSeriesFormat
from ._investment._asset_flow_data import AssetFlowProvider
from ._investment._normal_data import NormalDataProvider
from ._investment._common import _get_data_points, _get_data_point_col_names

from .._utils import _get_user_cells_quota, _get_data_points_total_columns
from ._data_type import DryRunResults


@_decorator.typechecked
def investment_data(
    investments: Union[List[str], str, Dict[str, Any]],
    datapoints: Union[List[Dict[str, Any]], str, DataFrame],
) -> DataFrame:
    warnings.warn(
        "The investment_data function is deprecated and will be removed in the next major version. Use get_investment_data instead",
        FutureWarning,
        stacklevel=2,
    )
    return _get_investment_data(investments, datapoints, time_series_format=TimeSeriesFormat.WIDE)


# FIXME: In https://msjira.morningstar.com/browse/AL2-92, the error_handler decorator was removed from some methods
# to trigger QueryLimitException.
# There are multiple methods where the decorator was removed to trigger certain exceptions back to the caller:
#   - save_investment_list
#   - investment_data
#   - holding_dates
#   - asset_flow
# For the time being, we will leave this as-is to keep things working. Moving forward, we must re-design the
# exception handling so that we don't have these types of special cases where error_handler is only allowed on some
# methods but not others.
@_decorator.typechecked
def get_investment_data(
    investments: Union[List[str], str, Dict[str, Any]],
    data_points: Optional[Union[List[Dict[str, Any]], str, DataFrame, List[Any]]] = None,
    display_name: bool = False,
    dry_run: Optional[bool] = False,
    time_series_format: TimeSeriesFormat = TimeSeriesFormat.WIDE,
) -> Union[DataFrame, DryRunResults]:
    """Retrieve data for the specified investments and data points.

    Args:
        investments (:obj:`Union`, `required`): Defines the investments to fetch. Input can be:

            * Investment IDs (:obj:`list`, `optional`): Investment identifiers, in the format of SecId;Universe or just SecId. E.g., ["F00000YOOK;FO","FOUSA00CFV;FO"] or ["F00000YOOK","FOUSA00CFV"]. Use the `investments <./lookup.html#morningstar_data.direct.investments>`_ function to discover identifiers.
            * Investment List ID (:obj:`str`, `optional`): Saved investment list in Morningstar Direct. Currently, this function does not support lists that combine investments and user-created portfolios. Use the `get_investment_lists <./lists.html#morningstar_data.direct.user_items.get_investment_lists>`_ function to discover saved lists.
            * Search Criteria  ID (:obj:`str`, `optional`): Saved search criteria in Morningstar Direct. Use the `get_search_criteria <./search_criteria.html#morningstar_data.direct.user_items.get_search_criteria>`_ function to discover saved search criteria.
            * Search Criteria Condition (:obj:`dict`, `optional`): Search criteria definition. See details in the Reference section below or use the `get_search_criteria_conditions <./search_criteria.html#morningstar_data.direct.user_items.get_search_criteria_conditions>`_ function to discover the definition of a saved search criteria.

        data_points (:obj:`Union`, `optional`): Defines the data points to fetch. If not provided and investments are specified with a list ID or search criteria ID, the corresponding bound dataset will be used.

            * Data Point IDs (:obj:`List[Dict]`, `optional`): A list of dictionaries, each defining a data point and its (optional) associated settings.
            * Data Set ID (:obj:`str`, `optional`): Morningstar data set or user-created data set saved in Morningstar Direct. Use the `get_data_sets <./data_set.html#morningstar_data.direct.user_items.get_data_sets>`_ or `get_morningstar_data_sets <./data_set.html#morningstar_data.direct.get_morningstar_data_sets>`_ functions to discover saved data sets.
            * Data Point Settings (:obj:`DataFrame`, `optional`): A DataFrame of data point identifiers and their associated settings. Use the `get_data_set_details <./data_set.html#morningstar_data.direct.user_items.get_data_set_details>`_ function to discover data point settings from a saved data set.

        display_name (:obj:`bool`, `optional`): When true, the returned column names will match display names saved in the data set. Default is false.
        time_series_format (:obj:`md.direct.data_type.TimeSeriesFormat`, `optional`):Default is Wide. Enumeration of md.direct.data_type.TimeSeriesFormat, which can be 'Wide', 'Long', 'LongWithoutName'. E.g., ``md.direct.data_type.TimeSeriesFormat.Long``

        dry_run(:obj:`bool`, `optional`): When True, the query will not be executed. Instead, a DryRunResults object will be returned with details about the query's impact on daily cell limit usage.

    :Returns:

        There are two return types:

        * DataFrame: A DataFrame object with investment data

        * DryRunResults: Is returned if dry_run=True is passed

          * estimated_cells_used: Number of cells by this query
          * daily_cells_remaining_before: How many cells are remaining in your daily cell limit before running this query
          * daily_cells_remaining_after: How many cells would be remaining in your daily cell limit after running this query
          * daily_cell_limit: Your total daily cell limit

    :Reference:

        Constructing a Search Criteria Condition dictionary:

        For example::

                    SEARCH_CRITERIA_CONDITION = {
                            "universeId": "cz",
                            "subUniverseId": "",
                            "subUniverseName": "",
                            "securityStatus": "activeonly",
                            "useDefinedPrimary": False,
                            "criteria": [
                                {"relation": "", "field": "HU338", "operator": "=", "value": "1"},
                                {"relation": "AND", "field": "HU863", "operator": "=", "value": "1"}
                            ]
                        }

        * universeId (:obj:`string`, `required`): Universe code (e.g., "FO"). Use the `get_investment_universes <./lookup.html#morningstar_data.direct.lookup.get_investment_universes>`_ function to explore available values or `download <../_static/assets/SearchCriteriaInfo.xlsx>`_ the reference file.
        * subUniverseId (:obj:`string`, `optional`): Sub-universe code, if applicable. See the refererece file above for available values.
        * subUniverseName (:obj:`string`, `optional`): Name of sub-universe, if applicable. See the refererece file above for available values.
        * securityStatus (:obj:`string`, `optional`): Security status, can be 'activeonly' or 'activeinactive'.
        * useDefinedPrimary (:obj:`Boolean`, `optional`): If set to true, Morningstar Direct user-defined settings will be used.
        * criteria (:obj:`List[Dict[]]`, `required`): Custom search conditions. Dictionary fields described below.

        The 'criteria' object consists of the following fields:
            * field (:obj:`string`): Data point identifier
            * value (:obj:`string`): Value to compare against the data point.
            * criteria (:obj:`List[Dict[]]`): A nested list of additional custom search conditions.
            * relation (:obj:`string`, `required`): Boolean condition used when joining with the previous condition. Accepts an empty string (for the first condition, as no previous condition exists to join with), 'Or', or 'And'.
            * operator (:obj:`string`): Operator used to compare field value to value. Possible operators include '=', '!=', '<', '>', '<=', '>=', 'like' (data contains value), and 'not like' (data does not contain value).

            For example::

                [
                    {
                        "field": "eb919bcc-c097-4fe3-898c-470d8b89dde1"
                        "operator": "="
                        "relation": ""
                        "value": "122"
                    },
                    {
                        "criteria": [
                            {...Condition1 },
                            {...Condition2 },
                            {...Condition3 },
                        ],
                        "relation": "And"
                    },
                    {
                        "field": "LS466"
                        "operator": "="
                        "relation": "Or"
                        "value": "FH"
                    }
                ]

    :Examples:

    Get investment data for the given investments and data points.
    ::

        import morningstar_data as md

        df = md.direct.get_investment_data(
            investments=["F0AUS05U7H", "F000010NJ5"],
            data_points=[
                {"datapointId": "OS01W"}, # Name
                {"datapointId": "LS05M"}, # Base Currency
                {
                    "datapointId": "HP010", # Monthly Return
                    "isTsdp": True,
                    "currency": "CNY",
                    "startDate": "2021-03-01",
                    "endDate": "2021-08-31",
                },
            ],
        )
        df

    :Output:
        =================  ===================================  ================= =========================  =========================
        Id                 Name                                 Base Currency     Monthly Return 2021-03-31  Monthly Return 2021-04-30
        =================  ===================================  ================= =========================  =========================
        F0AUS05U7H         Walter Scott Global Equity           Australian Dollar                  3.726094                   3.078352
        F000010NJ5         Vontobel Emerging Markets Eq U1 USD  US Dollar                         -0.417526                  -0.376890
        =================  ===================================  ================= =========================  =========================


    Get investment data for a saved investment list and data points.

    ::

        import morningstar_data as md

        df = md.direct.get_investment_data(
            investments="a727113a-9557-4378-924f-5d2ba553f687", # Replace with a valid List ID
            data_points=[{"datapointId": "HS793", "isTsdp": True}],
        )
        df

    :Output:
        ==============  =================================  =============================  =============================  =============================
        Id              Name                               Daily Return Index 2021-09-23  Daily Return Index 2021-09-24  Daily Return Index 2021-09-25
        ==============  =================================  =============================  =============================  =============================
        FOUSA00DFS;FO   BlackRock Global Allocation Inv A  129.92672                      129.56781                      129.56781
        ==============  =================================  =============================  =============================  =============================

    Get investment data for a saved search criteria and data points

    ::

        import morningstar_data as md

        df = md.direct.get_investment_data(
            investments="4216254", # Replace with a valid Search Criteria ID
            data_points=[{"datapointId": "12", "isTsdp": True}]
        )
        df

    :Output:
        ==============  =======================  =============================
        Id              Name                     Beta 2018-10-01 to 2021-09-30
        ==============  =======================  =============================
        FOUSA06JNH;FO   DWS RREEF Real Assets A    0.654343
        ==============  =======================  =============================

    Get investment data for a custom search criteria and data points.

    ::

        import morningstar_data as md

        SEARCH_CRITERIA_CONDITION = {
            "universeId": "cz",
            "subUniverseId": "",
            "subUniverseName": "",
            "securityStatus": "activeonly",
            "useDefinedPrimary": False,
            "criteria": [
                {"relation": "", "field": "HU338", "operator": "=", "value": "1"},
                {"relation": "AND", "field": "HU863", "operator": "=", "value": "1"},
            ],
        }

        df = md.direct.get_investment_data(
            investments=SEARCH_CRITERIA_CONDITION,
            data_points=[{"datapointId": "HS793", "isTsdp": True}],
        )
        df

    :Output:
        =  ===============  =====================================  =============================  ===  =============================
        #  Id               Name                                   Daily Return Index 2022-02-18  ...  Daily Return Index 2022-03-17
        =  ===============  =====================================  =============================  ===  =============================
        0  FOUSA06UOR;CZ    Columbia Trust Stable Government Fund  None                           ...  None
        1  FOUSA06UWL;CZ    Columbia Trust Stable Income Fund      88.8333                        ...  90.7781
        =  ===============  =====================================  =============================  ===  =============================

    Get investment data for the given investments and data points with md.direct.data_type.TimeSeriesFormat.long.
    ::

        import morningstar_data as md

        df = md.direct.get_investment_data(
            investments=["F0AUS05U7H", "F000010NJ5"],
            data_points=[
                {"datapointId": "OS01W"}, # Name
                {"datapointId": "LS05M"}, # Base Currency
                {
                    "datapointId": "HP010", # Monthly Return
                    "isTsdp": True,
                    "currency": "CNY",
                    "startDate": "2021-03-01",
                    "endDate": "2021-08-31",
                },
            ],
            time_series_format=md.direct.data_type.TimeSeriesFormat.Long
        )
        df

    :Output:
        =================  ===================================  ================= =========================  =========================
        Id                 Name                                 Base Currency     Date                       Monthly Return
        =================  ===================================  ================= =========================  =========================
        F0AUS05U7H         Walter Scott Global Equity           Australian Dollar                2021-04-30                   3.726094
        F0AUS05U7H         Walter Scott Global Equity           Australian Dollar                2021-05-31                   3.078352
        F0AUS05U7H         Walter Scott Global Equity           Australian Dollar                2021-06-30                   3.078352
        F000010NJ5         Vontobel Emerging Markets Eq U1 USD  US Dollar                        2021-04-30                  -0.417526
        F000010NJ5         Vontobel Emerging Markets Eq U1 USD  US Dollar                        2021-05-31                  -0.376890
        F000010NJ5         Vontobel Emerging Markets Eq U1 USD  US Dollar                        2021-06-30                  3.078352
        =================  ===================================  ================= =========================  =========================


    """

    result = _get_investment_data(investments=investments, data_points=data_points, display_name=display_name, time_series_format=time_series_format, dry_run=dry_run)
    return result


def _get_investment_data(
    investments: InvestmentType, data_points: DataPointsType, time_series_format: TimeSeriesFormat, display_name: bool = False, dry_run: Optional[bool] = False
) -> Union[DataFrame, DryRunResults]:
    investment_param = Investments(investments)
    data_point_param = DataPoints(data_points)

    if dry_run:
        investment_id_list = investment_param.get_investment_ids()
        data_point_settings = data_point_param.get_data_points()
        data_point_settings = data_point_settings.where(data_point_settings.notnull(), None)
        data_point_list = data_point_settings.to_dict(orient="records")
        estimated_cells_used = _get_data_points_total_columns(data_point_list) * len(investment_id_list)
        user_cells_quota = _get_user_cells_quota()
        dry_run_results = DryRunResults(
            estimated_cells_used=estimated_cells_used, daily_cells_remaining_before=user_cells_quota["daily_cell_remaining"], daily_cell_limit=user_cells_quota["daily_cell_limit"]
        )
        return dry_run_results

    # Get asset flow data
    asset_flow_req = AssetFlowProvider.build_request(investment_param, data_point_param, display_name)
    asset_flow_result = AssetFlowProvider.run_request(asset_flow_req)

    # Get normal data
    normal_data_req = NormalDataProvider.build_request(investment_param, data_point_param, display_name)
    normal_data_result = NormalDataProvider.run_request(normal_data_req)

    # Combine data
    merged_result = asset_flow_result.merge_with(normal_data_result)

    # Build data frame, re-order columns
    data_points = _get_data_points(investment_param, data_point_param)
    data_point_cols = _get_data_point_col_names(data_points, merged_result.get_data_point_alias_to_col_dict())

    return merged_result.as_data_frame(order_cols_by=data_point_cols, time_series_format=time_series_format)
