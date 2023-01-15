from typing import List, Dict

import pandas
from flet import (
    DataTable,
    DataColumn,
    DataRow,
    DataCell,
    Text,
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
    columns = [DataColumn(label=Text(name)) for name in column_names]

    # Create a list of DataRow objects using the data in the DataFrame
    rows = []
    for i, row in data_frame.iterrows():
        # Create a list of DataCell objects for the row
        cells = [DataCell(Text(str(value))) for value in row]

        # Create a DataRow object for the row
        rows.append(DataRow(cells=cells))

    # Create and return a DataTable object using the columns and rows
    return DataTable(
        columns=columns,
        rows=rows,
        **table_style or {},
    )
