import typing
from typing import Callable, List, Optional, Union
from dataclasses import dataclass
import datetime

from flet import (
    AlertDialog,
    Column,
    Container,
    Dropdown,
    ElevatedButton,
    FilledButton,
    Icon,
    Image,
    PopupMenuButton,
    PopupMenuItem,
    ProgressBar,
    margin,
    NavigationRail,
    Row,
    Text,
    TextField,
    TextStyle,
    UserControl,
    alignment,
    border_radius,
    dropdown,
    icons,
    padding,
)

from res import colors, dimens, fonts, image_paths

from .abstractions import DialogHandler
from . import utils


class Spacer(Container):
    """Creates a space between controls"""

    def __init__(
        self,
        lg_space: bool = False,
        md_space: bool = False,
        sm_space: bool = False,
        xs_space: bool = False,
        default_space: int = dimens.SPACE_STD,
    ):
        self._space_size = (
            dimens.SPACE_LG
            if lg_space
            else dimens.SPACE_MD
            if md_space
            else dimens.SPACE_SM
            if sm_space
            else dimens.SPACE_XS
            if xs_space
            else default_space
        )
        super().__init__(
            height=self._space_size, width=self._space_size, padding=0, margin=0
        )


class StdHeading(Text):
    """Creates a standard heading"""

    def __init__(
        self,
        title: str = "",
        size: int = fonts.SUBTITLE_1_SIZE,
        color: Optional[str] = None,
        align: str = utils.TXT_ALIGN_LEFT,
        show: bool = True,
        expand: bool | int | None = None,
    ):
        """Displays text formatted as a headline"""
        super().__init__(
            title,
            font_family=fonts.HEADLINE_FONT,
            weight=fonts.BOLD_FONT,
            size=size,
            color=color,
            text_align=align,
            visible=show,
            expand=expand,
        )


class StdSubHeading(Text):
    """Creates a standard subheading"""

    def __init__(
        self,
        subtitle: str = "",
        size: int = fonts.SUBTITLE_2_SIZE,
        color: Optional[str] = None,
        align: str = utils.TXT_ALIGN_LEFT,
        show: bool = True,
        expand: bool | int | None = None,
    ):
        super().__init__(
            subtitle,
            font_family=fonts.HEADLINE_FONT,
            size=size,
            color=color,
            text_align=align,
            visible=show,
            expand=expand,
        )


class StdHeadingWithSubheading(Column):
    """Creates a standard heading with a subheading"""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        alignment_in_container: str = utils.START_ALIGNMENT,
        txt_alignment: str = utils.TXT_ALIGN_LEFT,
        title_size: int = fonts.SUBTITLE_1_SIZE,
        subtitle_size: int = fonts.SUBTITLE_2_SIZE,
        subtitle_color: Optional[str] = None,
    ):

        super().__init__(
            spacing=0,
            horizontal_alignment=alignment_in_container,
            controls=[
                StdHeading(
                    title=title,
                    size=title_size,
                    align=txt_alignment,
                ),
                StdSubHeading(
                    subtitle=subtitle,
                    size=subtitle_size,
                    align=txt_alignment,
                    color=subtitle_color,
                ),
            ],
        )


class StdBodyText(Text):
    """Creates a standard body text"""

    def __init__(
        self,
        txt: str = "",
        size: int = fonts.BODY_1_SIZE,
        color: Optional[str] = None,
        show: bool = True,
        col: Optional[dict] = None,
        align: str = utils.TXT_ALIGN_LEFT,
        **kwargs,
    ):
        super().__init__(
            col=col,
            value=txt,
            color=color,
            size=size,
            visible=show,
            text_align=align,
            **kwargs,
        )


