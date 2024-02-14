import simplejson as json
import logging
import os
from typing import Dict, Any, Optional
import polling2

from botocore.exceptions import ClientError
from ..direct._backend_apis import DeliveryAPIBackend

from ._delivery_config import DeliveryConfig
from ._helpers import _get_mds_base_url, _get_mds_bucket, _create_deliver_body, _create_feed_body, _create_output_file_name, _validate_file_name
from ..direct import _decorator

_logger = logging.getLogger(__name__)
_api_backend = DeliveryAPIBackend()


def _create_feed_id() -> int:
    """Calls the MDS feeds api to generate a new feed id.

    This feed id is needed when calling the MDS deliver api. In general, when a notebook is running
    in a schedule it will be passed in this feed id. But for an ad-hoc delivery this feed id needs
    to be created before the MDS delivery api can be called.
    """
    _logger.info("Creating a feed id using MDS api")
    url = f"{_get_mds_base_url()}v1/feeds?type=notebook"
    data = _create_feed_body()

    try:
        _logger.info(f"Calling MDS /feeds endpoint with: {data}")
        response_json = _api_backend.do_post_request(url, data=json.dumps(data, ignore_nan=True))
        feed_id: int = response_json["feedId"]
        return feed_id
    except Exception:
        _logger.error("Could not create a feed id using MDS api")
        raise


def _upload_to_s3(file_path: str, output_file_name: str) -> None:
    """Uploads a file to the MDS s3 bucket"""
    try:
        output_bucket = _get_mds_bucket()
        output_bucket.upload_file(file_path, output_file_name)
    except FileNotFoundError:
        _logger.error(f"File not found: {file_path}, make sure the file you are trying to upload exists")
        raise
    except ClientError:
        _logger.error("Could not upload to s3 bucket due to AWS error")
        raise
    except Exception:
        _logger.error("Could not upload to s3 bucket")
        raise


def _mds_deliver_file(output_file_name: str, config: DeliveryConfig, feed_id: int, delivered_file_name: Optional[str] = None) -> str:
    """Calls the MDS delivery api with the needed information to deliver the uploaded file and returns job_id"""
    url = f"{_get_mds_base_url()}v1/delivery/{feed_id}"
    data = _create_deliver_body(output_file_name, config, delivered_file_name)
    _logger.info(f"Calling MDS /delivery/{feed_id} endpoint with: {data}")
    response_json = _api_backend.do_post_request(url, data=json.dumps(data, ignore_nan=True))
    _logger.info(f"Delivery response: {response_json}")
    job_id: str = response_json["jobId"]
    return job_id


@_decorator.typechecked
def get_delivery_profile() -> Dict:
    """Fetch ftp delivery profiles using MDS API
    Returns:
        :obj:`dict`: FTP delivery profiles for the user.
    """
    url = f"{_get_mds_base_url()}v1/delivery-profile"
    _logger.info(f"Calling MDS /delivery-profile endpoint. ")
    mds_delivery_profiles: Dict[Any, Any] = _api_backend.do_get_request(url)
    _logger.info(f"MDS delivery profile response: {mds_delivery_profiles}")
    ftp_delivery_profiles = {"ftps": mds_delivery_profiles.get("ftps", [])}
    return ftp_delivery_profiles


@_decorator.typechecked
def delivery_status(job_id: str, poll: bool = True) -> str:
    """Polls the MDS delivery api with the job_id to check the delivery status.
    Args:
        job_id (:obj:`str`): The job id that we get from MDS endpoint
        poll (:obj:`bool`): Flag to poll the endpoint or not (default is set as True,
        as we want to poll the endpoint to get the status)

    Returns:
        :obj:`str`: Delivery status as given by the endpoint.
    """
    url = f"{_get_mds_base_url()}v1/jobs/{job_id}/status"
    _logger.info(f"Calling MDS /delivery/{job_id}/status endpoint")

    # polling the endpoint till it gets status response; raise exception error if occurred
    def _delivery_finished(res: dict) -> bool:
        try:
            return res["jobStatus"].lower() in ["done", "failed"]
        except KeyError as e:
            _logger.error(f"Could not find delivery status. Exception as {e}")
            raise

    if poll:
        _logger.info(f"Polling the request to get the delivery status.")
        try:
            polling2.poll(
                lambda: _api_backend.do_get_request(url),
                step=5,
                timeout=60,
                check_success=lambda response: _delivery_finished(response),
            )
        except polling2.TimeoutException as te:
            _logger.info(f"Timeout for the request. Exception as {te}.")

    response_json = _api_backend.do_get_request(url)
    _logger.info(f"Delivery status: {response_json}")
    return str(response_json["jobStatus"])  # "DONE" or "FAILED" or "RUNNING"


