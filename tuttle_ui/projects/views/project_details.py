import typing
from typing import Callable, Optional
from projects.projects_model import Project
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

from core.views.progress_bars import horizontalProgressBar
from core.abstractions import LocalCache, TuttleView
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
)
from core.views.spacers import mdSpace
from projects.project_intents_impl import ProjectIntentImpl
from res import spacing, fonts, colors
from res.dimens import MIN_WINDOW_WIDTH
from res.strings import (
    CLIENT_ID_LBL,
    CONTRACT_ID_LBL,
    START_DATE,
    END_DATE,
    PROJECT_TAG,
    PROJECT_STATUS_LBL,
    PROJECT_LBL,
    DELETE_PROJECT,
    EDIT_PROJECT,
    MARK_AS_COMPLETE,
    VIEW_CLIENT_LBL,
    VIEW_CONTRACT_LBL,
    VIEW_CLIENT_HINT,
    VIEW_CONTRACT_HINT,
    PROJECT_DESC_LBL,
)
from res.utils import PROJECT_EDITOR_SCREEN_ROUTE


class ProjectDetailsScreen(TuttleView, UserControl):
    def __init__(
        self,
        projectId: str,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        onNavigateBack: Callable,
        showSnackCallback: Callable[[str, bool], None],
        pageDialogController: typing.Optional[
            Callable[[any, AlertDialogControls], None]
        ],
    ):
        intentHandler = ProjectIntentImpl(cache=localCacheHandler)
        super().__init__(
            onChangeRouteCallback=changeRouteCallback,
            keepBackStack=True,
            horizontalAlignmentInParent=CENTER_ALIGNMENT,
            onNavigateBack=onNavigateBack,
            pageDialogController=pageDialogController,
            intentHandler=intentHandler,
            showSnackCallback=showSnackCallback,
        )
        self.projectId = projectId
        self.intentHandler = intentHandler
        self.loadingIndicator = horizontalProgressBar
        self.project: Optional[Project]

    def display_project_data(self):
        self.projectTitleTxt.value = self.project.title
        self.clientIdTxt.value = f"{CLIENT_ID_LBL}{self.project.client_id}"
        self.contractIdTxt.value = f"{CONTRACT_ID_LBL}{self.project.contract_id}"
        self.projectDescriptionTxt.value = self.project.description
        self.projectStartDateTxt.value = f"{START_DATE}: {self.project.start_date}"
        self.projectEndDateTxt.value = f"{END_DATE}: {self.project.end_date}"
        self.projectStatusTxt.value = (
            f"{PROJECT_STATUS_LBL} {self.project.get_status()}"
        )
        self.projectTaglineTxt.value = f"{PROJECT_TAG}{self.project.unique_tag}"

    def did_mount(self):
        result = self.intentHandler.get_project_by_id(self.projectId)
        if not result.wasIntentSuccessful:
            self.showSnack(result.errorMsg, True)
        else:
            self.project = result.data
            self.display_project_data()
        self.loadingIndicator.visible = False
        self.update()

    def on_view_client_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_view_contract_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_mark_as_complete_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_edit_clicked(self, e):
        if self.project is None:
            # project is not loaded yet
            return
        self.changeRoute(PROJECT_EDITOR_SCREEN_ROUTE, self.project.id)

    def on_delete_clicked(self, e):
        self.showSnack("Coming soon", False)

    def build(self):
        """Called when page is built"""
        self.editProjectBtn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip=EDIT_PROJECT,
            on_click=self.on_edit_clicked,
        )
        self.markAsCompleteBtn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip=MARK_AS_COMPLETE,
            on_click=self.on_mark_as_complete_clicked,
        )
        self.deleteProjectBtn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip=DELETE_PROJECT,
            on_click=self.on_delete_clicked,
        )

        self.projectTitleTxt = Text(size=fonts.SUBTITLE_1_SIZE)
        self.clientIdTxt = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.contractIdTxt = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.projectDescriptionTxt = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.projectStartDateTxt = Text(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
            font_family=fonts.HEADLINE_FONT,
        )
        self.projectEndDateTxt = Text(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
            font_family=fonts.HEADLINE_FONT,
        )

        self.projectStatusTxt = Text(size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR)
        self.projectTaglineTxt = Text(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )

        page_view = Row(
            [
                Container(
                    padding=padding.all(spacing.SPACE_STD),
                    width=int(MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.onNavigateBack,
                            ),
                            TextButton(
                                VIEW_CLIENT_LBL,
                                tooltip=VIEW_CLIENT_HINT,
                                on_click=self.on_view_client_clicked,
                            ),
                            TextButton(
                                VIEW_CONTRACT_LBL,
                                tooltip=VIEW_CONTRACT_HINT,
                                on_click=self.on_view_contract_clicked,
                            ),
                        ]
                    ),
                ),
                Container(
                    expand=True,
                    padding=padding.all(spacing.SPACE_MD),
                    content=Column(
                        controls=[
                            self.loadingIndicator,
                            Row(
                                controls=[
                                    Icon(icons.WORK_ROUNDED),
                                    Column(
                                        expand=True,
                                        spacing=0,
                                        run_spacing=0,
                                        controls=[
                                            Row(
                                                vertical_alignment=CENTER_ALIGNMENT,
                                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    Text(
                                                        PROJECT_LBL,
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=CENTER_ALIGNMENT,
                                                        alignment=SPACE_BETWEEN_ALIGNMENT,
                                                        spacing=spacing.SPACE_STD,
                                                        run_spacing=spacing.SPACE_STD,
                                                        controls=[
                                                            self.editProjectBtn,
                                                            self.markAsCompleteBtn,
                                                            self.deleteProjectBtn,
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            self.projectTitleTxt,
                                            self.clientIdTxt,
                                            self.contractIdTxt,
                                        ],
                                    ),
                                ],
                            ),
                            mdSpace,
                            Text(
                                PROJECT_DESC_LBL,
                                size=fonts.SUBTITLE_1_SIZE,
                            ),
                            self.projectDescriptionTxt,
                            self.projectStartDateTxt,
                            self.projectEndDateTxt,
                            mdSpace,
                            Row(
                                spacing=spacing.SPACE_STD,
                                run_spacing=spacing.SPACE_STD,
                                alignment=START_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                controls=[
                                    Card(
                                        Container(
                                            self.projectStatusTxt,
                                            padding=padding.all(spacing.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                    Card(
                                        Container(
                                            self.projectTaglineTxt,
                                            padding=padding.all(spacing.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
            spacing=spacing.SPACE_XS,
            run_spacing=spacing.SPACE_MD,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        page_view.padding = spacing.SPACE_STD
        return page_view
