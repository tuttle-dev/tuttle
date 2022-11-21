import flet as ft
from flet import Page, AlertDialog, SnackBar, Text

from core.local_cache_impl import LocalCacheImpl
from res.strings import APP_NAME
from res.theme import APP_FONTS, APP_THEME, APP_THEME_MODE
from routes import TuttleRoutes
from res.dimens import MIN_WINDOW_WIDTH
import typing
from core.views.alert_dialog_controls import AlertDialogControls


def main(page: Page):
    """Entry point of the app"""
    page.title = APP_NAME
    page.fonts = APP_FONTS
    page.theme_mode = APP_THEME_MODE
    page.theme = APP_THEME
    page.window_min_width = MIN_WINDOW_WIDTH
    localCacheHandler = LocalCacheImpl(page=page)

    def change_route(toRoute: str, data: any):
        """Navigates to a new route

        passes data to the destination if provided
        """
        page.go(toRoute)

    def control_alert_dialog(
        dialog: typing.Optional[AlertDialog],
        control: AlertDialogControls,
    ):
        """handles adding, opening and closing of page alert dialogs"""
        if control.value == AlertDialogControls.ADD_AND_OPEN.value:
            if page.dialog:
                # make sure no two dialogs attempt to open at once
                page.dialog.open = False
            if dialog:
                page.dialog = dialog
                dialog.open = True

        if control.value == AlertDialogControls.CLOSE.value:
            if page.dialog:
                dialog.open = False
        page.update()

    def get_route_view(route: str):
        """helper function that parses a route to route view"""
        routeParser = TuttleRoutes(
            onChangeRouteCallback=change_route,
            localCacheHandler=localCacheHandler,
            dialogController=control_alert_dialog,
            onNavigateBack=on_view_pop,
        )
        return routeParser.parse_route(pageRoute=route)

    def on_route_change(route):
        """auto invoked when the route changes

        parses the new destination route
        then appends the new page to page views
        the splash view must always be in view
        """
        # insert the new view on top
        routeView = get_route_view(page.route)
        if not routeView.keepBackStack:
            page.views.clear()
        page.views.append(routeView.view)
        page.update()

    def on_view_pop(view):
        """invoked on back pressed"""
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    page.go(page.route)


ft.app(target=main, assets_dir="assets")
