from typing import Optional, Callable


from loguru import logger

from flet import (
    Column,
    Container,
    Icon,
    IconButton,
    Row,
    Tab,
    TabBar,
    TabBarView,
    Tabs,
    Control,
    Icons,
    Margin,
    Padding,
)

from ..core import utils, views
from ..core.abstractions import TView, TViewParams
from ..core.intent_result import IntentResult

from ..core.utils import (
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from ..preferences.intent import PreferencesIntent
from ..preferences.model import Preferences
from ..res import dimens
from ..res.dimens import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_MD,
    SPACE_STD,
    SPACE_XL,
    SPACE_XS,
)
from ..res.theme import THEME_MODES


class PreferencesScreen(TView, Row):
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
        self.pop_up_handler = None

    def set_available_currencies(self):
        self.currencies = [
            abbreviation for (name, abbreviation, symbol) in utils.get_currencies()
        ]
        self.currencies_control.update_dropdown_items(self.currencies)

    def on_currency_selected(self, e):
        if not self.preferences:
            return
        self.preferences.default_currency = e.control.value

    def refresh_preferences_items(self):
        if self.preferences is None:
            return
        self.theme_control.update_value(self.preferences.theme_mode)
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

    def on_reset_app_clicked(self, e):
        """Ask user to confirm this action"""
        if self.pop_up_handler:
            # Close any existing dialog
            self.pop_up_handler.close_dialog()
        # Add a confirmation dialog
        self.pop_up_handler = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to reset the app?\nThis will clear all your data.",
            on_proceed=self.on_reset_app_confirmed,
            proceed_button_label="Reset and Clear Data",
        )
        self.pop_up_handler.open_dialog()

    def on_reset_app_confirmed(
        self,
    ):
        """Reset the app to default state"""
        logger.warning("Resetting the app to default state")
        logger.warning("Clearning preferences")
        result: IntentResult[None] = self.intent.clear_preferences()
        assert result.was_intent_successful
        logger.warning("Clearning database")
        logger.warning("Quitting app after reset. Please restart.")
        self.on_reset_app_callback()

    def _make_tab_header(self, label, icon):
        return Tab(
            label=Column(
                alignment=CENTER_ALIGNMENT,
                horizontal_alignment=CENTER_ALIGNMENT,
                controls=[
                    Icon(icon, size=dimens.ICON_SIZE),
                    views.Spacer(sm_space=True),
                    views.TBodyText(txt=label),
                    views.Spacer(md_space=True),
                ],
            ),
        )

    def _make_tab_content(self, content_controls):
        return Container(
            content=Column(controls=content_controls),
            padding=Padding.symmetric(vertical=SPACE_XL),
            margin=Margin.symmetric(vertical=SPACE_MD),
        )

    def build(self):
        side_bar_width = int(MIN_WINDOW_WIDTH * 0.3)
        self.body_width = int(MIN_WINDOW_WIDTH * 0.7)
        self.loading_indicator = views.TProgressBar()
        self.sideBar = Container(
            padding=Padding.all(SPACE_STD),
            width=side_bar_width,
            content=Column(
                controls=[
                    IconButton(
                        icon=Icons.KEYBOARD_ARROW_LEFT,
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
            icon=Icons.RESTART_ALT_OUTLINED,
            on_click=self.on_reset_app_clicked,
            tooltip="Warning: This will reset the app to default state and delete all data. You will have to restart the app.",
        )

        self.tabs = Tabs(
            selected_index=0,
            animation_duration=300,
            length=2,
            width=self.body_width - SPACE_MD,
            height=MIN_WINDOW_HEIGHT,
            content=Column(
                expand=True,
                controls=[
                    TabBar(
                        tabs=[
                            self._make_tab_header("General", Icons.SETTINGS_OUTLINED),
                            self._make_tab_header("Locale", Icons.LANGUAGE_OUTLINED),
                        ],
                    ),
                    TabBarView(
                        expand=True,
                        controls=[
                            self._make_tab_content(
                                [
                                    self.theme_control,
                                    views.Spacer(lg_space=True),
                                    self.reset_button,
                                ]
                            ),
                            self._make_tab_content(
                                [
                                    self.languages_control,
                                    self.currencies_control,
                                ]
                            ),
                        ],
                    ),
                ],
            ),
        )
        self.body = Container(
            padding=Padding.all(SPACE_MD),
            width=self.body_width,
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(
                                Icons.SETTINGS_SUGGEST_OUTLINED,
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
        self.spacing = SPACE_XS
        self.run_spacing = SPACE_MD
        self.alignment = START_ALIGNMENT
        self.vertical_alignment = START_ALIGNMENT
        self.expand = True
        self.controls = [self.sideBar, self.body]

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