class StdTextField(TextField):
    """Creates a standard text field"""

    def __init__(
        self,
        on_change: typing.Optional[Callable] = None,
        label: str = "",
        hint: str = "",
        keyboard_type: str = utils.KEYBOARD_TEXT,
        on_focus: typing.Optional[Callable] = None,
        initial_value: typing.Optional[str] = None,
        expand: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        show: bool = True,
    ):
        """Displays commonly used text field in app forms"""
        txtFieldPad = padding.symmetric(horizontal=dimens.SPACE_XS)

        super().__init__(
            label=label,
            keyboard_type=keyboard_type,
            content_padding=txtFieldPad,
            hint_text=hint,
            hint_style=TextStyle(size=fonts.CAPTION_SIZE),
            value=initial_value,
            focused_border_width=1,
            on_focus=on_focus,
            on_change=on_change,
            password=keyboard_type == utils.KEYBOARD_PASSWORD,
            expand=expand,
            width=width,
            disabled=keyboard_type == utils.KEYBOARD_NONE,
            text_size=fonts.BODY_1_SIZE,
            label_style=TextStyle(size=fonts.BODY_2_SIZE),
            error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
            visible=show,
        )


class StdMultilineField(TextField):
    """Creates a standard multiline text field"""

    def __init__(
        self,
        on_change,
        label: str,
        hint: str,
        on_focus: typing.Optional[Callable] = None,
        keyboardType: str = utils.KEYBOARD_MULTILINE,
        minLines: int = 3,
        maxLines: int = 5,
    ):
        txtFieldHintStyle = TextStyle(size=fonts.CAPTION_SIZE)

        super().__init__(
            label=label,
            keyboard_type=keyboardType,
            hint_text=hint,
            hint_style=txtFieldHintStyle,
            focused_border_width=1,
            min_lines=minLines,
            max_lines=maxLines,
            on_focus=on_focus,
            on_change=on_change,
            text_size=fonts.BODY_1_SIZE,
            label_style=TextStyle(size=fonts.BODY_2_SIZE),
            error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
        )


class StdErrorText(StdBodyText):
    """Displays text formatted for errors / warnings"""

    def __init__(
        self,
        txt: str,
        show: bool = True,
    ):
        super().__init__(txt, color=colors.ERROR_COLOR, show=show)


class StdPrimaryButton(FilledButton):
    """A button with primary styling"""

    def __init__(
        self,
        on_click: Optional[Callable] = None,
        label: str = "",
        width: int = 200,
        icon: Optional[str] = None,
        show: bool = True,
    ):
        super().__init__(label, width=width, on_click=on_click, icon=icon, visible=show)


class StdSecondaryButton(ElevatedButton):
    """A button with secondary styling"""

    def __init__(
        self,
        on_click: Optional[Callable] = None,
        label: str = "",
        width: int = 200,
        icon: Optional[str] = None,
    ):

        super().__init__(
            label,
            width=width,
            on_click=on_click,
            icon=icon,
        )


class StdDangerButton(FilledButton):
    """A button styled for dangerous actions e.g. delete"""

    def __init__(
        self,
        on_click: Optional[Callable] = None,
        label: str = "",
        width: int = 200,
        icon: Optional[str] = None,
        tooltip: Optional[str] = None,
    ):

        super().__init__(
            label,
            width=width,
            on_click=on_click,
            icon=icon,
            icon_color=colors.DANGER_COLOR,
            tooltip=tooltip,
        )


class StdProfilePhotoImg(Image):
    """Creates a profile photo image"""

    def __init__(
        self,
        pic_src: str = image_paths.default_avatar,
    ):
        super().__init__(
            src=pic_src,
            width=72,
            height=72,
            border_radius=border_radius.all(36),
            fit=utils.CONTAIN,
        )


class StdImage(Container):
    """Creates a standard image wrapped in a container"""

    def __init__(
        self,
        path: str,
        semantic_label: str,
        width: int,
    ):
        super().__init__(
            width=width,
            content=Image(src=path, fit=utils.CONTAIN, semantics_label=semantic_label),
        )


class StdAppLogo(Container):
    """Creates a standard app logo"""

    def __init__(
        self,
        width: int = 12,
    ):
        super().__init__(
            width=width,
            content=Image(
                src=image_paths.logoPath, fit=utils.CONTAIN, semantics_label="logo"
            ),
        )


