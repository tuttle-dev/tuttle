from typing import Optional

from flet import (
    Column,
    Container,
    Icon,
    IconButton,
    Row,
    Tab,
    Tabs,
    Text,
    UserControl,
    dropdown,
    icons,
    margin,
    padding,
)

from core import utils, views
from core.abstractions import TuttleView, TuttleViewParams
from core.intent_result import IntentResult
from core.views import (
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
    get_dropdown,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    smSpace,
    update_dropdown_items,
)
from preferences.intent import PreferencesIntent
from preferences.model import Preferences
from res.dimens import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_MD,
    SPACE_STD,
    SPACE_XL,
    SPACE_XS,
)
from res.theme import THEME_MODES
from res import dimens
from .model import CloudAccounts


class PreferencesScreen(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
        on_theme_changed,
    ):
        super().__init__(params=params)
        self.intent = PreferencesIntent(client_storage=params.local_storage)
        self.on_theme_changed_callback = on_theme_changed
        self.preferences: Optional[Preferences] = None
        self.currencies = []

    def set_available_currencies(self):
        self.currencies = [
            abbreviation for (name, abbreviation, symbol) in utils.get_currencies()
        ]
        update_dropdown_items(self.currencies_control, self.currencies)

    def on_currency_selected(self, e):
        if not self.preferences:
            return
        self.preferences.default_currency = e.control.value

    def on_cloud_account_id_changed(self, e):
        if not self.preferences:
            return
        self.preferences.cloud_acc_id = e.control.value

    def on_cloud_provider_selected(self, e):
        if not self.preferences:
            return
        self.preferences.cloud_acc_provider = e.control.value

    def refresh_preferences_items(self):
        if self.preferences is None:
            return
        self.theme_control.value = self.preferences.theme_mode
        self.cloud_provider_control.value = self.preferences.cloud_acc_provider
        self.cloud_account_id_control.value = self.preferences.cloud_acc_id
        self.currencies_control.value = self.preferences.default_currency
        self.languages_control.value = self.preferences.language

    def on_theme_changed(self, e):
        if not self.preferences:
            return
        selected = e.control.value
        if selected:
            self.preferences.theme_mode = selected
            self.on_theme_changed_callback(selected)
            self.update_self()

    def on_window_resized_listener(self, width, height):
        super().on_window_resized_listener(width, height)
        self.body_width = width - self.sideBar.width - SPACE_MD * 2
        self.body.width = self.body_width
        self.tabs.width = self.body_width - SPACE_MD
        self.tabs.height = height - SPACE_MD * 2
        self.update_self()

    def on_language_selected(self, e):
        if not self.preferences:
            return
        self.preferences.language = e.control.value

    def get_tab_item(self, label, icon, content_controls):
        return Tab(
            tab_content=Column(
                alignment=CENTER_ALIGNMENT,
                horizontal_alignment=CENTER_ALIGNMENT,
                controls=[
                    Icon(
                        icon,
                        size=dimens.ICON_SIZE,
                    ),
                    smSpace,
                    views.get_body_txt(txt=label),
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
                        icon_size=dimens.ICON_SIZE,
                        on_click=self.on_navigate_back,
                    ),
                ]
            ),
        )

        self.theme_control = get_dropdown(
            items=[mode.value for mode in THEME_MODES],
            on_change=self.on_theme_changed,
            label="Appearance",
            hint="",
        )
        self.cloud_provider_control = get_dropdown(
            label="Cloud Provider",
            on_change=self.on_cloud_provider_selected,
            items=[item.value for item in CloudAccounts],
        )
        self.cloud_account_id_control = get_std_txt_field(
            label="Cloud Account Name",
            hint="Your cloud account name",
            on_change=self.on_cloud_account_id_changed,
        )
        self.currencies_control = get_dropdown(
            label="Default Currency",
            on_change=self.on_currency_selected,
            items=self.currencies,
        )
        self.languages_control = get_dropdown(
            label="Language",
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
                    "Cloud",
                    icons.CLOUD_OUTLINED,
                    [
                        self.cloud_provider_control,
                        self.cloud_account_id_control,
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
                            Icon(
                                icons.SETTINGS_SUGGEST_OUTLINED,
                                size=dimens.ICON_SIZE,
                            ),
                            views.get_heading(
                                title="Preferences",
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
        self.mounted = True
        self.loading_indicator.visible = True
        self.update_self()
        self.set_available_currencies()
        result: IntentResult = self.intent.get_preferences()
        if result.was_intent_successful:
            self.preferences = result.data
            self.refresh_preferences_items()
        else:
            self.show_snack(result.error_msg, True)

        self.loading_indicator.visible = False
        self.update_self()

    def will_unmount(self):
        # save changes
        if self.preferences:
            self.intent.save_preferences(self.preferences)
        self.mounted = False
