from typing import Optional
import pycountry
from flet import (
    Tabs,
    Tab,
    Column,
    Container,
    Icon,
    icons,
    Text,
    IconButton,
    Row,
    UserControl,
    padding,
    margin,
)
from core.models import IntentResult
from core.abstractions import TuttleView
from core.views import (
    update_dropdown_items,
    get_dropdown,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    smSpace,
    START_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from preferences.intent import PreferencesIntent
from preferences.model import Preferences
from res.dimens import (
    SPACE_XL,
    SPACE_MD,
    SPACE_STD,
    SPACE_XS,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)
from res.theme import THEME_MODES
from core.abstractions import TuttleViewParams


class PreferencesScreen(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
        on_theme_changed,
    ):
        super().__init__(params=params)
        self.intent_handler = PreferencesIntent(client_storage=params.local_storage)
        self.on_theme_changed_callback = on_theme_changed
        self.preferences: Optional[Preferences] = None
        self.currencies = []

    def set_available_currencies(self):
        currency_list = list(pycountry.currencies)
        for currency in currency_list:
            self.currencies.append(currency.name)
        self.currencies.sort()
        update_dropdown_items(self.currencies_control, self.currencies)

    def on_currency_selected(self, e):
        if not self.preferences:
            return
        self.preferences.default_currency = e.control.value

    def on_icloud_acc_changed(self, e):
        if not self.preferences:
            return
        self.preferences.icloud_acc_id = e.control.value

    def refresh_preferences_items(self):
        if self.preferences is None:
            return
        self.theme_control.value = self.preferences.theme_mode
        self.icloud_acc_id_control.value = self.preferences.icloud_acc_id
        self.currencies_control.value = self.preferences.default_currency

    def on_theme_changed(self, e):
        if not self.preferences:
            return
        selected = e.control.value
        if selected:
            self.preferences.theme_mode = selected
            self.on_theme_changed_callback(selected)
            if self.mounted:
                self.update()

    def on_window_resized(self, width, height):
        super().on_window_resized(width, height)
        self.body_width = width - self.sideBar.width - SPACE_MD * 2
        self.body.width = self.body_width
        self.tabs.width = self.body_width - SPACE_MD
        self.tabs.height = height - SPACE_MD * 2
        if self.mounted:
            self.update()

    def on_language_selected(self, e):
        if not self.preferences:
            return
        self.preferences.language = e.control.value

    def get_tab_item(self, lbl, icon, content_controls):
        return Tab(
            tab_content=Column(
                alignment=CENTER_ALIGNMENT,
                horizontal_alignment=CENTER_ALIGNMENT,
                controls=[
                    Icon(icon, size=24),
                    smSpace,
                    Text(lbl),
                    mdSpace,
                ],
            ),
            content=Container(
                content=Column(controls=content_controls),
                padding=padding.symmetric(vertical=SPACE_XL),
                margin=margin.symmetric(vertical=SPACE_MD),
            ),
        )

    def build(self):
        side_bar_width = int(MIN_WINDOW_WIDTH * 0.3)
        self.body_width = int(MIN_WINDOW_WIDTH * 0.7)
        self.loading_indicator = horizontal_progress
        self.sideBar = Container(
            padding=padding.all(SPACE_STD),
            width=side_bar_width,
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
        self.currencies_control = get_dropdown(
            lbl="Default Currency",
            on_change=self.on_currency_selected,
            items=self.currencies,
        )
        self.languages_control = get_dropdown(
            lbl="Language",
            on_change=self.on_language_selected,
            items=[
                "English",
            ],
        )
        self.tabs = Tabs(
            selected_index=0,
            animation_duration=300,
            width=self.body_width - SPACE_MD,
            height=MIN_WINDOW_HEIGHT,
            tabs=[
                self.get_tab_item(
                    "General",
                    icons.SETTINGS_OUTLINED,
                    [
                        self.theme_control,
                    ],
                ),
                self.get_tab_item(
                    "Accounts",
                    icons.CLOUD_OUTLINED,
                    [
                        self.icloud_acc_id_control,
                    ],
                ),
                self.get_tab_item(
                    "Locale",
                    icons.LANGUAGE_OUTLINED,
                    [
                        self.languages_control,
                        self.currencies_control,
                    ],
                ),
            ],
        )
        self.body = Container(
            padding=padding.all(SPACE_MD),
            width=self.body_width,
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
                    self.tabs,
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
            self.set_available_currencies()
            result: IntentResult = self.intent_handler.get_preferences()
            if result.was_intent_successful:
                self.preferences = result.data
                self.refresh_preferences_items()
            else:
                self.show_snack(result.error_msg, True)

            self.loading_indicator.visible = False
            self.update()
        except Exception as e:
            # log
            print(f"Exception raised @preferences_screen.did_mount {e}")

    def will_unmount(self):
        # save changes
        if self.preferences:
            self.intent_handler.save_preferences(self.preferences)
        self.mounted = False
