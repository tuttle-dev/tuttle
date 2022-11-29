import flet as ft
from flet import Page, AlertDialog, SnackBar, Text

from core.models import RouteView
from typing import Optional, Callable
from res.strings import (
    APP_NAME,
)
from res.fonts import APP_FONTS, HEADLINE_4_SIZE, HEADLINE_FONT
from res.theme import THEME_MODES, APP_THEME
from res.dimens import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from core.local_storage_impl import ClientStorageImpl
from res.colors import BLACK_COLOR_ALT, WHITE_COLOR, ERROR_COLOR, PRIMARY_COLOR
from core.constants_and_enums import AlertDialogControls
from routing import TuttleRoutes


class TuttleApp:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.page.title = APP_NAME
        self.page.fonts = APP_FONTS
        self.page.theme = APP_THEME
        self.page.window_min_width = MIN_WINDOW_WIDTH
        self.page.window_min_height = MIN_WINDOW_HEIGHT
        self.local_storage = ClientStorageImpl(page=self.page)
        self.page.on_route_change = self.on_route_change
        self.page.on_view_pop = self.on_view_pop
        self.routeParser = TuttleRoutes(
            on_change_route=self.change_route,
            local_storage=self.local_storage,
            dialog_controller=self.control_alert_dialog,
            on_navigate_back=self.on_view_pop,
            show_snack=self.show_snack,
            on_theme_changed=self.on_theme_mode_changed,
        )
        self.currentRouteView: Optional[RouteView] = None
        self.page.on_resize = self.page_resize

    def page_resize(self, e):
        if self.currentRouteView:
            self.currentRouteView.on_window_resized(
                self.page.window_width, self.page.window_height
            )

    def on_theme_mode_changed(self, theme_mode: THEME_MODES):
        """callback function used by views for changing app theme mode"""
        self.page.theme_mode = theme_mode.value
        self.page.update()

    def show_snack(
        self,
        message: str,
        is_error: bool = True,
        action_label: Optional[str] = None,
        action_callback: Optional[Callable] = None,
    ):
        """callback function used by views to display a snack bar message"""
        if self.page.snack_bar and self.page.snack_bar.open:
            self.page.snack_bar.open = False
            self.page.update()
        self.page.snack_bar = SnackBar(
            Text(
                message,
                size=HEADLINE_4_SIZE,
                color=ERROR_COLOR if is_error else WHITE_COLOR,
                font_family=HEADLINE_FONT,
            ),
            bgcolor=WHITE_COLOR if is_error else BLACK_COLOR_ALT,
            action=action_label,
            action_color=PRIMARY_COLOR,
            on_action=action_callback,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def control_alert_dialog(
        self,
        dialog: Optional[AlertDialog] = None,
        control: AlertDialogControls = AlertDialogControls.CLOSE,
    ):
        """handles adding, opening and closing of page alert dialogs"""
        if control.value == AlertDialogControls.ADD_AND_OPEN.value:
            if self.page.dialog:
                # make sure no two dialogs attempt to open at once
                self.page.dialog.open = False
            if dialog:
                self.page.dialog = dialog
                dialog.open = True

        if control.value == AlertDialogControls.CLOSE.value:
            if self.page.dialog:
                dialog.open = False
        self.page.update()

    def change_route(self, to_route: str, data: Optional[any] = None):
        """navigates to a new route"""
        newRoute = to_route if data is None else f"{to_route}/{data}"

        self.page.go(newRoute)

    def on_view_pop(self, view):
        """invoked on back pressed"""
        if len(self.page.views) == 1:
            return
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

    def on_route_change(self, route):
        """auto invoked when the route changes

        parses the new destination route
        then appends the new page to page views
        the splash view must always be in view
        """
        # insert the new view on top
        routeView = self.routeParser.parse_route(pageRoute=route.route)
        if not routeView.keep_back_stack:
            """clear previous views"""
            self.page.views.clear()
        self.page.views.append(routeView.view)
        self.currentRouteView = routeView
        self.page.update()
        self.currentRouteView.on_window_resized(
            self.page.window_width, self.page.window_height
        )

    def build(self):
        self.page.go(self.page.route)


def main(page: Page):
    """Entry point of the app"""
    app = TuttleApp(page)
    app.build()


ft.app(target=main, assets_dir="assets")