class StdAppLogoWithLabel(Row):
    """Returns app logo with app name next to it"""

    def __init__(self):
        super().__init__(
            vertical_alignment=utils.CENTER_ALIGNMENT,
            controls=[
                StdAppLogo(),
                StdHeading(
                    "Tuttle",
                    size=fonts.HEADLINE_3_SIZE,
                ),
            ],
        )


class StdProgressBar(ProgressBar):
    """Creates a standard progress bar"""

    def __init__(
        self,
        show: bool = True,
    ):
        super().__init__(width=320, height=4, visible=show)


class StdDropDown(UserControl):
    """Creates a standard dropdown button"""

    def __init__(
        self,
        label: str,
        on_change: Callable,
        items: List[str],
        hint: Optional[str] = "",
        width: Optional[int] = None,
        initial_value: Optional[str] = None,
        show: bool = True,
    ):
        super().__init__()
        self.visible = show
        self.label = label
        self.on_change = on_change
        self.initial_value = initial_value
        self.width = width
        self.hint = hint
        self.options = []
        for item in items:
            self.options.append(
                dropdown.Option(
                    text=item,
                )
            )

    def update_dropdown_items(self, items: List[str]):
        """Updates the dropdown items"""
        self.options.clear()
        for item in items:
            self.options.append(
                dropdown.Option(
                    text=item,
                )
            )
        self.drop_down.options = self.options
        self.update()

    def update_value(
        self,
        new_value: str,
    ):
        """Updates the dropdown value"""
        self.drop_down.value = new_value
        self.update()

    def update_error_txt(self, error_txt: str = ""):
        """Updates Or clears the error text"""
        self.drop_down.error_text = error_txt if error_txt else None
        self.update()

    def build(self):
        self.drop_down = Dropdown(
            label=self.label,
            hint_text=self.hint,
            options=self.options,
            text_size=fonts.BODY_1_SIZE,
            label_style=TextStyle(size=fonts.BODY_2_SIZE),
            on_change=self.on_change,
            width=self.width,
            value=self.initial_value,
            content_padding=padding.all(dimens.SPACE_XS),
            error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
            visible=self.visible,
        )
        return self.drop_down


class DateSelector(UserControl):
    """Date selector."""

    def __init__(
        self,
        label: str,
        initial_date: Optional[datetime.date] = None,
        label_color: Optional[str] = None,
    ):
        super().__init__()
        self.label = label
        self.initial_date = initial_date if initial_date else datetime.date.today()
        self.date = str(self.initial_date.day)
        self.month = str(self.initial_date.month)
        self.year = str(self.initial_date.year)
        self.label_color = label_color

        self.day_dropdown = StdDropDown(
            label="Day",
            hint="",
            on_change=self.on_date_set,
            items=[str(day) for day in range(1, 32)],
            width=50,
            initial_value=self.date,
        )

        self.month_dropdown = StdDropDown(
            label="Month",
            on_change=self.on_month_set,
            items=[str(month) for month in range(1, 13)],
            width=50,
            initial_value=self.month,
        )

        self.year_dropdown = StdDropDown(
            label="Year",
            on_change=self.on_year_set,
            # set items to a list of years -10 to + 10 years from now
            items=[
                str(year)
                for year in range(
                    datetime.date.today().year - 10, datetime.date.today().year + 10
                )
            ],
            width=100,
            initial_value=self.year,
        )

    def on_date_set(self, e):
        self.date = e.control.value

    def on_month_set(self, e):
        self.month = e.control.value

    def on_year_set(self, e):
        self.year = e.control.value

    def build(self):
        self.view = Container(
            content=Column(
                controls=[
                    StdBodyText(txt=self.label, color=self.label_color),
                    Row(
                        [
                            self.day_dropdown,
                            self.month_dropdown,
                            self.year_dropdown,
                        ],
                    ),
                ]
            ),
        )
        return self.view

    def set_date(self, date: Optional[datetime.date] = None):
        if date is None:
            return
        self.date = str(date.day)
        self.month = str(date.month)
        self.year = str(date.year)
        self.day_dropdown.update_value(self.date)
        self.month_dropdown.update_value(self.month)
        self.year_dropdown.update_value(self.year)

        self.update()

    def get_date(self) -> Optional[datetime.date]:
        """Return the selected timeframe."""
        if self.year is None or self.month is None or self.date is None:
            return None

        date = datetime.date(
            year=int(self.year),
            month=int(self.month),
            day=int(self.date),
        )
        return date


