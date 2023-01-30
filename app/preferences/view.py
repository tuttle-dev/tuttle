from typing import Optional, Callable


from loguru import logger

from flet import (
    Column,
    Container,
    Icon,
    IconButton,
    Row,
    Tab,
    Tabs,
    UserControl,
    icons,
    margin,
    padding,
)

from core import utils, views
from core.abstractions import TView, TViewParams
from core.intent_result import IntentResult

from core.utils import (
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from preferences.intent import PreferencesIntent
from preferences.model import Preferences
from res import dimens
from res.dimens import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_MD,
    SPACE_STD,
    SPACE_XL,
    SPACE_XS,
)
from res.theme import THEME_MODES

from tuttle.cloud import CloudProvider


class PreferencesScreen(TView, UserControl):
    def __init__(
        self,
        params: TViewParams,
        on_theme_changed_callback: Callable,
        on_reset_app_callback: Callable,
    ):
        super().__init__(params=params)
        self.intent = PreferencesIntent(client_storage=params.client_storage)
        self.on_theme_changed_callback = on_theme_changed_callback
        self.on_reset_app_callback = on_reset_app_callback
        self.preferences: Optional[Preferences] = None
        self.currencies = []

    def set_available_currencies(self):
        self.currencies = [
            abbreviation for (name, abbreviation, symbol) in utils.get_currencies()
        ]
        self.currencies_control.update_dropdown_items(self.currencies)

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
        self.theme_control.update_value(self.preferences.theme_mode)
        self.cloud_provider_control.update_value(self.preferences.cloud_acc_provider)
        self.cloud_account_id_control.value = self.preferences.cloud_acc_id
        self.currencies_control.update_value(self.preferences.default_currency)
        self.languages_control.update_value(self.preferences.language)

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

    def on_reset_app(self, e):
        logger.warning("Resetting the app to default state")
        logger.warning("Clearning preferences")
        result: IntentResult[None] = self.intent.clear_preferences()
        assert result.was_intent_successful
        logger.warning("Clearning database")
        logger.warning("Quitting app after reset. Please restart.")
        self.on_reset_app_callback()

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
                    views.Spacer(sm_space=True),
                    views.TBodyText(txt=label),
                    views.Spacer(md_space=True),
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
        self.loading_indicator = views.TProgressBar()
        self.sideBar = Container(
            padding=padding.all(SPACE_STD),
            width=side_bar_width,
            content=Column(
                controls=[
                    IconButton(
                        icon=icons.KEYBOARD_ARROW_LEFT,
                        icon_size=dimens.ICON_SIZE,
                        on_click=self.navigate_back,
                    ),
                ]
            ),
        )

        self.theme_control = views.TDropDown(
            items=[mode.value for mode in THEME_MODES],
            on_change=self.on_theme_changed,
            label="Appearance",
            hint="",
        )
        self.cloud_provider_control = views.TDropDown(
            label="Cloud Provider",
            on_change=self.on_cloud_provider_selected,
            items=[item.value for item in CloudProvider],
        )
        self.cloud_account_id_control = views.TTextField(
            label="Cloud Account Name",
            hint="Your cloud account name",
            on_change=self.on_cloud_account_id_changed,
        )
        self.currencies_control = views.TDropDown(
            label="Default Currency",
            on_change=self.on_currency_selected,
            items=self.currencies,
        )
        self.languages_control = views.TDropDown(
            label="Language",
            on_change=self.on_language_selected,
            items=[
                "English",
            ],
        )

        # a reset button for the app with a warning sign, warning color and a confirmation dialog
        self.reset_button = views.TDangerButton(
            label="Reset App and Quit",
            icon=icons.RESTART_ALT_OUTLINED,
            on_click=self.on_reset_app,
            tooltip="Warning: This will reset the app to default state and delete all data. You will have to restart the app.",
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
                        views.Spacer(lg_space=True),
                        self.reset_button,
                    ],
                ),
                self.get_tab_item(
                    "Cloud",
                    icons.CLOUD_OUTLINED,
                    [
                        views.TBodyText(
                            txt="Setting up your cloud account will enable you to import time tracking data from your cloud calendar.",
                        ),
                        views.Spacer(sm_space=True),
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
                            views.THeading(
                                title="Preferences",
                            ),
                        ],
                    ),
                    self.loading_indicator,
                    views.Spacer(md_space=True),
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
