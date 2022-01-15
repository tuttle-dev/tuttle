from pathlib import Path
from typing import Type
import collections

import ipywidgets as widgets
import sqlmodel


def model_form(
    model_class: Type[sqlmodel.SQLModel],
):
    properties = model_class.schema()["properties"]
    print(properties)
    form_header = [
        widgets.HTML(
            value=f"<b>Create {model_class.__name__}</b>",
        )
    ]
    form_elements = collections.OrderedDict()
    for (prop_name, prop_meta) in properties.items():
        if prop_name == "id":
            # ignore id columns
            pass
        if prop_name.endswith("_id"):
            # relationship field
            pass
        if prop_meta["type"] == "string":
            text_field = widgets.Text(description=prop_meta["title"], disabled=False)
            form_elements[prop_name] = text_field
        elif prop_meta["type"] == "int":
            int_field = widgets.IntText(description=prop_meta["title"], disabled=False)
            form_elements[int_field] = int_field

    # assemble form

    create_button = widgets.Button(
        description="Create",
        disabled=False,
        button_style="success",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Create model object",
        icon="hammer",  # (FontAwesome names without the `fa-` prefix)
    )

    def factory_function():
        instance = model_class(
            **dict(
                (prop_name, form_elements[prop_name].value)
                for prop_name in form_elements.keys()
            )
        )
        return instance

    create_button.on_click(factory_function)

    form = widgets.VBox(
        children=(form_header + list(form_elements.values()) + [create_button])
    )
    return form
