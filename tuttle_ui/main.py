import flet
from flet import Page, theme
from routes import TuttleRoutes
from res.theme import APP_THEME, APP_FONTS, APP_THEME_MODE


def main(page: Page):
    page.title = "Tuttle"
    page.fonts = APP_FONTS
    page.theme_mode = APP_THEME_MODE
    page.theme = APP_THEME

    def route_change(route,):
        # auto invoked when the route changes
        page.views.clear()

        routeParser = TuttleRoutes()
        routeView = routeParser.parseRoute(pageRoute=page.route)
        
        page.views.append(routeView)
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


flet.app(target=main, assets_dir="assets")