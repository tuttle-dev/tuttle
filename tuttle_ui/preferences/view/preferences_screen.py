import typing
from typing import Callable, Optional
from flet import (
    Column,
    Container,
    Card,
    Row,
    Text,
    UserControl,
    icons,
    Icon,
    IconButton,
    padding,
    TextButton,
)
from res.theme import THEME_MODES, get_theme_mode_from_value
from core.views.progress_bars import horizontalProgressBar
from core.abstractions import LocalCache, TuttleView
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
)
from core.views.selectors import get_dropdown
from core.views.spacers import mdSpace
from res import spacing, fonts, colors
from res.dimens import MIN_WINDOW_WIDTH
from res.strings import PREFERENCES
from preferences.preferences_intent_impl import PreferencesIntentImpl
from preferences.preferences_model import Preferences


class PreferencesScreen(TuttleView, UserControl):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onNavigateBack: Callable,
        showSnackCallback: Callable[[str, bool], None],
        onThemeChangedCallback: Callable,
    ):
        intentHandler = PreferencesIntentImpl(cache=localCacheHandler)
        super().__init__(
            keepBackStack=True,
            horizontalAlignmentInParent=CENTER_ALIGNMENT,
            onNavigateBack=onNavigateBack,
            intentHandler=intentHandler,
            showSnackCallback=showSnackCallback,
        )
        self.intentHandler = intentHandler
        self.onThemeChangedCallback = onThemeChangedCallback
        self.preferences: Optional[Preferences] = None

    def refresh_preferences(self):
        if self.preferences is None:
            return
        self.themeControl.value = self.preferences.theme_mode.value

    def on_theme_changed(self, e):
        selected = e.control.value
        if selected:
            mode = get_theme_mode_from_value(selected)
            self.preferences.theme_mode = mode
            self.themeControl.value = mode.value
            self.onThemeChangedCallback(mode)
        self.update()

    def build(self):

        self.loadingIndicator = horizontalProgressBar
        self.sideBar = Container(
            padding=padding.all(spacing.SPACE_STD),
            width=int(MIN_WINDOW_WIDTH * 0.3),
            content=Column(
                controls=[
                    IconButton(
                        icon=icons.KEYBOARD_ARROW_LEFT,
                        on_click=self.onNavigateBack,
                    ),
                ]
            ),
        )

        self.themeControl = get_dropdown(
            items=[mode.value for mode in THEME_MODES],
            onChange=self.on_theme_changed,
            lbl="Appearance",
            hint="",
        )

        self.currencyControl = get_dropdown(
            items=["USD ($)", "EUR (€)", "GBP (£)"],
            onChange=lambda e: None,
            lbl="Default currency",
            hint="",
        )
        self.body = Container(
            padding=padding.all(spacing.SPACE_MD),
            width=int(MIN_WINDOW_WIDTH * 0.7),
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(icons.SETTINGS_SUGGEST_OUTLINED),
                            Text(
                                PREFERENCES,
                            ),
                        ],
                    ),
                    self.loadingIndicator,
                    mdSpace,
                    self.themeControl,
                    mdSpace,
                    self.currencyControl,
                ],
            ),
        )
        page_view = Row(
            [self.sideBar, self.body],
            spacing=spacing.SPACE_XS,
            run_spacing=spacing.SPACE_MD,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        page_view.padding = spacing.SPACE_STD
        return page_view

    def did_mount(self):
        self.loadingIndicator.visible = True
        self.update()
        result = self.intentHandler.get_preferences()
        if result.wasIntentSuccessful:
            self.preferences = result.data
            self.refresh_preferences()
        self.loadingIndicator.visible = False
        self.update()

    def will_unmount(self):
        # save changes
        if self.preferences:
            self.intentHandler.set_preferences(self.preferences)
        return super().will_unmount()
