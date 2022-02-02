from pathlib import Path
from typing import Type
import collections
import functools
import inspect
import warnings

# import ipywidgets as widgets
import sqlmodel


# def model_form(
#     model_class: Type[sqlmodel.SQLModel],
# ):
#     properties = model_class.schema()["properties"]
#     print(properties)
#     form_header = [
#         widgets.HTML(
#             value=f"<b>Create {model_class.__name__}</b>",
#         )
#     ]
#     form_elements = collections.OrderedDict()
#     for (prop_name, prop_meta) in properties.items():
#         if prop_name == "id":
#             # ignore id columns
#             pass
#         if prop_name.endswith("_id"):
#             # relationship field
#             pass
#         if prop_meta["type"] == "string":
#             text_field = widgets.Text(description=prop_meta["title"], disabled=False)
#             form_elements[prop_name] = text_field
#         elif prop_meta["type"] == "int":
#             int_field = widgets.IntText(description=prop_meta["title"], disabled=False)
#             form_elements[int_field] = int_field

#     # assemble form

#     create_button = widgets.Button(
#         description="Create",
#         disabled=False,
#         button_style="success",  # 'success', 'info', 'warning', 'danger' or ''
#         tooltip="Create model object",
#         icon="hammer",  # (FontAwesome names without the `fa-` prefix)
#     )

#     def factory_function():
#         instance = model_class(
#             **dict(
#                 (prop_name, form_elements[prop_name].value)
#                 for prop_name in form_elements.keys()
#             )
#         )
#         return instance

#     create_button.on_click(factory_function)

#     form = widgets.VBox(
#         children=(form_header + list(form_elements.values()) + [create_button])
#     )
#     return form


string_types = (type(b""), type(""))


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, string_types):

        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                warnings.simplefilter("default", DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
