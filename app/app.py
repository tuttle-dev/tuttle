import re
from typing import Callable, Optional

from loguru import logger

import flet
from flet import (
    Page,
    FilePickerUploadFile,
    AlertDialog,
    SnackBar,
    TemplateRoute,
    Text,
    View,
)

import demo
from auth.view import ProfileScreen, SplashScreen
from contracts.view import (
    ContractEditorScreen,
    CreateContractScreen,
    ViewContractScreen,
)
from core.abstractions import TuttleView
from core.constants_and_enums import AlertDialogControls
from core.local_storage_impl import ClientStorageImpl
from core.models import RouteView
from error_views.page_not_found_screen import Error404Screen
from home.view import HomeScreen
from preferences.view import PreferencesScreen
from projects.view import CreateProjectScreen, EditProjectScreen, ViewProjectScreen
from res.colors import BLACK_COLOR_ALT, ERROR_COLOR, PRIMARY_COLOR, WHITE_COLOR
from res.dimens import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH
from res.fonts import APP_FONTS, HEADLINE_4_SIZE, HEADLINE_FONT
from res.theme import APP_THEME, THEME_MODES
from res.utils import (
    CONTRACT_CREATOR_SCREEN_ROUTE,
    CONTRACT_DETAILS_SCREEN_ROUTE,
    CONTRACT_EDITOR_SCREEN_ROUTE,
    HOME_SCREEN_ROUTE,
    PREFERENCES_SCREEN_ROUTE,
    PROFILE_SCREEN_ROUTE,
    PROJECT_CREATOR_SCREEN_ROUTE,
    PROJECT_DETAILS_SCREEN_ROUTE,
    PROJECT_EDITOR_SCREEN_ROUTE,
    SPLASH_SCREEN_ROUTE,
)


class TuttleApp:
    """The main application class"""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.page.title = "Tuttle"
        self.page.fonts = APP_FONTS
        self.page.theme = APP_THEME
        self.page.theme_mode = THEME_MODES.dark.value
        self.page.window_min_width = MIN_WINDOW_WIDTH
        self.page.window_min_height = MIN_WINDOW_HEIGHT
        self.file_picker = flet.FilePicker()
        self.page.overlay.append(self.file_picker)

        """holds the RouteView object associated with a route
        used in on route change"""
        self.route_to_route_view_cache = {}

        self.local_storage = ClientStorageImpl(page=self.page)
        self.page.on_route_change = self.on_route_change
        self.page.on_view_pop = self.on_view_pop
        self.routeParser = TuttleRoutes(self)
        self.current_route_view: Optional[RouteView] = None
        self.page.on_resize = self.page_resize

    def page_resize(self, e):
        if self.current_route_view:
            self.current_route_view.on_window_resized(
                self.page.window_width, self.page.window_height
            )

    def pick_file_callback(
        self,
        on_file_picker_result,
        on_upload_progress,
        allowed_extensions,
        dialog_title,
        file_type,
    ):
        # used by views to request a file upload
        self.file_picker.on_result = on_file_picker_result
        self.file_picker.on_upload = on_upload_progress
        self.file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=allowed_extensions,
            dialog_title=dialog_title,
            file_type=file_type,
        )

    def upload_file_callback(self, file):
        try:
            upload_item = FilePickerUploadFile(
                file.name,
                upload_url=self.page.get_upload_url(file.name, 600),
            )
            self.file_picker.upload([upload_item])
        except Exception as e:
            print(f"Exception @app.upload_file_callback raised during file upload {e}")

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

    def on_view_pop(self, view: Optional[any] = None):
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
        """

        # if route is already in stack, get it's view
        # this happens when the user presses back
        view_for_route = None
        for view in self.page.views:
            if view.route == route.route:
                view_for_route = view
                break

        # get a new view if no view found in stack
        if not view_for_route:
            route_view_wrapper = self.routeParser.parse_route(pageRoute=route.route)
            if not route_view_wrapper.keep_back_stack:
                """clear previous views"""
                self.route_to_route_view_cache.clear()
                self.page.views.clear()
            view_for_route = route_view_wrapper.view
            self.route_to_route_view_cache[route.route] = route_view_wrapper
            self.page.views.append(view_for_route)

        self.current_route_view: RouteView = self.route_to_route_view_cache[route.route]
        self.page.update()
        self.current_route_view.on_window_resized(
            self.page.window_width, self.page.window_height
        )

    def build(self):
        self.page.go(self.page.route)


class TuttleRoutes:
    """Utility class for parsing of routes to destination views"""

    def __init__(self, app: TuttleApp):
        self.app = app

    def get_page_route_view(
        self,
        routeName: str,
        view: TuttleView,
    ) -> RouteView:
        """Constructs the view with a given route"""

        view_container = View(
            padding=0,
            spacing=0,
            route=routeName,
            scroll=view.page_scroll_type,
            controls=[view],
            vertical_alignment=view.vertical_alignment_in_parent,
            horizontal_alignment=view.horizontal_alignment_in_parent,
        )

        return RouteView(
            view=view_container,
            on_window_resized=view.on_window_resized,
            keep_back_stack=view.keep_back_stack,
        )

    def parse_route(self, pageRoute: str):
        """parses a given route path and returns it's view"""

        routePath = TemplateRoute(pageRoute)
        screen = None
        if routePath.match(SPLASH_SCREEN_ROUTE):
            screen = SplashScreen(
                # TODO: pass app directly?
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(HOME_SCREEN_ROUTE):
            screen = HomeScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
                upload_file_callback=self.app.upload_file_callback,
                pick_file_callback=self.app.pick_file_callback,
            )
        elif routePath.match(PROFILE_SCREEN_ROUTE):
            screen = ProfileScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(CONTRACT_CREATOR_SCREEN_ROUTE):
            screen = CreateContractScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(CONTRACT_DETAILS_SCREEN_ROUTE):
            screen = ViewContractScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(CONTRACT_EDITOR_SCREEN_ROUTE):
            screen = ContractEditorScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(PREFERENCES_SCREEN_ROUTE):
            screen = PreferencesScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                on_theme_changed=self.app.on_theme_changed,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(PROJECT_CREATOR_SCREEN_ROUTE):
            screen = CreateProjectScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(PROJECT_DETAILS_SCREEN_ROUTE):
            screen = ViewProjectScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        elif routePath.match(PROJECT_EDITOR_SCREEN_ROUTE):
            screen = EditProjectScreen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )
        else:
            screen = Error404Screen(
                navigate_to_route=self.app.change_route,
                show_snack=self.app.show_snack,
                dialog_controller=self.app.control_alert_dialog,
                on_navigate_back=self.app.on_view_pop,
                local_storage=self.app.local_storage,
            )

        return self.get_page_route_view(routePath.route, view=screen)


def install_demo_data():
    try:
        demo.install_demo_data(
            n=10,
        )
    except Exception as ex:
        logger.exception(ex)
        logger.error("Failed to install demo data")


def main(page: Page):
    """Entry point of the app"""
    app = TuttleApp(page)
    # install_demo_data()
    app.build()


if __name__ == "__main__":
    flet.app(name="Tuttle", target=main, assets_dir="assets", upload_dir="uploads")
