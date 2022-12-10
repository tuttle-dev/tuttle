from flet import (
    Column,
    Container,
    GridView,
    ResponsiveRow,
    Text,
    UserControl,
)

import core
import res

from .intent import TimeTrackingIntentImpl


class TimeTrackingView(core.abstractions.TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = TimeTrackingIntentImpl(local_storage=local_storage)
        self.loading_indicator = core.views.horizontal_progress
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        core.views.get_headline_txt(
                            txt="My Time Tracking", size=res.fonts.HEADLINE_4_SIZE
                        ),
                        self.loading_indicator,
                        self.no_time_tracking_control,
                    ],
                )
            ]
        )

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_time_tracking()
            count = len(self.time_tracking_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_time_tracking()
            else:
                self.display_currently_filtered_time_tracking()
            if self.mounted:
                self.update()
        except Exception as e:
            # logger
            print(f"exception raised @time_tracking.did_mount {e}")

    def build(self):
        return Column(
            controls=[
                self.title_control,
                res.dimens.mdSpace,
            ]
        )

    def will_unmount(self):
        self.mounted = False
