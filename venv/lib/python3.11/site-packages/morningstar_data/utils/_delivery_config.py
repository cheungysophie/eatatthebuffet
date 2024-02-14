import dataclasses
import re
from enum import Enum

from ..direct._exceptions import ValueErrorException


class DeliveryConfigErrorMessage(Enum):
    EMAIL = """
        Invalid Email Address.
        Example:
        - email = "analyticslab.user@morningstar.com"
    """
    FTP = """
        Invalid FTP configuration.
        The username and password must not be empty
        The server must not include any protocal, like "ftp://".
        The folder must not include a root path '/'.
        Example:
        - user_name = "analyticslab_user"
        - password = "password123"
        - server = "ftp.morningstar.com"
        - folder = "folder_1/folder_2/"
    """
    DELIVERY_PROFILE = """
        Invalid delivery profile Id.
        The delivery profile id must not be empty
        The delivery profile id must be a digit string
        Example:
        - delivery_profile_id = "12345"
    """


class DeliveryType(Enum):
    EMAIL = 1
    FTP = 2
    DELIVERY_PROFILE = 3


@dataclasses.dataclass
class DeliveryConfig:
    """Container for delivery configuration settings
    Args:
        method (:obj:`DeliveryType`): Required, the type of delivery, see DeliveryType for supported options
        email_address (:obj:`str`): a valid email_address to send the file to, needed if using "email" delivery option
        user_name (:obj:`str`): the user_name to login to the ftp server, needed if using "ftp" method
        password (:obj:`str`): the password to login to the ftp server, needed if using "ftp" method
        server (:obj:`str`): the ftp server to use, needed if using "ftp" method. The server address should not include "ftp://"
        folder (:obj:`str`): the folder on the ftp server to upload the file to, needed if using "ftp" method. The folder should not include a folder path like "/folder"

    :Examples:

    Valid delivery config

    ::
        email_address = "test@morningstar.com"
        delivery_config_email = md.utils.DeliveryConfig(method=md.utils.DeliveryType.EMAIL, email_address=email_address)

        ftp_username = "test"
        ftp_password = "test_pwd"
        ftp_server = "ts.ftp.com"
        ftp_folder = "data/"
        delivery_config_ftp = md.utils.DeliveryConfig(method=md.utils.DeliveryType.FTP, user_name=ftp_username, password=ftp_password, server=ftp_server, folder=ftp_folder)

        delivery_profile_id = "12345"
        delivery_config_email = md.utils.DeliveryConfig(method=md.utils.DeliveryType.DELIVERY_PROFILE, delivery_profile_id=delivery_profile_id)

    Invalid delivery config

    ::
        email_address = "@invalid_email_address@morningstar.com"
        delivery_config_email = md.utils.DeliveryConfig(method=md.utils.DeliveryType.EMAIL, email_address=email_address)
        >>> ValueErrorException: Invalid Email Address

        ftp_username = "test"
        ftp_password = "test_pwd"
        ftp_server = "ftp://ts.ftp.com"
        ftp_folder = "/data/"
        delivery_config_ftp = md.utils.DeliveryConfig(method=md.utils.DeliveryType.FTP, user_name=ftp_username, password=ftp_password, server=ftp_server, folder=ftp_folder)
        >>> ValueErrorException: Invalid FTP configuration

        delivery_profile_id = "12ABC"
        delivery_config_email = md.utils.DeliveryConfig(method=md.utils.DeliveryType.DELIVERY_PROFILE, delivery_profile_id=delivery_profile_id)
        >>> ValueErrorException: Invalid delivery profile Id
    """

    method: DeliveryType
    email_address: str = ""
    delivery_profile_id: str = ""
    user_name: str = ""
    password: str = ""
    server: str = ""
    folder: str = ""

    def __post_init__(self) -> None:
        if not self.is_valid():
            raise ValueErrorException(DeliveryConfigErrorMessage[self.method.name].value)

    def _is_email_valid(self) -> bool:
        """Check whether the email config provided is valid"""
        email_regex = re.compile(
            r"""\b             # a word boundary
                [a-z0-9._%+-]+ # the email prefix part, any character in the list
                @              # the @ part
                [a-z0-9.-]+    # the email domain name part, any character in the list
                \.             # the dot part
                [a-z]{2,}      # the top-level domain part, any alphabetical character and length >= 2
                \b             # a word boundary
            """,
            re.X,
        )
        return re.fullmatch(email_regex, self.email_address.lower()) is not None

    def _is_delivery_profile_valid(self) -> bool:
        """Checks if the provided delivery profile ID is valid.
        At present, the MDS delivery endpoint allows any user to deliver to any profile ID.
        In the future, MDS need to add validation based on the user's company.
        """
        return self.delivery_profile_id.isdigit()

    def _is_ftp_valid(self) -> bool:
        """Check whether the ftp config provided is valid"""
        if self.user_name == "" or self.password == "":
            return False

        server_regex = re.compile(
            r"""\b          # a word boundary
                [a-z0-9.-]+ # the domain name part, any character in the list
                \.          # the dot part
                [a-z]{2,}   # the top-level domain part, any alphabetical character and length >= 2
                \b          # a word boundary
            """,
            re.X,
        )
        if not re.fullmatch(server_regex, self.server.lower()):
            return False

        folder_regex = re.compile(
            r"""
                ^[^\/]                   # cannot start with /
                (
                    [\w\d\s\._%+-\[\]]+  # any character in the list
                    [\/]{1,1}            # ending with /
                )+                       # capturing group
            """,
            re.X,
        )
        if not re.fullmatch(folder_regex, self.folder):
            return False

        return True

    def is_valid(self) -> bool:
        is_email_valid = self.method == DeliveryType.EMAIL and self._is_email_valid()
        is_ftp_valid = self.method == DeliveryType.FTP and self._is_ftp_valid()
        is_delivery_profile_valid = self.method == DeliveryType.DELIVERY_PROFILE and self._is_delivery_profile_valid()
        return is_email_valid or is_ftp_valid or is_delivery_profile_valid