@_decorator.typechecked
def deliver(file_path: str, config: DeliveryConfig, wait_for_delivery: bool = False, delivered_file_name: Optional[str] = None) -> dict:
    """
    :bdg-ref-danger:`Upcoming Feature <../upcoming_feature>`

    Delivers a file from a notebook to an email or FTP.

    Args:
        file_path (:obj:`str`): The path to the file that will be delivered, including file name and extension.
        config (:obj:`md.utils.DeliveryConfig`): An object that holds the delivery configuration information.

            For an email it contains
                * method (:obj:`DeliveryType`): ``DeliveryType.EMAIL`` in this case.
                * email_address (:obj:`str`): email_address to send the file to.
            For FTP it contains
                * method (:obj:`DeliveryType`): ``DeliveryType.FTP`` in this case.
                * user_name (:obj:`str`): the user_name to login to the ftp server.
                * password (:obj:`str`): the password to login to the ftp server.
                * server (:obj:`str`): the ftp server to use.
                * folder (:obj:`str`): the folder on the ftp server to upload the file to.
            For a Delivery Profile it contains
                * method (:obj:`DeliveryType`): ``DeliveryType.DELIVERY_PROFILE`` in this case.
                * delivery_profile_id (:obj:`str`): delivery_profile_id that was setup by MDS. Can be retrieved with get_delivery_profile()
        wait_for_delivery (:obj:`bool`): Flag to poll the api to check the delivery status or not. (True=show status)
        delivered_file_name (:obj:`Optional[str]`): An optional parameter for the user to specify the file name to be used when
            delivered. No file extension should be provided. Valid characters are `., -, _, (, ), , a-z, A-Z, 0-9`. If the file
            name includes non-valid characters, an exception will be raised.

    Returns:
        :obj:`dict`: A dictionary with the 'job_id', 'message', 'delivery_status' keys containing information about the delivery status

    :Examples:

    Deliver to an email address.

    ::

        import morningstar_data as md
        import pandas as pd

        df = pd.DataFrame({'a':[1], 'b':[2]})
        df.to_csv("test_export.csv")

        # Email example
        delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.EMAIL, email_address="test@email.com")
        md.utils.deliver("test_export.csv", delivery_config)

    Deliver to a ftp server.

    ::

        import morningstar_data as md
        import pandas as pd

        df = pd.DataFrame({'a':[1], 'b':[2]})
        df.to_csv("test_export.csv")

        # FTP example
        delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.FTP, user_name="test", password="test", server="ts.ftp.com", folder="data/")
        md.utils.deliver("test_export.csv", delivery_config)

    Deliver to a Delivery Profile

    ::

        import morningstar_data as md
        import pandas as pd

        df = pd.DataFrame({'a':[1], 'b':[2]})
        df.to_csv("test_export.csv")

        # Delivery Profile example
        delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.DELIVERY_PROFILE, delivery_profile_id="1234")
        md.utils.deliver("test_export.csv", delivery_config)

    Multiple delivery within a single notebook.

    ::

        import morningstar_data as md
        import pandas as pd

        df = pd.DataFrame({'a':[1], 'b':[2]})
        df.to_csv("test_export.csv")

        ftp_delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.FTP, user_name="test", password="test", server="ts.ftp.com", folder="data/")
        md.utils.deliver("test_export.csv", ftp_delivery_config)

        email_delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.EMAIL, email_address="test@email.com")
        md.utils.deliver("test_export.csv", email_delivery_config)

    Deliver with a specific filename.

    ::

        import morningstar_data as md
        import pandas as pd

        df = pd.DataFrame({'a':[1], 'b':[2]})
        df.to_csv("test_export.csv")

        # Email example
        delivery_config = md.utils.DeliveryConfig(method=md.utils.DeliveryType.EMAIL, email_address="test@email.com")
        md.utils.deliver("test_export.csv", delivery_config, delivered_file_name="Delivered_Dataframe_123")
        # File delivered will be named "Delivered_Dataframe_123.csv"

    Errors:
        AccessDeniedError: Raised when the user is not authenticated.

        UnauthorizedDeliveryException: Raised when the user does not have permissions to deliver artifacts.

        BadRequestError: Raised when the user does not provide a properly formatted request.

        InternalServerError: Raised when the server encounters an unhandled error.

        NetworkExceptionError: Raised when the request fails to reach the server due to a network error.

        FileNotFoundError: Raised when the file path specified to be delivered does not exist
    """
    if delivered_file_name:
        _validate_file_name(delivered_file_name)

    # Check for a feed_id, create one if not specified
    try:
        feed_id = int(os.environ["FEED_ID"])
    except KeyError:
        feed_id = _create_feed_id()

    output_file_name = _create_output_file_name(file_path)

    _upload_to_s3(file_path, output_file_name)
    job_id: str = _mds_deliver_file(output_file_name, config, feed_id, delivered_file_name)

    res = {"job_id": job_id, "message": "Delivery has been submitted."}

    # if flag is set True, poll the api, return the delivery status
    res["delivery_status"] = delivery_status(job_id, poll=wait_for_delivery)
    return res
