from typing import List, Dict
import pandas
from . import views, utils
from res import dimens
import pandas
from flet import (
    DataTable,
    Column,
    DataColumn,
    DataRow,
    DataCell,
)


def data_frame_to_data_table(
    data_frame: pandas.DataFrame,
    table_style: Dict = None,
) -> DataTable:
    """
    Convert a pandas DataFrame to a flet DataTable.
    """
    # Get the column names from the DataFrame
    column_names = data_frame.columns.tolist()

    # Create a list of DataColumn objects using the column names
    columns = [
        DataColumn(label=views.get_body_txt(_format_column_name(column_name)))
        for column_name in column_names
    ]

    # Create a list of DataRow objects using the data in the DataFrame
    rows = []
    for i, row in data_frame.iterrows():
        # Create a list of DataCell objects for the row
        cells = [
            DataCell(views.get_body_txt(_format_data_frame_cell_value(value)))
            for value in row
        ]

        # Create a DataRow object for the row
        rows.append(DataRow(cells=cells))

    # Create and return a DataTable object using the columns and rows
    return Column(
        controls=[
            DataTable(
                columns=columns,
                rows=rows,
                **table_style or {},
            )
        ],
        scroll=utils.ALWAYS_SCROLL,
    )


def _format_column_name(value: any) -> str:
    value_as_str = str(value)
    capped = value_as_str.capitalize()
    no_underscores = capped.replace("_", " ")
    return no_underscores


def _format_data_frame_cell_value(value: any) -> str:
    value_as_str = str(value).strip()
    if value_as_str == "False":
        return "No"
    if value_as_str == "True":
        return "Yes"
    if value_as_str == "None":
        return "-"
    return value_as_str
