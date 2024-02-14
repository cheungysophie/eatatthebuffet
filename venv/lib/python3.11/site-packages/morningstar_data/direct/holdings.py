import simplejson as json
import os
import time
import uuid
import warnings
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from urllib.request import urlopen

import pandas as pd
from pandas import DataFrame


from .. import datalake
from .._base import _logger
from . import _decorator, _utils
from . import investment as inv
from . import portfolio
from ._base_api import APIBackend
from ._config import _Config
from ._config_key import FORMAT_DATE
from ._error_messages import (
    BAD_REQUEST_ERROR_INCLUDE_ALL_DATE,
    BAD_REQUEST_ERROR_NO_START_DATE,
    BAD_REQUEST_ERROR_INVALID_INVESTMENT_ID,
    BAD_REQUEST_ERROR_NO_INVESTMENT_IDS,
    BAD_REQUEST_ERROR_NO_PORTFOLIO_DATA,
    BAD_REQUEST_ERROR_NO_START_DATE,
    BAD_REQUEST_ERROR_INVALID_LOOKTHROUGH_HOLDING_TYPE,
    BAD_REQUEST_ERROR_INVALID_PORTFOLIO_ID,
)
from ._exceptions import BadRequestException, ValueErrorException
from ._backend_apis._holdings_backend import HoldingAPIBackend, FoFAPIBackend, AMSAPIBackend
from ._data_objects import Investments

_config = _Config()

_holding_api_request = HoldingAPIBackend()
_fof_api_request = FoFAPIBackend()
_ams_api_request = AMSAPIBackend()

MASTER_PORTFOLIO_ID = "MasterPortfolio Id"