class AlertDisplayPopUp(DialogHandler):
    """Pop up used for displaying alerts"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        title: str,
        description: str,
        on_complete: Optional[Callable] = None,
        button_label: str = "Got it",
        is_error: bool = True,
    ):
        pop_up_height = 150
        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        StdHeading(
                            title=title,
                            size=fonts.HEADLINE_4_SIZE,
                        ),
                        Spacer(xs_space=True),
                        StdBodyText(
                            txt=description,
                            size=fonts.SUBTITLE_1_SIZE,
                            color=colors.ERROR_COLOR if is_error else None,
                        ),
                    ],
                ),
            ),
            actions=[
                StdPrimaryButton(
                    label=button_label, on_click=self.on_complete_btn_clicked
                ),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_complete_callback = on_complete

    def on_complete_btn_clicked(self, e):
        self.close_dialog()
        if self.on_complete_callback:
            self.on_complete_callback()


class ConfirmDisplayPopUp(DialogHandler):
    """Pop up used for displaying confirmation pop up"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        title: str,
        description: str,
        data_on_confirmed: any,
        on_proceed: Callable,
        on_cancel: Optional[Callable] = None,
        proceed_button_label: str = "Proceed",
        cancel_button_label: str = "Cancel",
    ):
        pop_up_height = 150
        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        StdHeading(
                            title=title,
                            size=fonts.HEADLINE_4_SIZE,
                        ),
                        Spacer(xs_space=True),
                        StdBodyText(
                            txt=description,
                            size=fonts.SUBTITLE_1_SIZE,
                        ),
                    ],
                ),
            ),
            actions=[
                StdSecondaryButton(
                    label=cancel_button_label, on_click=self.on_cancel_btn_clicked
                ),
                StdPrimaryButton(
                    label=proceed_button_label, on_click=self.on_proceed_btn_clicked
                ),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_proceed_callback = on_proceed
        self.on_cancel_callback = on_cancel
        self.data_on_confirmed = data_on_confirmed

    def on_cancel_btn_clicked(self, e):
        self.close_dialog()
        if self.on_cancel_callback:
            self.on_cancel_callback()

    def on_proceed_btn_clicked(self, e):
        self.close_dialog()
        self.on_proceed_callback(self.data_on_confirmed)


class StdPopUpMenuItem(PopupMenuItem):
    """Returns a customizable pop up menu item with standard styling"""

    def __init__(
        self,
        icon,
        txt,
        on_click,
        is_delete: bool = False,
    ):
        super().__init__(
            content=Row(
                [
                    Icon(
                        icon,
                        size=dimens.ICON_SIZE,
                        color=colors.ERROR_COLOR if is_delete else None,
                    ),
                    StdBodyText(
                        txt,
                        size=fonts.BUTTON_SIZE,
                        color=colors.ERROR_COLOR if is_delete else None,
                    ),
                ]
            ),
            on_click=on_click,
        )


class StdContextMenu(PopupMenuButton):
    """Returns a customizable pop up menu button with optional view, edit and delete menus"""

    def __init__(
        self,
        on_click_edit: Optional[Callable] = None,
        on_click_delete: Optional[Callable] = None,
        view_item_lbl="View Details",
        delete_item_lbl="Delete",
        edit_item_lbl="Edit",
        on_click_view: Optional[Callable] = None,
        prefix_menu_items: Optional[list[PopupMenuItem]] = None,
        suffix_menu_items: Optional[list[PopupMenuItem]] = None,
    ):

        items = []
        if prefix_menu_items:
            items.extend(prefix_menu_items)
        if on_click_view:
            items.append(
                StdPopUpMenuItem(
                    icons.VISIBILITY_OUTLINED, txt=view_item_lbl, on_click=on_click_view
                ),
            )
        if on_click_edit:
            items.append(
                StdPopUpMenuItem(
                    icons.EDIT_OUTLINED,
                    txt=edit_item_lbl,
                    on_click=on_click_edit,
                )
            )
        if on_click_delete:
            items.append(
                StdPopUpMenuItem(
                    icons.DELETE_OUTLINE,
                    txt=delete_item_lbl,
                    on_click=on_click_delete,
                    is_delete=True,
                )
            )
        if suffix_menu_items:
            items.extend(suffix_menu_items)
        super().__init__(items=items)


class StdStatusDisplay(Row):
    """Returns a text with a checked prefix icon"""

    def __init__(
        self,
        txt: str,
        is_done: bool,
    ):
        super().__init__(
            controls=[
                Icon(
                    icons.CHECK_CIRCLE_OUTLINE
                    if is_done
                    else icons.RADIO_BUTTON_UNCHECKED,
                    size=dimens.SM_ICON_SIZE,
                    color=colors.PRIMARY_COLOR if is_done else colors.GRAY_COLOR,
                ),
                StdBodyText(txt),
            ]
        )


class OrView(Row):
    """Returns a view representing ---- OR ----"""

    def __init__(
        self,
        show_lines: Optional[bool] = True,
        show: bool = True,
    ):

        super().__init__(
            visible=show,
            alignment=utils.SPACE_BETWEEN_ALIGNMENT
            if show_lines
            else utils.CENTER_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            controls=[
                Container(
                    height=2,
                    bgcolor=colors.GRAY_COLOR,
                    width=100,
                    alignment=alignment.center,
                    visible=show_lines,
                ),
                StdBodyText(
                    "OR", align=utils.TXT_ALIGN_CENTER, color=colors.GRAY_COLOR
                ),
                Container(
                    height=2,
                    bgcolor=colors.GRAY_COLOR,
                    width=100,
                    alignment=alignment.center,
                    visible=show_lines,
                ),
            ],
        )


@dataclass
class NavigationMenuItem:
    """defines a menu item used in navigation rails"""

    index: int
    label: str
    icon: str
    selected_icon: str
    destination: UserControl
    on_new_screen_route: Optional[str] = None
    on_new_intent: Optional[str] = None


class StdNavigationMenu(NavigationRail):
    """
    Returns a navigation menu for the application.

    :param title: Title of the navigation menu.
    :param on_change: Callable function to be called when the selected item in the menu changes.
    :param selected_index: The index of the selected item in the menu.
    :param destinations: List of destinations in the menu.
    :param menu_height: The height of the menu.
    :return: A NavigationRail widget containing the navigation menu.
    """

    def __init__(
        self,
        title: str,
        on_change,
        selected_index: Optional[int] = 0,
        destinations=[],
        menu_height: int = 300,
        width: int = int(dimens.MIN_WINDOW_WIDTH * 0.3),
        left_padding: int = dimens.SPACE_STD,
        top_margin: int = dimens.SPACE_STD,
    ):

        super().__init__(
            leading=Container(
                content=StdSubHeading(
                    subtitle=title,
                    align=utils.START_ALIGNMENT,
                    expand=True,
                    color=colors.GRAY_DARK_COLOR,
                ),
                expand=True,
                width=width,
                margin=margin.only(top=top_margin),
                padding=padding.only(left=left_padding),
            ),
            selected_index=selected_index,
            min_width=utils.COMPACT_RAIL_WIDTH,
            extended=True,
            height=menu_height,
            min_extended_width=width,
            destinations=destinations,
            on_change=on_change,
        )
