import re
from typing import Callable, Optional

from loguru import logger
from pathlib import Path

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
from preferences.model import PreferencesStorageKeys
from preferences.intent import PreferencesIntent
from core.abstractions import TuttleView
from core.utils import AlertDialogControls
from core.local_storage_impl import ClientStorageImpl
from core.models import RouteView
from error_views.page_not_found_screen import Error404Screen
from home.view import HomeScreen
from preferences.view import PreferencesScreen
from projects.view import CreateProjectScreen, EditProjectScreen, ViewProjectScreen
from res.colors import BLACK_COLOR_ALT, ERROR_COLOR, PRIMARY_COLOR, WHITE_COLOR
from res.dimens import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH
from res.fonts import APP_FONTS, HEADLINE_4_SIZE, HEADLINE_FONT
from res.theme import APP_THEME, THEME_MODES, get_theme_mode_from_value
from res.res_utils import (
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
from core.abstractions import TuttleViewParams


class TuttleApp:
    """The main application class"""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.page.title = "Tuttle"
        self.page.fonts = APP_FONTS
        self.page.theme = APP_THEME
        self.local_storage = ClientStorageImpl(page=self.page)
        preferences = PreferencesIntent(self.local_storage)
        preferences_result = preferences.get_preference(
            PreferencesStorageKeys.theme_mode_key
        )
        theme = (
            preferences_result.data
            if preferences_result.was_intent_successful
            else THEME_MODES.dark.value
        )
        self.page.theme_mode = theme
        self.page.window_min_width = MIN_WINDOW_WIDTH
        self.page.window_min_height = MIN_WINDOW_HEIGHT
        self.page.window_width = MIN_WINDOW_WIDTH * 2
        self.page.window_height = MIN_WINDOW_HEIGHT * 2
        self.file_picker = flet.FilePicker()
        self.page.overlay.append(self.file_picker)

        """holds the RouteView object associated with a route
        used in on route change"""
        self.route_to_route_view_cache = {}
        self.page.on_route_change = self.on_route_change
        self.page.on_view_pop = self.on_view_pop
        self.route_parser = TuttleRoutes(self)
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
            tmp_upload_url = self.page.get_upload_url(file.name, 600)
            upload_item = FilePickerUploadFile(
                file.name,
                upload_url=tmp_upload_url,
            )
            self.file_picker.upload([upload_item])
            return f"{get_uploads_url(full_path = False)}/{file.name}"
        except Exception as e:
            print(f"Exception @app.upload_file_callback raised during file upload {e}")
            return None

    def on_theme_mode_changed(self, selected_theme: str):
        """callback function used by views for changing app theme mode"""
        mode = get_theme_mode_from_value(selected_theme)
        self.page.theme_mode = mode.value
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
            route_view_wrapper = self.route_parser.parse_route(pageRoute=route.route)
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
        self.on_theme_changed = app.on_theme_mode_changed
        self.tuttle_view_params = TuttleViewParams(
            navigate_to_route=app.change_route,
            show_snack=app.show_snack,
            dialog_controller=app.control_alert_dialog,
            on_navigate_back=app.on_view_pop,
            local_storage=app.local_storage,
            upload_file_callback=app.upload_file_callback,
            pick_file_callback=app.pick_file_callback,
        )

    def get_page_route_view(
        self,
        routeName: str,
        view: TuttleView,
    ) -> RouteView:
        """Constructs the view with a given route"""
        print(f"page scroll type {view.page_scroll_type}")
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
            screen = SplashScreen(params=self.tuttle_view_params)
        elif routePath.match(HOME_SCREEN_ROUTE):
            screen = HomeScreen(params=self.tuttle_view_params)
        elif routePath.match(PROFILE_SCREEN_ROUTE):
            screen = ProfileScreen(params=self.tuttle_view_params)
        elif routePath.match(CONTRACT_CREATOR_SCREEN_ROUTE):
            screen = CreateContractScreen(params=self.tuttle_view_params)
        elif routePath.match(f"{CONTRACT_DETAILS_SCREEN_ROUTE}/:contractId"):
            screen = ViewContractScreen(
                params=self.tuttle_view_params, contract_id=routePath.contractId
            )
        elif routePath.match(f"{CONTRACT_EDITOR_SCREEN_ROUTE}/:contractId"):
            contractId = None
            if hasattr(routePath, "contractId"):
                contractId = routePath.contractId
            screen = ContractEditorScreen(
                params=self.tuttle_view_params, contract_id=contractId
            )
        elif routePath.match(PREFERENCES_SCREEN_ROUTE):
            screen = PreferencesScreen(
                params=self.tuttle_view_params, on_theme_changed=self.on_theme_changed
            )
        elif routePath.match(PROJECT_CREATOR_SCREEN_ROUTE):
            screen = CreateProjectScreen(params=self.tuttle_view_params)
        elif routePath.match(f"{PROJECT_DETAILS_SCREEN_ROUTE}/:projectId"):
            screen = ViewProjectScreen(
                params=self.tuttle_view_params, project_id=routePath.projectId
            )
        elif routePath.match(PROJECT_EDITOR_SCREEN_ROUTE) or routePath.match(
            f"{PROJECT_EDITOR_SCREEN_ROUTE}/:projectId"
        ):
            projectId = None
            if hasattr(routePath, "projectId"):
                projectId = routePath.projectId
            screen = EditProjectScreen(
                params=self.tuttle_view_params, project_id=projectId
            )
        else:
            screen = Error404Screen(params=self.tuttle_view_params)

        print(f"screen has {screen.page_scroll_type}")
        return self.get_page_route_view(routePath.route, view=screen)


def ensure_app_dir() -> Path:
    """Ensures that the user directory exists"""
    # use pathlib
    app_dir = Path.home() / ".tuttle"
    if not app_dir.exists():
        app_dir.mkdir(parents=True)
    return app_dir


def install_demo_data():
    try:
        app_dir = ensure_app_dir()
        demo.install_demo_data(
            n=10,
            db_path=app_dir / "tuttle.db",
        )
    except Exception as ex:
        logger.exception(ex)
        logger.error("Failed to install demo data")


def get_uploads_url(full_path: bool = True):
    return "assets/uploads" if full_path else "/uploads"


def main(page: Page):
    """Entry point of the app"""
    app = TuttleApp(page)

    # install demo data
    install_demo_data()
    app.build()


if __name__ == "__main__":
    flet.app(
        name="Tuttle",
        target=main,
        assets_dir="assets",
        upload_dir=get_uploads_url(),
    )
