import enum
from enum import Enum
from typing import Any
from ._exceptions import BadRequestException


class DatabaseCD(str, Enum):
    user = ("UDP",)
    firm = ("CDP",)


class RaiseEnum(enum.EnumMeta):
    def __getitem__(cls, name: str) -> Any:
        try:
            return super().__getitem__(name)
        except KeyError:
            options = ", ".join(cls._member_map_.keys())
            raise BadRequestException(f"Please choose one of the following valid options: '{options}'.\n" f"'{name}' is an invalid choice.\n") from None


class ErrorMessages(str, Enum):
    date_format_error = "Please input the date in yyyy-MM-dd format."
    start_date_require_error = "Please specify start_date to proceed with your query."
    no_data_point_msg = "There is no data point available."
    start_end_date_error = "Please specify start_date and end_date to proceed with your query."
    frequency_error_msg = "Please specify frequency to proceed with your query."
    currency_error_msg = "Please specify currency to proceed with your query."


class DryRunResults:
    estimated_cells_used: int
    daily_cells_remaining_before: int
    daily_cells_remaining_after: int
    daily_cell_limit: int

    def __init__(self, estimated_cells_used: int, daily_cells_remaining_before: int, daily_cell_limit: int) -> None:
        self.estimated_cells_used = estimated_cells_used
        self.daily_cells_remaining_before = daily_cells_remaining_before
        self.daily_cell_limit = daily_cell_limit
        self.daily_cells_remaining_after = daily_cells_remaining_before - estimated_cells_used
