from typing import List, Dict
import types
import pandas
from flet import UserControl, Container, Column, Row, Text, margin, alignment
from . import views, utils
from res import dimens


# TODO  use flet's Data Frame when it works?
def data_frame_to_data_table(
    data_frame: pandas.DataFrame,
) -> UserControl:
    """
    Convert a pandas DataFrame to a flet ft.DataTable.
    """
    column_names = data_frame.columns.tolist()

    columns_titles = [
        views.get_headline_txt(
            txt=_format_column_name(name),
            align=utils.TXT_ALIGN_CENTER,
        )
        for name in column_names
    ]

    # Create a list of Row objects using the data in the DataFrame
    data_rows = []
    for i, dataframe_row in data_frame.iterrows():
        total_cells_in_row = len(dataframe_row)
        data_cells = [
            _get_cell(
                views.get_body_txt(
                    _format_data_frame_cell_value(value),
                    align=utils.TXT_ALIGN_CENTER,
                ),
                total_cells=total_cells_in_row,
            )
            for value in dataframe_row
        ]
        data_rows.append(_get_cells_row(data_cells))
    table_controls = [_get_cells_row(columns_titles), views.mdSpace]
    table_controls.extend(data_rows)
    return Column(
        alignment=utils.SPACE_BETWEEN_ALIGNMENT,
        horizontal_alignment=utils.START_ALIGNMENT,
        spacing=dimens.SPACE_STD,
        run_spacing=dimens.SPACE_LG,
        controls=table_controls,
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


def _get_cells_row(controls):
    return Row(
        controls=controls,
        alignment=utils.SPACE_BETWEEN_ALIGNMENT,
        vertical_alignment=utils.CENTER_ALIGNMENT,
        spacing=dimens.SPACE_XS,
        run_spacing=dimens.SPACE_XS,
    )


def _get_cell(content, total_cells: int):
    return Container(
        content=content,
        width=int(dimens.MIN_WINDOW_WIDTH / total_cells),
        margin=margin.only(bottom=dimens.SPACE_STD),
        alignment=alignment.center,
    )
