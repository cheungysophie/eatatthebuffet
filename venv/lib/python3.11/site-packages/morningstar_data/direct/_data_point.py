import simplejson as json

from pandas import DataFrame
from typing import List, Dict, Any
 
from . import _decorator
from .._base import _logger
from ._exceptions import ValueErrorException
from ._api import _direct_api_request
from ._config import _Config

_config = _Config()


def _data_point_request_builder(data_point_details: list) -> List[Any]:
    if not data_point_details:
        raise ValueErrorException("No datapoint available.")
    url = f"{_config.data_point_service_url()}v1/datapoints/datapointrequestbuilder"
    response_json: List[Any] = _direct_api_request("POST", url, json.dumps(data_point_details, ignore_nan=True))

    return response_json


def _request_asset_flow_data_points() -> List[Any]:
    url = f"{_config.securitydata_service_url()}v1/assetflow/datapoints"
    response_json: List[Any] = _direct_api_request("GET", url)
    return response_json


def _get_asset_flow_data_points_by_ids(data_point_ids: list) -> list:
    response_json = _request_asset_flow_data_points()
    result = []
    if response_json and isinstance(response_json, list):
        data_point_id_settings_dict = {x.get("datapointId", "").strip(): x for x in response_json if x is not None}
        for data_point_id in data_point_ids:
            settings = data_point_id_settings_dict.get(data_point_id)
            if settings is not None:
                settings = settings.copy()
                settings["datapointName"] = settings.pop("name")
                settings["alias"] = settings["datapointName"]
                result.append(settings)
    return result


@_decorator.error_handler
def _get_data_point_details(params: list) -> List[Dict[Any, Any]]:
    url = f"{_config.data_point_service_url()}v1/datapoints/detail"
    response_json: List[Dict[Any, Any]] = _direct_api_request("POST", url, json.dumps(params, ignore_nan=True))
    return _filter_time_series_data_points(params, response_json)


def _filter_time_series_data_points(data_points: List[Dict[Any, Any]], data_points_detail: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
    for data_point in data_points:
        data_point_id = data_point.get("datapointId")
        compare_id = lambda x, id=data_point_id: x.get("datapointId") == id
        should_keep_dp = lambda x, id=data_point_id: x.get("datapointId") != id or x.get("isTsdp") != False  or x.get("canBeAddedToDataset")  
        
        data_points_detail_for_id = list(filter(compare_id, data_points_detail))
        if len(data_points_detail_for_id) > 1:
            data_points_detail = list(filter(should_keep_dp, data_points_detail))
    return data_points_detail


@_decorator.error_handler
def _get_all_universes() -> DataFrame:
    url = f"{_config.data_point_service_url()}v1/universes"
    response_json = _direct_api_request("GET", url)
    result = DataFrame(response_json)
    return result[["id", "name"]]
