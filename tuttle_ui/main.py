import flet
from flet import Page

from res.strings import APP_NAME
from res.theme import APP_FONTS, APP_THEME, APP_THEME_MODE
from routes import TuttleRoutes

def main(page: Page):
    """Entry point of the app"""
    page.title = APP_NAME
    page.fonts = APP_FONTS
    page.theme_mode = APP_THEME_MODE
    page.theme = APP_THEME

    def change_route(toRoute : str, data : any):
        """Navigates to a new route
        
        passes data to the destination if provided
        """
        page.go(toRoute)

    def on_route_change(route):
        """auto invoked when the route changes
        
        parses the new destination route
        then appends the new page to page views
        """
        page.views.clear()

        routeParser = TuttleRoutes(onChangeRouteCallback = change_route)
        routeView = routeParser.parse_route(pageRoute=page.route)
        page.views.append(routeView)
        page.update()

    def on_view_pop(view):
        """auto invoked on back pressed"""
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    page.go(page.route)


flet.app(target=main, assets_dir="assets")