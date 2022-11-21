import typing
from typing import Callable

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    IconButton,
    Row,
    UserControl,
    icons,
    margin,
    padding,
)

from core.abstractions import DialogHandler, LocalCache, TuttleView
from core.views import progress_bars, selectors, texts
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    COMPACT_RAIL_WIDTH,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_START,
)
from core.views.spacers import mdSpace, smSpace, stdSpace
from projects.projects_model import Project
from res import spacing
from res.colors import GRAY_DARK_COLOR
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_3_SIZE, HEADLINE_FONT


class NewClientPopUp(DialogHandler):
    def __init__(self, dialogController: Callable[[any, AlertDialogControls], None]):
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    controls=[
                        texts.get_headline_with_subtitle(
                            title="Create a new client",
                            subtitle="You can add more info later",
                        ),
                        mdSpace,
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_client_title_changed,
                            lbl="Client Name",
                            hint="",
                        ),
                        mdSpace,
                        get_primary_btn(
                            label="Add Client", onClickCallback=self.on_add
                        ),
                    ]
                ),
                height=200,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            )
        )
        super().__init__(dialog, dialogController)
        self.clientTitle = ""

    def on_client_title_changed(self, e):
        self.clientTitle = e.control.value

    def on_add(self, e):
        pass


class NewContractPopUp(DialogHandler):
    def __init__(self, dialogController: Callable[[any, AlertDialogControls], None]):
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    controls=[
                        texts.get_headline_with_subtitle(
                            title="Create a new contract",
                            subtitle="You can add more info later",
                        ),
                        mdSpace,
                        texts.get_std_multiline_field(
                            onChangeCallback=self.on_contract_desc_changed,
                            lbl="Contract desctiption",
                            hint="",
                            minLines=5,
                        ),
                        mdSpace,
                        get_primary_btn(
                            label="Add Contract", onClickCallback=self.on_add
                        ),
                    ]
                ),
                height=300,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            )
        )
        super().__init__(dialog, dialogController)
        self.contract_title = ""

    def on_contract_desc_changed(self, e):
        self.contract_title = e.control.value

    def on_add(self, e):
        pass


class ProjectEditorScreen(TuttleView, UserControl):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        onNavigateBack: Callable,
        pageDialogController: typing.Optional[
            Callable[[any, AlertDialogControls], None]
        ],
    ):
        super().__init__(
            onChangeRouteCallback=changeRouteCallback,
            keepBackStack=True,
            horizontalAlignmentInParent=CENTER_ALIGNMENT,
            onNavigateBack=onNavigateBack,
            pageDialogController=pageDialogController,
        )
        self.newClientPopUp = NewClientPopUp(dialogController=self.pageDialogController)
        self.newContractPopUp = NewContractPopUp(
            dialogController=self.pageDialogController
        )
        self.clients = []
        self.contracts = []
        self.loadingBar = progress_bars.horizontalProgressBar

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_description_changed(self, e):
        self.description = e.control.value

    def on_tag_changed(self, e):
        self.tag = e.control.value

    def on_client_selected(self, e):
        self.client = e.control.value

    def on_contract_selected(self, e):
        self.contract = e.control.value

    def set_clients(self):
        """loads any existing clients"""
        self.clients = []

    def set_contracts(self):
        """loads any existing contracts"""
        self.contracts = []

    def did_mount(self):
        self.set_clients()
        self.set_contracts()
        if len(self.clients) == 0:
            self.clientsField.error_text = "Please create a new client"
        if len(self.contracts) == 0:
            self.contractsField.error_text = "Please create a new contract"
        self.loadingBar.visible = False
        self.update()

    def on_add_client(self, e):
        self.newClientPopUp.open_dialog()

    def on_add_contract(self, e):
        self.newContractPopUp.open_dialog()

    def on_save(self, e):
        print("clicked")

    def build(self):
        self.titleField = texts.get_std_txt_field(
            lbl="Title",
            hint="Project's title",
            onChangeCallback=self.on_title_changed,
        )
        self.descriptionField = texts.get_std_multiline_field(
            lbl="Description",
            hint="Project's description",
            onChangeCallback=self.on_description_changed,
        )
        self.tagField = texts.get_std_txt_field(
            lbl="Tag",
            hint="an optional tag",
            onChangeCallback=self.on_tag_changed,
        )
        self.clientsField = selectors.get_dropdown(
            lbl="Client",
            hint="Select the client",
            onChange=self.on_client_selected,
            items=self.clients,
        )
        self.contractsField = selectors.get_dropdown(
            lbl="Contract",
            hint="Contract under which this project is bind",
            onChange=self.on_contract_selected,
            items=self.contracts,
        )

        view = Container(
            expand=True,
            padding=padding.all(spacing.SPACE_MD),
            margin=margin.symmetric(vertical=spacing.SPACE_MD),
            content=Card(
                expand=True,
                content=Container(
                    Column(
                        expand=True,
                        controls=[
                            Row(
                                controls=[
                                    IconButton(
                                        icon=icons.CHEVRON_LEFT_ROUNDED,
                                        on_click=self.onNavigateBack,
                                    ),
                                    texts.get_headline_with_subtitle(
                                        title="New Project",
                                        subtitle="Create a new project",
                                    ),
                                ]
                            ),
                            self.loadingBar,
                            mdSpace,
                            self.titleField,
                            smSpace,
                            self.descriptionField,
                            smSpace,
                            Row(
                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                spacing=spacing.SPACE_STD,
                                controls=[
                                    self.clientsField,
                                    IconButton(
                                        icon=icons.ADD_CIRCLE_OUTLINE,
                                        on_click=self.on_add_client,
                                    ),
                                ],
                            ),
                            smSpace,
                            Row(
                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                spacing=spacing.SPACE_STD,
                                controls=[
                                    self.contractsField,
                                    IconButton(
                                        icon=icons.ADD_CIRCLE_OUTLINE,
                                        on_click=self.on_add_contract,
                                    ),
                                ],
                            ),
                            smSpace,
                            self.tagField,
                            mdSpace,
                            get_primary_btn(
                                label="Create Project", onClickCallback=self.on_save
                            ),
                        ],
                    ),
                    padding=padding.all(spacing.SPACE_MD),
                    width=MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def will_unmount(self):
        self.newClientPopUp.dimiss_open_dialogs()
        self.newContractPopUp.dimiss_open_dialogs()
        return super().will_unmount()