@_decorator.typechecked
def holdings(
    investment_ids: List[str],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> DataFrame:
    warnings.warn(
        "The holdings function is deprecated and will be removed in the next major version. Use get_holdings instead",
        FutureWarning,
        stacklevel=2,
    )
    return get_holdings(investment_ids, date, start_date, end_date)


@_decorator.typechecked
def get_holdings(
    investments: Optional[Union[List[str], str, Dict[str, Any]]] = None,  # Make it required once investment_ids get removed,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    investment_ids: Optional[List[str]] = None,
) -> DataFrame:
    """Returns holdings for the specified investments and date or date range. If the date is not specified, the function uses the latest portfolio date by default.

    Args:
        investments (:obj:`Union`, `required`): Defines the investments to fetch. Input can be:

                * Investment IDs (:obj:`list`, `optional`): Investment identifiers, in the format of SecId;Universe or just SecId. E.g., ["F00000YOOK;FO","FOUSA00CFV;FO"] or ["F00000YOOK","FOUSA00CFV"]. Use the `investments <./lookup.html#morningstar_data.direct.investments>`_ function to discover identifiers.
                * Investment List ID (:obj:`str`, `optional`): Saved investment list in Morningstar Direct. Currently, this function does not support lists that combine investments and user-created portfolios. Use the `get_investment_lists <./lists.html#morningstar_data.direct.user_items.get_investment_lists>`_ function to discover saved lists.
                * Search Criteria  ID (:obj:`str`, `optional`): Saved search criteria in Morningstar Direct. Use the `get_search_criteria <./search_criteria.html#morningstar_data.direct.user_items.get_search_criteria>`_ function to discover saved search criteria.
                * Search Criteria Condition (:obj:`dict`, `optional`): Search criteria definition. See details in the Reference section below or use the `get_search_criteria_conditions <./search_criteria.html#morningstar_data.direct.user_items.get_search_criteria_conditions>`_ function to discover the definition of a saved search criteria.

        date (:obj:`str`, `optional`): The portfolio date for which to retrieve data. The format is YYYY-MM-DD.
            For example, "2020-01-01". If a date is provided, then the `start_date` and `end_date` parameters are ignored.
            An exception is thrown if `start_date` or `end_date` is provided along with `date`.
        start_date (:obj:`str`, `optional`): The start date for retrieving data. The format is
            YYYY-MM-DD. For example, "2020-01-01". An exception is thrown if `date` is provided along with `start_date`.
        end_date (:obj:`str`, `optional`): The end date for retrieving data. If no value is provided for
            `end_date`, current date will be used. The format is YYYY-MM-DD. For example, "2020-01-01". An exception is
            thrown if `date` is provided along with `end_date`.
        investment_ids (:obj:`list`): DEPRECATED, A list of investment IDs. The investment ID format is SecId;Universe or just SecId.
            For example: ["F00000YOOK;FO","FOUSA00CFV;FO"] or ["F00000YOOK","FOUSA00CFV"].

    Returns:
        DataFrame: A DataFrame object with holdings data. DataFrame columns include:

        * investmentId
        * masterPortfolioId
        * portfolioDate
        * holdingId
        * bondId
        * name
        * secId
        * isin
        * cusip
        * weight
        * shares
        * marketValue
        * sharesChanged
        * currency
        * ticker
        * detailHoldingType

    Raises:
        ValueErrorException: Raised when the `investments` parameter is invalid.

    Examples:
        Retrieve holdings for investment "FOUSA00KZH" on "2020-12-31".

    ::

        import morningstar_data as md

        df = md.direct.get_holdings(investments=["FOUSA00KZH"], date="2020-12-31")
        df

    :Output:
        =============  =================  ===  ======  =================
        investmentId   masterPortfolioId  ...  ticker  detailHoldingType
        =============  =================  ===  ======  =================
        FOUSA00KZH     6079               ...  CBRE    EQUITY
        FOUSA00KZH     6079               ...  GOOGL   EQUITY
        ...
        =============  =================  ===  ======  =================

    """
    if investment_ids is not None:
        warnings.warn(
            "The investment_ids argument is deprecated and will be removed in the next major version. Use investments instead",
            FutureWarning,
            stacklevel=2,
        )

    if not investment_ids and not investments:
        raise BadRequestException(BAD_REQUEST_ERROR_NO_INVESTMENT_IDS) from None

    investment_param = Investments(investments or investment_ids)
    investment_id_list = investment_param.get_investment_ids()

    if [x for x in investment_id_list if len(x.split(";")[0]) != 10]:
        raise BadRequestException(BAD_REQUEST_ERROR_INVALID_INVESTMENT_ID) from None

    _validate_date(date, start_date, end_date)

    investment_date_info = _get_dates(investment_id_list, date, start_date, end_date)
    params = []
    master_portfolio_id_investment_id_dict = defaultdict(list)
    for sec_id, date_info in investment_date_info.items():
        if date_info not in params:
            params.append(date_info)
        master_portfolio_id_investment_id_dict[date_info.get("masterPortfolioId", "")].append(sec_id)

    url = f"{_config.securitydata_service_url()}v1/securities/holdings"
    response_json = _holding_api_request.do_post_request(url, json.dumps(params, ignore_nan=True))
    if not isinstance(response_json, list) or not response_json:
        return DataFrame()
    details = []
    for holdings_info in response_json:
        master_portfolio_id = holdings_info.get("masterPortfolioId", "")
        holdings_date_info = holdings_info.get("holdings", dict())
        for single_date, holdings in holdings_date_info.items():
            for value in master_portfolio_id_investment_id_dict.get(master_portfolio_id, ""):
                details.extend(
                    [
                        {
                            "portfolioDate": single_date,
                            "investmentId": value,
                            "masterPortfolioId": master_portfolio_id,
                            "holdingId": x.get("id", ""),
                            "bondId": x.get("bondId", ""),
                            "name": x.get("name", ""),
                            "secId": x.get("secId", ""),
                            "isin": x.get("isin", ""),
                            "cusip": x.get("cusip", ""),
                            "weight": x.get("weight", ""),
                            "shares": x.get("shares", ""),
                            "marketValue": x.get("marketValue", ""),
                            "sharesChanged": x.get("sharesChanged", ""),
                            "currency": x.get("currency", ""),
                            "ticker": x.get("ticker", ""),
                            "detailHoldingType": x.get("detailHoldingType", ""),
                        }
                        for x in holdings
                    ]
                )
    return DataFrame(details)


def _get_dates_by_investments(investment_ids: list) -> List[Any]:
    ids = quote(",".join(investment_ids), "utf-8")
    url = f"{_config.securitydata_service_url()}v2/securities/{ids}/portfolio-dates"
    result: List[Any] = _holding_api_request.do_get_request(url)
    return result


@_decorator.typechecked
def holding_dates(investment_ids: List[str]) -> DataFrame:
    warnings.warn(
        "The holding_dates function is deprecated and will be removed in the next major version. Use get_holding_dates instead",
        FutureWarning,
        stacklevel=2,
    )
    return get_holding_dates(investment_ids)


@_decorator.typechecked
def get_holding_dates(investment_ids: List[str]) -> DataFrame:
    """Returns all dates with available holdings data for the given investment.

    Args:
        investment_ids (:obj:`list`): A list of investment IDs. The investment ID format is SecId;Universe or just SecId.
            For example: ["F00000YOOK;FO","FOUSA00CFV;FO"] or ["F00000YOOK","FOUSA00CFV"].

    Returns:
        DataFrame: A DataFrame object with portfolio date data. DataFrame columns include:

       * secId
       * masterPortfolioId
       * date
       * suppression
       * suppressionHoldingNumber

    Examples:
        Retrieve portfolio dates for investment "FOUSA00KZH".

    ::

        import morningstar_data as md

        df = md.direct.get_holding_dates(investment_ids=["FOUSA06JNH"])
        df

    :Output:
        ==========  =================  ==========  ===========  ========================
        secId       masterPortfolioId  date        suppression  suppressionHoldingNumber
        ==========  =================  ==========  ===========  ========================
        FOUSA06JNH  210311             2021-08-31  False        None
        FOUSA06JNH  210311             2021-07-31  False        None
        ...
        ==========  =================  ==========  ===========  ========================

    """
    if not investment_ids:
        raise BadRequestException(BAD_REQUEST_ERROR_NO_INVESTMENT_IDS) from None
    response_json = _get_dates_by_investments(investment_ids)
    if isinstance(response_json, list) and response_json:
        details = []
        for date_info in response_json:
            sec_id = date_info.get("secId", "")
            master_portfolio_id = date_info.get("masterPortfolioId", "")
            details.extend(
                [
                    {
                        "secId": sec_id,
                        "masterPortfolioId": master_portfolio_id,
                        "date": portfolio_date.get("date", ""),
                        "suppression": portfolio_date.get("suppression", False),
                        "suppressionHoldingNumber": portfolio_date.get("suppressionHoldingNumber", None),
                    }
                    for portfolio_date in date_info.get("portfolioDates", [])
                ]
            )
        return DataFrame(details)
    else:
        return DataFrame()


def _get_dates(
    investment_ids: list,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    dates_raw: Dict[str, Optional[str]] = {
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
    }
    dates: Dict[str, str] = {}

    for key, value in dates_raw.items():
        if value is not None and len(value.strip()) > 0:
            dates[key] = _utils._format_date(value)
        elif key == "end_date" and dates_raw["start_date"] is not None:
            dates[key] = _utils._format_date(time.strftime(FORMAT_DATE, time.localtime()))

    response_json = _get_dates_by_investments(investment_ids)
    if not isinstance(response_json, list) or not response_json:
        raise BadRequestException(BAD_REQUEST_ERROR_NO_PORTFOLIO_DATA) from None

    if not bool(dates):
        return _handle_no_date(response_json)
    elif "date" in dates:
        return _handle_single_date(response_json, **dates)

    return _handle_date_range(response_json, **dates)


def _validate_date(date: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> None:
    if date:
        if start_date or end_date:
            raise BadRequestException(BAD_REQUEST_ERROR_INCLUDE_ALL_DATE) from None
    else:
        if not start_date and end_date:
            raise BadRequestException(BAD_REQUEST_ERROR_NO_START_DATE) from None


def _handle_single_date(date_info_list: list, date: str) -> dict:
    investment_date_info = dict()
    for date_info in date_info_list:
        available_date = _get_available_date(date, date_info)
        if available_date is not None:
            master_portfolio_id = date_info.get("masterPortfolioId", "")
            investment_date_info[date_info.get("secId", "")] = {
                "masterPortfolioId": master_portfolio_id,
                "portfolioDates": [available_date],
            }
    return investment_date_info


def _get_available_date(date: str, date_info: dict = dict()) -> Optional[str]:
    date_objs = date_info.get("portfolioDates", [])
    available_date = None
    for date_obj in date_objs:
        if date_obj.get("date", "") == date:
            available_date = date
            break
        elif date_obj.get("date", "") < date and available_date is None:
            available_date = date_obj.get("date", "")
    return available_date


def _handle_no_date(date_info_list: list) -> dict:
    investment_date_info = dict()
    for date_info in date_info_list:
        portfolio_dates = date_info.get("portfolioDates", [])
        if portfolio_dates:
            date = next(
                (x.get("date", "") for x in portfolio_dates if x.get("date", "") is not None and len(x.get("date", "")) > 0),
                None,
            )
            if date is not None and len(date) > 0:
                master_portfolio_id = date_info.get("masterPortfolioId", "")
                investment_date_info[date_info.get("secId", "")] = {
                    "masterPortfolioId": master_portfolio_id,
                    "portfolioDates": [date],
                }
    return investment_date_info


def _handle_date_range(date_info_list: list, start_date: str, end_date: str) -> dict:
    investment_date_info = dict()
    for date_info in date_info_list:
        sec_id = date_info.get("secId", "")
        master_portfolio_id = date_info.get("masterPortfolioId", "")
        portfolio_dates = date_info.get("portfolioDates", [])
        date_list = []
        for portfolio_date in portfolio_dates:
            single_date = portfolio_date.get("date", "")
            if start_date <= single_date <= end_date:
                date_list.append(single_date)
        if date_list:
            investment_date_info[sec_id] = {
                "masterPortfolioId": master_portfolio_id,
                "portfolioDates": date_list,
            }
    return investment_date_info


def _get_ids_from_lake_house(df_lookthrough: pd.DataFrame) -> pd.DataFrame:
    sql = """SELECT distinct
            a.investment_id
            ,a.isin
            ,a.cusip
            ,a.weight
            ,a.marketValue as market_value
            ,a.security_name
            ,a.currency
            ,a.morningstar_instrument_type_code
            ,b.entity_id
            ,b.morningstar_entity_name
            ,b.performance_id as primary_performance_id
            FROM lookthrough_temp a
                left join platform__reference__prd.investment_lookup b
                    on a.investment_id=b.investment_id and b.is_primary = True
            where (b.is_primary = True or b.investment_id is null)
    """
    df = datalake.query(sql, temp_tables=[datalake.TempTable("lookthrough_temp", df_lookthrough)])
    return df


def _get_fof_secid_and_investment_types(df_top_level_holdings: pd.DataFrame) -> pd.DataFrame:
    # create DataFrame with Direct secId and Direct securityType
    # df_top_level_holdings_expanded = df_top_level_holdings["HoldingId"].str.split(";", expand=True).rename(columns={0: "secid", 1: "sectype"})
    df_top_level_holdings[["fof_secid", "fof_sectype"]] = df_top_level_holdings["HoldingId"].str.split(";", expand=True).rename(columns={0: "fof_secid", 1: "fof_sectype"})
    if MASTER_PORTFOLIO_ID in df_top_level_holdings.columns:
        df_top_level_holdings["masterPortfolioId"] = df_top_level_holdings[MASTER_PORTFOLIO_ID].astype("Int64")

    query_str = """with cte as (
        SELECT distinct --performance_id,
        case
            when left(investment_id,2) ='E0' and fund_id is null
                then performance_id
            when is_primary=False
                then performance_id
            else investment_id
        end as sec_id
        ,investment_id
        ,morningstar_investment_name
        ,case
            when morningstar_instrument_type_code is not null
                then morningstar_instrument_type_code
            when left(investment_id,2) in ('FE','FC','FO','FH','FM','FV','SC')
                then left(investment_id,2)
            when left(investment_id,2) = 'F0'
                then 'FO'
            when left(investment_id,2) ='SA'
                then 'FS'
            when left(investment_id,2) ='E0' and fund_id is null
                then 'E'
            when left(investment_id,2) ='E0' and fund_id is not null
                then 'FC'
            else null
        end as morningstar_instrument_type_code
        ,is_primary
        FROM platform__reference__prd.investment_lookup a
        where
        (
            performance_id is not null
            or
            morningstar_instrument_type_code in ('BC','12','BZ','BY','B','BT','NE','BH','IP','NE','NB','NC','BG','BD','ND')
        )
        and
            left(investment_id,2) not in ('XI','VA')
        and
        (
            a.performance_id in (select fof_secid from temp_top_level_holdings_expanded)
            or
            a.investment_id in (select fof_secid from temp_top_level_holdings_expanded)
        )
    )
    select
        a.weight as weighting,
        a.Name as securityName,
        b.investment_id as secId,
        coalesce(trim(b.morningstar_instrument_type_code), 'Q') as detailHoldingTypeId
    from
        temp_top_level_holdings_expanded a
        left join cte b
            on a.fof_secid=b.sec_id
    """

    return datalake.query(
        query_str=query_str,
        temp_tables=[
            datalake.TempTable(name="temp_top_level_holdings_expanded", df=df_top_level_holdings),
        ],
    )


def _get_lookthrough_holdings_from_fof_api(portfolio_id: str, df_top_level_holdings: DataFrame) -> DataFrame:

    from ._backend_apis._signed_url_backend import SignedUrlBackend

    _signed_url_request = SignedUrlBackend()

    # 'XI' represents an index, which is unsupported by FoF API
    if "XI" in df_top_level_holdings["SecurityType"].values:
        raise BadRequestException(BAD_REQUEST_ERROR_INVALID_LOOKTHROUGH_HOLDING_TYPE)

    _logger.info(
        "Fetching FOF comptabile secid and investment types from investments_lookup table in lakehouse along with required fields from top level holdings to pass to FOF API."
    )
    df_fof_sec_id_investment_types = _get_fof_secid_and_investment_types(df_top_level_holdings)

    _logger.info("Generating a unique id for each row in the top level holdings.")
    # Add a UUID as value for clientSecurityGuid for each holding

    df_fof_sec_id_investment_types = df_fof_sec_id_investment_types.rename(
        columns={
            "secid": "secId",
            "weighting": "weighting",
            "detailholdingtypeid": "detailHoldingTypeId",
            "securityname": "securityName",
        }
    )

    df_fof_sec_id_investment_types["clientSecurityGuid"] = [str(uuid.uuid4()) for _ in range(len(df_fof_sec_id_investment_types.index))]

    _logger.info("Extracting fof_secid, investment_type, weight and masterportfolio id into json to pass to FOF API")
    holdings_json = df_fof_sec_id_investment_types.to_json(orient="records")

    holdings_parsed = json.loads(holdings_json)  # This is sent to FOF API in the holdings field

    fof_post_url = f"{_config.fof_api_url()}portfolios/drilldown/{portfolio_id.split(';')[0]}/ALCustomerHoldings"
    payload = json.dumps(
        {
            "clientPortfolioGuid": str(uuid.uuid4()),
            "portfolioDate": str(datetime.now().strftime("%Y%m%d")),
            "currencyId": "USD",
            "holdings": holdings_parsed,  # The SQL query returns the columns in exactly the same format as required by FOF API
        }
    )

    _logger.info("Submitting request to FOF API to run lookthrough holdings.")
    _logger.debug(f"Sending request to {fof_post_url}")

    # MD proxy api will poll FOF API and return the signed url to download the lookthrough holdings
    signed_url = _fof_api_request.do_post_request(fof_post_url, payload)["jobId"]  # Returns reponse.content as string

    _logger.info("Submitting request to download lookthrough holdsings from signed url.")
    _logger.debug(f"Sending request to {signed_url}")
    look_through_holdings_reponse = _signed_url_request.do_get_request(signed_url)  # The reponse includes lookthrough holdings as json

    _logger.info("Got response from Signed url request")
    look_through_holdings_json = json.loads(look_through_holdings_reponse)
    holdings = look_through_holdings_json["holdings"]
    _logger.debug(f"Got {len(holdings)} lookthrough holdings.")

    df_look_through_holdings = pd.DataFrame(holdings)
    return df_look_through_holdings


def _has_ams_license_for_isin() -> bool:
    ams_get_url = f"{_config.al_proxy_api_url()}/v2/ams/api/user/entitlements"
    response = _ams_api_request.do_get_request(ams_get_url)

    data_groups = response["DataGroups"]
    for data_group in data_groups:
        if ((data_group["IdType"] == "UNIVERSEID" and data_group["DataGroupId"] == "ALL") or data_group["DataGroupId"] == "CUSIP") and data_group["Permission"] == 1:
            return True
    return False


# temporary function until this data is added to Lake House
def _morningstar_investment_type_id_name_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"morningstar_instrument_type_code": "0", "morningstar_instrument_type_name": "Muni Bond - Unspecified"},
            {"morningstar_instrument_type_code": "1", "morningstar_instrument_type_name": "Muni Bond - General Obligation"},
            {"morningstar_instrument_type_code": "12", "morningstar_instrument_type_name": "Muni Bond - Revenue"},
            {
                "morningstar_instrument_type_code": "13",
                "morningstar_instrument_type_name": "Muni Bond - Cash (Retired after Oct 2022)",
            },
            {"morningstar_instrument_type_code": "14", "morningstar_instrument_type_name": "Muni Bond - Double Barrelled"},
            {"morningstar_instrument_type_code": "AF", "morningstar_instrument_type_name": "Alternatives - Farm & Timber Land"},
            {"morningstar_instrument_type_code": "AI", "morningstar_instrument_type_name": "Alternatives - Infrastructure"},
            {
                "morningstar_instrument_type_code": "AM",
                "morningstar_instrument_type_name": "Alternatives - Master Investment Trust",
            },
            {"morningstar_instrument_type_code": "AP", "morningstar_instrument_type_name": "Alternatives - Private Equity"},
            {"morningstar_instrument_type_code": "AR", "morningstar_instrument_type_name": "Alternatives - Real Estate"},
            {"morningstar_instrument_type_code": "B", "morningstar_instrument_type_name": "Bond - Corporate Bond"},
            {"morningstar_instrument_type_code": "BB", "morningstar_instrument_type_name": "Bond - Short-term Corporate Bills"},
            {"morningstar_instrument_type_code": "BC", "morningstar_instrument_type_name": "Bond - Convertible"},
            {"morningstar_instrument_type_code": "BD", "morningstar_instrument_type_name": "Bond - Gov't Agency Debt"},
            {"morningstar_instrument_type_code": "BG", "morningstar_instrument_type_name": "Bond - Gov't Agency Pass-Thru"},
            {"morningstar_instrument_type_code": "BH", "morningstar_instrument_type_name": "Bond - Non-Agency Residential MBS"},
            {"morningstar_instrument_type_code": "BL", "morningstar_instrument_type_name": "Bond Index - Future"},
            {"morningstar_instrument_type_code": "BM", "morningstar_instrument_type_name": "Bond - Non-U.S. Gov't Agency MBS"},
            {
                "morningstar_instrument_type_code": "BO",
                "morningstar_instrument_type_name": "Bond Index - Option (Call) (Consolidation to FD after Oct 2022)",
            },
            {
                "morningstar_instrument_type_code": "BP",
                "morningstar_instrument_type_name": "Bond Index - Option (Put) (Consolidation to FD after Oct 2022)",
            },
            {"morningstar_instrument_type_code": "BQ", "morningstar_instrument_type_name": "Bond - Undefined"},
            {"morningstar_instrument_type_code": "BR", "morningstar_instrument_type_name": "Bond - Bank Loans"},
            {"morningstar_instrument_type_code": "BT", "morningstar_instrument_type_name": "Bond - Gov't/Treasury"},
            {"morningstar_instrument_type_code": "BU", "morningstar_instrument_type_name": "Bond - Units"},
            {"morningstar_instrument_type_code": "BW", "morningstar_instrument_type_name": "Bond - Warrants/Rights (Call)"},
            {"morningstar_instrument_type_code": "BX", "morningstar_instrument_type_name": "Bond - Warrants/Rights (Put)"},
            {"morningstar_instrument_type_code": "BY", "morningstar_instrument_type_name": "Bond - Asset Backed"},
            {"morningstar_instrument_type_code": "BZ", "morningstar_instrument_type_name": "Bond - Supranational"},
            {"morningstar_instrument_type_code": "C", "morningstar_instrument_type_name": "Cash"},
            {"morningstar_instrument_type_code": "CA", "morningstar_instrument_type_name": "Cash - Collateral"},
            {
                "morningstar_instrument_type_code": "CC",
                "morningstar_instrument_type_name": "Cash - Option (Call) (Consolidation to CY after Oct 2022)",
            },
            {"morningstar_instrument_type_code": "CD", "morningstar_instrument_type_name": "Cash - CD/Time Deposit"},
            {"morningstar_instrument_type_code": "CH", "morningstar_instrument_type_name": "Cash - Currency"},
            {"morningstar_instrument_type_code": "CL", "morningstar_instrument_type_name": "Currency - Future"},
            {"morningstar_instrument_type_code": "CN", "morningstar_instrument_type_name": "Bond - Contingent Convertible"},
            {
                "morningstar_instrument_type_code": "CO",
                "morningstar_instrument_type_name": "Cash - Option (Put) (Consolidation to CZ after Oct 2022)",
            },
            {"morningstar_instrument_type_code": "CP", "morningstar_instrument_type_name": "Cash - Commercial Paper"},
            {"morningstar_instrument_type_code": "CQ", "morningstar_instrument_type_name": "Cash - Future Offset"},
            {"morningstar_instrument_type_code": "CR", "morningstar_instrument_type_name": "Cash - Repurchase Agreement"},
            {"morningstar_instrument_type_code": "CS", "morningstar_instrument_type_name": "Currency - Swap"},
            {"morningstar_instrument_type_code": "CT", "morningstar_instrument_type_name": "Bond - Capital Contingent Debt"},
            {"morningstar_instrument_type_code": "CU", "morningstar_instrument_type_name": "Currency - Forward"},
            {
                "morningstar_instrument_type_code": "CV",
                "morningstar_instrument_type_name": "Currency - Warrants\\Rights (Call) (Consolidation to CY after Oct 2022)",
            },
            {
                "morningstar_instrument_type_code": "CX",
                "morningstar_instrument_type_name": "Currency - Warrants\\Rights (Put) (Consolidation to CZ after Oct 2022)",
            },
            {"morningstar_instrument_type_code": "CY", "morningstar_instrument_type_name": "Currency Option (Call)"},
            {"morningstar_instrument_type_code": "CZ", "morningstar_instrument_type_name": "Currency Option (Put)"},
            {"morningstar_instrument_type_code": "DA", "morningstar_instrument_type_name": "Bond - Future"},
            {"morningstar_instrument_type_code": "DB", "morningstar_instrument_type_name": "Bond - Option (Call)"},
            {"morningstar_instrument_type_code": "DC", "morningstar_instrument_type_name": "Commodity - Option (Call)"},
            {"morningstar_instrument_type_code": "DD", "morningstar_instrument_type_name": "Commodity"},
            {"morningstar_instrument_type_code": "DE", "morningstar_instrument_type_name": "Bond - Option (Put)"},
            {"morningstar_instrument_type_code": "DG", "morningstar_instrument_type_name": "Equity - Future"},
            {"morningstar_instrument_type_code": "DH", "morningstar_instrument_type_name": "Equity - Option (Call)"},
            {"morningstar_instrument_type_code": "DI", "morningstar_instrument_type_name": "Equity - Option (Put)"},
            {"morningstar_instrument_type_code": "DJ", "morningstar_instrument_type_name": "Other - Future"},
            {"morningstar_instrument_type_code": "DM", "morningstar_instrument_type_name": "Commodity - Future"},
            {
                "morningstar_instrument_type_code": "DO",
                "morningstar_instrument_type_name": "Bond - Collateralized Debt Obligations (CDO/CBO)",
            },
            {"morningstar_instrument_type_code": "DP", "morningstar_instrument_type_name": "Commodity - Option (Put)"},
            {
                "morningstar_instrument_type_code": "DS",
                "morningstar_instrument_type_name": "Bond - Sub-sovereign Government Debt",
            },
            {"morningstar_instrument_type_code": "E", "morningstar_instrument_type_name": "Equity"},
            {"morningstar_instrument_type_code": "EC", "morningstar_instrument_type_name": "Equity Index - Option (Call)"},
            {"morningstar_instrument_type_code": "EL", "morningstar_instrument_type_name": "Equity Index - Future"},
            {"morningstar_instrument_type_code": "EP", "morningstar_instrument_type_name": "Equity Index - Option (Put)"},
            {"morningstar_instrument_type_code": "EQ", "morningstar_instrument_type_name": "Equity - Undefined"},
            {"morningstar_instrument_type_code": "ER", "morningstar_instrument_type_name": "Equity - REIT"},
            {"morningstar_instrument_type_code": "EU", "morningstar_instrument_type_name": "Equity - Units"},
            {"morningstar_instrument_type_code": "EV", "morningstar_instrument_type_name": "Equity - Warrants/Rights (Put)"},
            {"morningstar_instrument_type_code": "EW", "morningstar_instrument_type_name": "Equity - Warrants/Rights (Call)"},
            {"morningstar_instrument_type_code": "EX", "morningstar_instrument_type_name": "Mutual Fund - Unspecified"},
            {"morningstar_instrument_type_code": "FC", "morningstar_instrument_type_name": "Mutual Fund - Closed End"},
            {"morningstar_instrument_type_code": "FD", "morningstar_instrument_type_name": "Other Fixed Income Derivative"},
            {"morningstar_instrument_type_code": "FE", "morningstar_instrument_type_name": "Mutual Fund - ETF"},
            {"morningstar_instrument_type_code": "FH", "morningstar_instrument_type_name": "Mutual Fund - Hedge Fund"},
            {"morningstar_instrument_type_code": "FM", "morningstar_instrument_type_name": "Mutual Fund - Money Market"},
            {"morningstar_instrument_type_code": "FO", "morningstar_instrument_type_name": "Mutual Fund - Open End"},
            {"morningstar_instrument_type_code": "FS", "morningstar_instrument_type_name": "Mutual Fund - Separate Account"},
            {"morningstar_instrument_type_code": "FV", "morningstar_instrument_type_name": "Mutual Fund - Variable Annuity"},
            {"morningstar_instrument_type_code": "FZ", "morningstar_instrument_type_name": "Mutual Fund - Client Portfolio"},
            {"morningstar_instrument_type_code": "GA", "morningstar_instrument_type_name": "Bond - Non-US Gov't Agency CMO"},
            {"morningstar_instrument_type_code": "GC", "morningstar_instrument_type_name": "Bond - Global Non-Agency CMO"},
            {"morningstar_instrument_type_code": "GM", "morningstar_instrument_type_name": "Bond - Global Non-Agency MBS"},
            {"morningstar_instrument_type_code": "GS", "morningstar_instrument_type_name": "Bond - Short-term Government Bills"},
            {"morningstar_instrument_type_code": "IP", "morningstar_instrument_type_name": "Bond - Corp Inflation Protected"},
            {"morningstar_instrument_type_code": "IS", "morningstar_instrument_type_name": "Inflation Swap"},
            {"morningstar_instrument_type_code": "IT", "morningstar_instrument_type_name": "Income Trust"},
            {
                "morningstar_instrument_type_code": "LO",
                "morningstar_instrument_type_name": "Bond - Collateralized Loan Obligations (CLO)",
            },
            {"morningstar_instrument_type_code": "NB", "morningstar_instrument_type_name": "Bond - Commercial MBS"},
            {"morningstar_instrument_type_code": "NC", "morningstar_instrument_type_name": "Bond - Gov't Agency CMO"},
            {"morningstar_instrument_type_code": "ND", "morningstar_instrument_type_name": "Bond - Covered Bond"},
            {"morningstar_instrument_type_code": "NE", "morningstar_instrument_type_name": "Bond - Gov't Agency ARM"},
            {"morningstar_instrument_type_code": "NR", "morningstar_instrument_type_name": "Bond - U.S. Agency Credit Risk CMO"},
            {"morningstar_instrument_type_code": "OO", "morningstar_instrument_type_name": "Cash - Option Offset"},
            {"morningstar_instrument_type_code": "OS", "morningstar_instrument_type_name": "Cash - Swap Offset"},
            {"morningstar_instrument_type_code": "OT", "morningstar_instrument_type_name": "Cash - Forward Offset"},
            {"morningstar_instrument_type_code": "P", "morningstar_instrument_type_name": "Preferred Stock"},
            {"morningstar_instrument_type_code": "PA", "morningstar_instrument_type_name": "Participating Preferred"},
            {"morningstar_instrument_type_code": "PC", "morningstar_instrument_type_name": "Convertible Preferred"},
            {"morningstar_instrument_type_code": "PP", "morningstar_instrument_type_name": "Property"},
            {"morningstar_instrument_type_code": "PS", "morningstar_instrument_type_name": "Interest Rate Swaption - Payer"},
            {"morningstar_instrument_type_code": "Q", "morningstar_instrument_type_name": "Unidentified Holding"},
            {"morningstar_instrument_type_code": "QQ", "morningstar_instrument_type_name": "Other Assets And Liabilities"},
            {"morningstar_instrument_type_code": "RS", "morningstar_instrument_type_name": "Interest Rate Swaption - Receiver"},
            {"morningstar_instrument_type_code": "SA", "morningstar_instrument_type_name": "Asset Swap"},
            {"morningstar_instrument_type_code": "SC", "morningstar_instrument_type_name": "Mutual Fund - CIT"},
            {"morningstar_instrument_type_code": "SD", "morningstar_instrument_type_name": "Debt Swap"},
            {"morningstar_instrument_type_code": "SE", "morningstar_instrument_type_name": "Equity Swap"},
            {"morningstar_instrument_type_code": "SF", "morningstar_instrument_type_name": "Contract For Difference"},
            {"morningstar_instrument_type_code": "SI", "morningstar_instrument_type_name": "Interest Rate Swap"},
            {"morningstar_instrument_type_code": "SJ", "morningstar_instrument_type_name": "Interest Rate Future"},
            {"morningstar_instrument_type_code": "SK", "morningstar_instrument_type_name": "Interest Rate Forward"},
            {"morningstar_instrument_type_code": "SN", "morningstar_instrument_type_name": "Volatility/Variance Swap"},
            {"morningstar_instrument_type_code": "SQ", "morningstar_instrument_type_name": "Equity Index Swap"},
            {"morningstar_instrument_type_code": "SR", "morningstar_instrument_type_name": "Credit Default Swap"},
            {"morningstar_instrument_type_code": "ST", "morningstar_instrument_type_name": "Total Return Swap"},
            {"morningstar_instrument_type_code": "SU", "morningstar_instrument_type_name": "Structured Product"},
            {"morningstar_instrument_type_code": "SV", "morningstar_instrument_type_name": "Cash - Stable Value Fund"},
            {"morningstar_instrument_type_code": "SW", "morningstar_instrument_type_name": "Credit Default Index Swap (CDX)"},
            {"morningstar_instrument_type_code": "SX", "morningstar_instrument_type_name": "Swaption - Payer"},
            {"morningstar_instrument_type_code": "SY", "morningstar_instrument_type_name": "Swaption - Receiver"},
            {"morningstar_instrument_type_code": "TF", "morningstar_instrument_type_name": "Bond - Treasury Future"},
            {"morningstar_instrument_type_code": "TG", "morningstar_instrument_type_name": "Bond - U.S. Agency TBA"},
            {"morningstar_instrument_type_code": "TP", "morningstar_instrument_type_name": "Bond - Gov't Inflation Protected"},
            {"morningstar_instrument_type_code": "WR", "morningstar_instrument_type_name": "Undefined - Warrants/Rights"},
            {"morningstar_instrument_type_code": "XP", "morningstar_instrument_type_name": "Credit Default Swaption - Payer"},
            {"morningstar_instrument_type_code": "XR", "morningstar_instrument_type_name": "Credit Default Swaption - Receiver"},
            {"morningstar_instrument_type_code": "YF", "morningstar_instrument_type_name": "Cryptocurrency - Future"},
            {"morningstar_instrument_type_code": "YO", "morningstar_instrument_type_name": "Cryptocurrency"},
        ]
    )


