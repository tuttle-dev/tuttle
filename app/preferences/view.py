from typing import Callable, Optional

from flet import (
    Column,
    Container,
    Icon,
    icons,
    Text,
    IconButton,
    Row,
    UserControl,
    padding,
)
from core.models import IntentResult
from core.abstractions import TuttleView
from core.views import (
    get_dropdown,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    START_ALIGNMENT,
)
from preferences.intent import PreferencesIntent
from preferences.model import Preferences
from res.dimens import SPACE_MD, SPACE_STD, SPACE_XS, MIN_WINDOW_WIDTH
from res.theme import THEME_MODES, get_theme_mode_from_value


class PreferencesScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
        on_theme_changed,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
        )
        self.intent_handler = PreferencesIntent(client_storage=local_storage)
        self.on_theme_changed_callback = on_theme_changed
        self.preferences: Optional[Preferences] = None

    def on_icloud_acc_changed(self, e):
        self.preferences.icloud_acc_id = e.control.value
        self.intent_handler.set_preferences(self.preferences)

    def refresh_preferences(self):
        if self.preferences is None:
            return
        self.theme_control.value = self.preferences.theme_mode.value
        self.icloud_acc_id_control.value = self.preferences.icloud_acc_id

    def on_theme_changed(self, e):
        if not self.preferences:
            return
        selected = e.control.value
        if selected:
            mode = get_theme_mode_from_value(selected)
            self.preferences.theme_mode = mode
            self.theme_control.value = mode.value
            self.on_theme_changed_callback(mode)
            if self.mounted:
                self.update()

    def build(self):

        self.loading_indicator = horizontal_progress
        self.sideBar = Container(
            padding=padding.all(SPACE_STD),
            width=int(MIN_WINDOW_WIDTH * 0.3),
            content=Column(
                controls=[
                    IconButton(
                        icon=icons.KEYBOARD_ARROW_LEFT,
                        on_click=self.on_navigate_back,
                    ),
                ]
            ),
        )

        self.theme_control = get_dropdown(
            items=[mode.value for mode in THEME_MODES],
            on_change=self.on_theme_changed,
            lbl="Appearance",
            hint="",
        )
        self.icloud_acc_id_control = get_std_txt_field(
            lbl="ICloud Account Id",
            hint="to load time tracking info from calendar",
            on_change=self.on_icloud_acc_changed,
        )
        self.body = Container(
            padding=padding.all(SPACE_MD),
            width=int(MIN_WINDOW_WIDTH * 0.7),
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(icons.SETTINGS_SUGGEST_OUTLINED),
                            Text(
                                "Preferences",
                            ),
                        ],
                    ),
                    self.loading_indicator,
                    mdSpace,
                    self.theme_control,
                    mdSpace,
                    self.icloud_acc_id_control,
                ],
            ),
        )
        page_view = Row(
            [self.sideBar, self.body],
            spacing=SPACE_XS,
            run_spacing=SPACE_MD,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        return page_view

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.update()
            result: IntentResult = self.intent_handler.get_preferences()
            if result.was_intent_successful:
                self.preferences = result.data
                self.refresh_preferences()
            self.loading_indicator.visible = False
            self.update()
        except Exception as e:
            # log
            print(f"Exception raised @preferences_screen.did_mount {e}")

    def will_unmount(self):
        # save changes
        if self.preferences:
            self.intent_handler.set_preferences(self.preferences)
        self.mounted = False
