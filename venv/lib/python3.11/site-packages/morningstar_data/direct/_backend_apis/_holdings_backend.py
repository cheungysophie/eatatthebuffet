import os
from .._base_api import APIBackend
from typing import Any, Dict, Optional, Union
from .._exceptions import BadRequestException, NetworkExceptionError, ResourceNotFoundError, ForbiddenError

from ..._base import _logger
from .._error_messages import (
    RESOURCE_NOT_FOUND_ERROR_HOLDING,
)

import requests
import uuid

from .._core_api import make_request
from .._config import _Config

_config = _Config()


class HoldingAPIBackend(APIBackend):
    """
    Subclass to call the Holding API and handle any HTTP errors that occur.
    """

    def __init__(self) -> None:
        super().__init__()

    def _handle_custom_http_errors(self, res: Any) -> Any:
        """
        Handle HTTP errors with custom error messages
        """
        response_message = res.json()["message"]
        if res.status_code == 404:
            _logger.debug(f"Resource Not Found Error: {res.status_code} {response_message}")
            raise ResourceNotFoundError(RESOURCE_NOT_FOUND_ERROR_HOLDING) from None


class FoFAPIBackend(APIBackend):
    """
    Subclass to call the FoF API and handle any HTTP errors that occur.
    Temporarily implements do_get_request and do_put_request becuase the response of FOF api is not JSON
    """

    def __init__(self) -> None:
        super().__init__()

    def do_get_request(self, url: str) -> Any:
        """
        Makes a GET request
        """
        return self._make_request(url, "GET")

    def do_post_request(self, url: str, data: Optional[Union[Dict[Any, Any], str]] = None) -> Any:
        """
        Makes a POST request
        """
        return self._make_request(url, "POST", data)

    def _make_request(self, url: str, method: str, data: Optional[Union[Dict[Any, Any], str]] = None) -> Any:
        """
        Request and handle OK (status_code = 200) and network error responses.
        """
        _logger.info(f"Requesting: {method} {url}")
        try:
            res = make_request(method, url, headers=self.get_headers(), verify=True, data=data)
            res.raise_for_status()
            # We have asked FOF team to return JSON object in the API, so we don't have to implement this class completely like this.
            # https://mswiki.morningstar.com/display/DWH/AL+FOF+Lookthrough+Holding?focusedCommentId=645255358#comment-645255358
            return res.json()
        except requests.ConnectionError:
            raise NetworkExceptionError from None
        except requests.HTTPError:
            self._handle_custom_http_errors(res)
            self._handle_default_http_errors(res)

    def _handle_custom_http_errors(self, res: Any) -> Any:
        """
        Handle HTTP errors with custom error messages
        """
        response_message = res.text
        _logger.error(response_message)
        status_code = res.status_code

        if status_code in [404, 500]:
            raise NetworkExceptionError from None
        elif status_code == 401:
            raise ForbiddenError from None
        else:
            raise BadRequestException(response_message)

    def _handle_default_http_errors(self, res: Any) -> Any:
        """
        Handle HTTP errors with standard messages
        """
        response_message = res.text
        _logger.error(response_message)
        raise


class AMSAPIBackend(APIBackend):
    """
    Subclass to call a Signed url and handle any HTTP errors that occur.
    Temporarily implements do_get_request becuase the request does not need headers and the response need not be JSON
    """

    def __init__(self) -> None:
        super().__init__()

    def do_get_request(self, url: str) -> Any:
        """
        Makes a GET request
        """
        return self._make_request(url, "GET")

    def _make_request(self, url: str, method: str, data: Optional[Union[Dict[Any, Any], str]] = None) -> Any:
        """
        Request and handle OK (status_code = 200) and network error responses.
        """
        _logger.info(f"Requesting: {method} {url}")
        try:
            res = make_request(method, url, headers=self.get_headers(), verify=True, data=data)
            res.raise_for_status()
            return res.json()
        except requests.ConnectionError:
            raise NetworkExceptionError from None
        except requests.HTTPError:
            self._handle_custom_http_errors(res)
            self._handle_default_http_errors(res)

    def _handle_custom_http_errors(self, res: Any) -> Any:
        """
        Handle HTTP errors with custom error messages
        """
        response_message = res.json()["message"]
        if res.status_code == 404:
            _logger.debug(f"Resource Not Found Error: {res.status_code} {response_message}")
            raise ResourceNotFoundError(RESOURCE_NOT_FOUND_ERROR_HOLDING) from None