@_decorator.typechecked
def get_lookthrough_holdings(portfolio_id: str) -> DataFrame:
    """
    :bdg-ref-danger:`Upcoming Feature <../upcoming_feature>`

    Returns look-through holdings for a user-created portfolio.

    Args:
        portfolio_id (:obj:`str`): Portfolio ID. Use the `get_portfolios <../portfolio/portfolio_list.html#morningstar_data.direct.user_items.get_portfolios>`_ function to discover saved portfolios.

    Returns:
        DataFrame: A DataFrame object with holdings data. DataFrame columns include

        * investment_id
        * isin
        * cusip
        * weight
        * market_value
        * security_name
        * currency
        * morningstar_instrument_type_code
        * entity_id
        * morningstar_entity_name
        * primary_performance_id
        * morningstar_instrument_type_name

    :Examples:

    Retrieve the look-through holdings for a portfolio.
    ::

        import morningstar_data as md

        df = md.direct.get_lookthrough_holdings(portfolio_id='7b9cb5db-e3da-414e-8f75-b52b02222b5a') # Replace with a valid Portfolio ID
        df

    :Output:

        =============  === ======================  ================================
        investment_id  ... primary_performance_id  morningstar_instrument_type_name
        =============  === ======================  ================================
        E0USA00462         0P000000YM              Equity
        F00000Q5HQ	       0P0000Z4DP              Equity
        F00000UMZ1         0P00014J84              Equity
        B10002POBD         None                    Bond - Asset Backed
        =============  === ======================  ================================

    Errors:
        InternalServerError: Raised when the server encounters an unhandled error.

        NetworkExceptionError: Raised when the request fails to reach the server due to a network error.

        TimeoutError: Raised when the fund of fund calculation takes too long.

        ResourceNotFoundError: Raised when portfolio_id does not exist in Direct.

        BadRequestException: Raised when portfolio_id is an invalid UUID.

        UnavailableExternally: Raised when the function is not available for external Python package callers.
    """

    _logger.info("morningstar_data.direct.get_lookthrough_holdings")

    # Get top level holdings in the portfolio
    _logger.info("Fetching top level holdings")

    # Split portfolio type from porfolio id
    portfolio_id = portfolio_id.split(";")[0]
    try:
        uuid.UUID(portfolio_id)
    except ValueError:
        raise BadRequestException(BAD_REQUEST_ERROR_INVALID_PORTFOLIO_ID) from None

    df_top_level_holdings = portfolio.get_holdings(portfolio_ids=[portfolio_id])

    # Convert the weight to float, bcoz we think the FOF requires weight as float
    df_top_level_holdings["Weight"] = df_top_level_holdings["Weight"].astype(float)

    # Split secid and security type. They are bound together by ;
    df_top_level_holdings[["SecId", "SecurityType"]] = df_top_level_holdings["HoldingId"].str.split(";", expand=True)

    # We only are going to query FO and FE fund types. (open ended funds and ETFs)
    # Maybe we need all fund types ???
    fund_secids = df_top_level_holdings.loc[df_top_level_holdings["SecurityType"].isin(["FO", "FE"])]["SecId"].tolist()

    investments = fund_secids

    # Get investment data for each top level fund holding in the portfolio
    # We are making this call to get  masterportfolio_id.
    # If masterportfolio_id is added to lakehouse, this step can be removed

    # only if a portfolio has funds of type FO or FE find the MasterPortfolio Id
    if investments:
        _logger.info("Fetching investment data for all top level holdings")
        _logger.debug(f"{investments}")

        data_points = [
            {"datapointId": "DC09A", "datapointName": MASTER_PORTFOLIO_ID},
            {"datapointId": "OS00I", "datapointName": "SecId"},
        ]
        df_mpid_mapping = inv.get_investment_data(investments, data_points)
        df_top_level_holdings = df_top_level_holdings.merge(df_mpid_mapping[["SecId", MASTER_PORTFOLIO_ID]], on="SecId", how="left")

    _logger.info("Fetching lookthrough holdings from FOF API.")
    try:
        df_lookthrough = _get_lookthrough_holdings_from_fof_api(portfolio_id, df_top_level_holdings)
    except Exception as e:
        _logger.error(e)
        if type(e).__name__ == "InvalidQueryException":
            raise BadRequestException(f"Sorry, something went wrong on our end: {str(e)} Please contact AL support") from None
        else:
            raise e from None

    df_lookthrough = df_lookthrough.rename(
        columns={
            "securityName": "security_name",
            "holdingDetailId": "investment_id",
            "detailHoldingTypeId": "morningstar_instrument_type_code",
            "currencyId": "currency",
            "fractionalWeight": "weight",
        }
    )

    _logger.info("Fetching enriched info with company information.")
    df_enriched_data = _get_ids_from_lake_house(df_lookthrough)

    # add morningstar_instrument_type_name as new column
    df_enriched_data = df_enriched_data.merge(_morningstar_investment_type_id_name_mapping(), on="morningstar_instrument_type_code", how="left")

    # If the user has AMS license, we return ISIN.
    if _has_ams_license_for_isin() == False:
        df_enriched_data = df_enriched_data.drop(["isin", "cusip"])

    return df_enriched_data
