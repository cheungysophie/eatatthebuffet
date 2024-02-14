import simplejson as json
import logging
import os
import re
import pathlib
import string
import uuid
from typing import Dict, Optional

import boto3
import jwt
import requests
from urllib3.exceptions import InsecureRequestWarning

from ..direct._exceptions import ForbiddenError
from ._delivery_config import DeliveryConfig, DeliveryType
from ..direct._config import _Config

from ..direct._backend_apis import DeliveryAPIBackend
from ..direct._exceptions import BadRequestException, UnauthorizedDeliveryException

# NOTE: We are not able to verify the SSL cert on MDS API since
#       the VPC endpoint domain name is not on the server's SSL cert.
#       So with a heavy heart, we disable the InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


_logger = logging.getLogger(__name__)
_config = _Config()

# A filename can include 'a-z', 'A-Z', '0-9', '-', '_', '(', ')', ' ', '.'
_invalid_chars_regex = re.compile(r"[^a-zA-Z\d\-_\(\)\ .]")


def _get_user_id_from_uim_token() -> str:
    """Returns the user's id by decoding their UIM token"""
    try:
        md_auth_token = md_auth_token = os.getenv("MD_AUTH_TOKEN", os.getenv("UIM_JWT", ""))
        decode_key = os.getenv("UIM_DECODE_KEY", "https://login-prod.morningstar.com/.well-known/jwks.json")
        jwks_client = jwt.jwks_client.PyJWKClient(decode_key)
        signing_key = jwks_client.get_signing_key_from_jwt(md_auth_token)
        decoded_jwt = jwt.decode(
            md_auth_token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
            leeway=60,
        )
        user_id: str = decoded_jwt["sub"].split("|")[1]
        return user_id.upper()
    except Exception as err:
        _logger.error(f"Error decoding MD_AUTH_TOKEN: {err}")
        raise


def _get_user_id_from_eams_token() -> str:
    """Returns the user's id by decoding their EAMS token"""
    try:
        key = os.getenv("EAMS_PUBLIC_KEY", "").replace("\\n", "\n")
        token = os.getenv("EAMS_JWT")
        decoded = jwt.decode(token, key, algorithms=["RS256"])
        user_id: str = decoded["sub"]
        return user_id.upper()
    except Exception as err:
        _logger.error(f"Error decoding EAMS token: {err}")
        raise


def _get_user_id() -> str:
    """Returns the user's id using their UIM token if it exists, EAMS token otherwise"""
    try:
        user_id = _get_user_id_from_uim_token()
        _logger.info(f"Using UIM token for User ID: {user_id}")
        return user_id
    except Exception:
        pass

    user_id = _get_user_id_from_eams_token()
    _logger.info(f"Using EAMS token for User ID: {user_id}")
    return user_id


def _get_job_name() -> str:
    """Returns the job name for a feed or delivery"""
    return str(uuid.uuid4())


def _get_request_id() -> str:
    """Returns the request id for use in POST requests"""
    request_id = os.getenv("REQUEST_ID", str(uuid.uuid4()))
    _logger.info(f"RequestId: {request_id} passed to POST requests")
    return request_id


def _get_bucket_name() -> str:
    """Returns the mds bucket name for s3 upload"""
    return os.getenv("MDS_BUCKET_NAME", "velo-notebook-output-prod-us-east-1")


def _create_feed_body() -> Dict:
    """Creates the post body which is used to call the MDS api when creating a feed id"""
    body = {
        "userId": _get_user_id(),
        "userName": _get_user_id(),
        "jobName": _get_job_name(),
        "jobMetaData": {
            "jobRunUrl": "place_holder",
            "jobRunMethod": "POST",
            "jobPostBody": {
                "app_source": "Morningstar Data Service(MDS)",
                "run_type": "notebook",
                "notebook_parameters": {"bucket": _get_bucket_name()},
            },
        },
    }
    return body


def _get_mds_base_url() -> str:
    return f"{_config.mds_api_url()}"


def _get_al_proxy_base_url() -> str:
    return f"{_config.al_proxy_api_url()}"


def _encrypt_ftp_password(password: str) -> str:
    """Takes a password and encrypts it using the user_id as the salt"""
    _api_backend = DeliveryAPIBackend()
    url = f"{_get_al_proxy_base_url()}encrypt-message"
    data = {"message": password, "salt": _get_user_id()}
    try:
        _logger.info(f"Calling {url} to encrypt ftp password")
        response_json = _api_backend.do_post_request(url, data=json.dumps(data, ignore_nan=True))
        encrypted_password: str = response_json["encrypted_message"]
        return encrypted_password
    except Exception:
        _logger.error("Could not encrypt password using /encrypt-message")
        raise


def _create_deliver_body(output_file_name: str, config: DeliveryConfig, delivered_file_name: Optional[str] = None) -> Dict:
    """Creates the post body which is used to call the MDS delivery api"""
    body = {
        "userId": _get_user_id(),
        "userName": _get_user_id(),
        "jobName": _get_job_name(),
        "s3key": output_file_name,
    }
    if delivered_file_name:
        body["fileName"] = delivered_file_name
    if config.method == DeliveryType.EMAIL:
        body["deliveryInfos"] = {  # type: ignore
            "emails": [
                {
                    "address": config.email_address,
                },
            ]
        }
    elif config.method == DeliveryType.DELIVERY_PROFILE:
        body["deliveryInfos"] = {  # type: ignore
            "profiles": [
                {
                    "deliveryProfileId": config.delivery_profile_id,
                },
            ]
        }
    elif config.method == DeliveryType.FTP:
        body["deliveryInfos"] = {  # type: ignore
            "ftps": [
                {
                    "server": config.server,
                    "username": config.user_name,
                    "password": _encrypt_ftp_password(config.password),
                    "folder": config.folder,
                },
            ]
        }
    return body


def _create_output_file_name(file_path: str) -> str:
    """Creates the output file name for the file which will be uploaded to MDS s3 bucket"""
    file_name = pathlib.Path(file_path).name
    return f"{uuid.uuid4()}-{file_name}"


def _retrieve_credentials() -> Dict[str, str]:
    """Retrieves the credentials required to access the MDS s3 bucket"""
    _api_backend = DeliveryAPIBackend()
    url = f"{_get_al_proxy_base_url()}assume-mds-role?user_id={_get_user_id()}"
    try:
        _logger.info(f"Calling {url} to get assume role credentials")
        response_json: Dict[str, str] = _api_backend.do_get_request(url)
        return response_json
    except ForbiddenError:
        _logger.error(f"Unable to retrieve credentials for MDS s3 bucket upload")
        _logger.error(f"User does not have access to deliver function feature")
        raise UnauthorizedDeliveryException from None


def _get_mds_bucket() -> boto3.session.Session.resource:
    """Returns the MDS bucket where we will upload the file before calling the delivery endpoint"""
    credentials = _retrieve_credentials()
    s3_resource = boto3.resource(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    bucket = s3_resource.Bucket(_get_bucket_name())
    return bucket


def _validate_file_name(file_name: str) -> bool:
    """Checks if the file name used for the delivered file is valid"""
    matches = _invalid_chars_regex.findall(file_name)
    if matches:
        error_message = f"File name: {file_name} is invalid. The following can't be used in the file name: '{matches}'"
        raise BadRequestException(error_message)
    return True
