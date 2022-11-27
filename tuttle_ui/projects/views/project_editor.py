import typing
from typing import Callable, Mapping, Optional
from projects.projects_model import Project
from flet import (
    Card,
    Column,
    Container,
    IconButton,
    Row,
    UserControl,
    icons,
    margin,
    padding,
    Text,
)

from core.abstractions import LocalCache, TuttleView
from core.views import progress_bars, selectors, texts

from core.views.buttons import get_primary_btn
from core.views.flet_constants import CENTER_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from core.views.spacers import mdSpace, smSpace
from projects.project_intents_impl import ProjectIntentImpl
from res import spacing
from res.dimens import MIN_WINDOW_WIDTH
from contracts.view.new_contract import NewContractPopUp
from core.views.alert_dialog_controls import AlertDialogControls
from clients.view.client_creator import NewClientPopUp
from res.colors import GRAY_COLOR
from res.fonts import BODY_1_SIZE

# TODO BUG WHEN EDITING BACK BUTTON DOES NOT WORK
class ProjectEditorScreen(TuttleView, UserControl):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        onNavigateBack: Callable,
        showSnackCallback: Callable[[str, bool], None],
        pageDialogController: typing.Optional[
            Callable[[any, AlertDialogControls], None]
        ],
        projectId: Optional[str],
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
        self.intentHandler = intentHandler
        self.newClientPopUp = NewClientPopUp(
            dialogController=self.pageDialogController,
            onSubmit=self.on_new_client_added,
        )
        self.newContractPopUp = NewContractPopUp(
            dialogController=self.pageDialogController,
            onContractSet=self.on_new_contract_added,
        )
        self.clients: Mapping[str, str] = {}
        self.contracts: Mapping[str, str] = {}
        self.loadingBar = progress_bars.horizontalProgressBar
        # info of project being edited / created
        self.projectId: Optional[int] = projectId
        self.projectBeingEdited: Optional[Project] = None
        self.title = ""
        self.description = ""
        self.contractId = ""
        self.clientId = ""
        self.tag = ""

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_description_changed(self, e):
        self.description = e.control.value

    def on_tag_changed(self, e):
        self.tag = e.control.value

    def get_id_from_dropdown_selection(self, selected: str):
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c
        return id

    def on_client_selected(self, e):
        # parse selected value to extract id
        self.clientId = self.get_id_from_dropdown_selection(selected=e.control.value)
        if self.clientsField.error_text:
            self.clientsField.error_text = None
            self.update()

    def on_contract_selected(self, e):
        # parse selected value to extract id
        self.contractId = self.get_id_from_dropdown_selection(selected=e.control.value)
        if self.contractsField.error_text:
            self.contractsField.error_text = None
            self.update()

    def clear_title_error(self, e):
        if self.titleField.error_text:
            self.titleField.error_text = None
            self.update()

    def clear_description_error(self, e):
        if self.descriptionField.error_text:
            self.descriptionField.error_text = None
            self.update()

    def show_progress_bar_disable_action(self):
        self.loadingBar.visible = True
        self.submitButton.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loadingBar.visible = False
        self.submitButton.disabled = False

    def on_new_contract_added(self, title: str):
        """attempts to save new contract"""
        self.show_progress_bar_disable_action()
        result = self.intentHandler.create_contract(title)
        if result.wasIntentSuccessful:
            self.reload_load_clients_and_contracts(reLoadClients=False)
        else:
            self.showSnack(result.errorMsg, True)
        self.enable_action_remove_progress_bar()
        self.update()

    def set_edited_project_info(self):
        """if user is editing a project
        set the data of the project as form values
        """
        self.titleField.value = self.projectBeingEdited.title
        self.title = self.projectBeingEdited.title
        self.descriptionField.value = self.projectBeingEdited.description
        self.description = self.projectBeingEdited.description
        self.tagField.value = self.projectBeingEdited.unique_tag
        self.tag = self.projectBeingEdited.unique_tag
        self.startDateField.set_date(self.projectBeingEdited.start_date)
        self.endDateField.set_date(self.projectBeingEdited.end_date)
        self.clientsEditor.visible = False
        self.contractsEditor.visible = False
        self.clientId = self.projectBeingEdited.client_id
        self.contractId = self.projectBeingEdited.contract_id
        self.clientIdView.value = f"Client Id {self.clientId}"
        self.contractIdView.value = f"Contract Id {self.contractId}"
        self.clientIdView.visible = True
        self.contractIdView.visible = True

    def on_new_client_added(self, title: str):
        """attempts to save new client"""
        self.loadingBar.visible = True
        self.submitButton.disabled = True
        result = self.intentHandler.create_client(title)
        if result.wasIntentSuccessful:
            self.reload_load_clients_and_contracts(reLoadContracts=False)
        else:
            self.showSnack(result.errorMsg, True)
        self.loadingBar.visible = False
        self.submitButton.disabled = False
        self.update()

    def add_tag_to_dropdown_item_id(self, id, value):
        """given id and value, prepends a # symbol and returns as str"""
        return f"#{id} {value}"

    def get_clients_as_list(self):
        """transforms a map of id-client_title to a list for dropdown options"""
        clients = []
        for key in self.clients:
            clients.append(
                self.add_tag_to_dropdown_item_id(id=key, value=self.clients[key])
            )
        return clients

    def get_contracts_as_list(self):
        """transforms a map of id-contract_desc to a list for dropdown options"""
        contracts = []
        for key in self.contracts:
            contracts.append(
                self.add_tag_to_dropdown_item_id(id=key, value=self.contracts[key])
            )
        return contracts

    def reload_load_clients_and_contracts(
        self, reLoadClients=True, reLoadContracts=True
    ):

        if reLoadClients:
            self.clients = self.intentHandler.get_all_clients_as_map()
            self.clientsField.error_text = (
                "Please create a new client" if len(self.clients) == 0 else None
            )
            selectors.update_dropdown_items(
                self.clientsField, self.get_clients_as_list()
            )
        if reLoadContracts:
            self.contracts = self.intentHandler.get_all_contracts_as_map()
            self.contractsField.error_text = (
                "Please create a new contract" if len(self.contracts) == 0 else None
            )
            selectors.update_dropdown_items(
                self.contractsField, self.get_contracts_as_list()
            )

    def did_mount(self):
        self.show_progress_bar_disable_action()
        if self.projectId:
            # user is editing an existing project
            result = self.intentHandler.get_project_by_id(self.projectId)
            if result.wasIntentSuccessful:
                self.projectBeingEdited = result.data
                self.set_edited_project_info()
            else:
                self.showSnack(result.errorMsg, True)
        else:
            # user is creating a new project
            self.reload_load_clients_and_contracts()
        self.enable_action_remove_progress_bar()
        self.update()

    def on_add_client(self, e):
        self.newClientPopUp.open_dialog()

    def on_add_contract(self, e):
        self.newContractPopUp.open_dialog()

    def on_save(self, e):
        if self.title is None:
            self.titleField.error_text = "Project title is required"
            self.update()
            return

        if self.description is None:
            self.descriptionField.error_text = "Project description is required"
            self.update()
            return

        startDate = self.startDateField.get_date()
        if startDate is None:
            self.showSnack("Please specify the start date", True)
            return

        endDate = self.endDateField.get_date()
        if endDate is None:
            self.showSnack("Please specify the end date", True)
            return

        if startDate > endDate:
            self.showSnack(
                "The end date of the project cannot be before the start date", True
            )
            return

        if self.clientId is None:
            self.clientsField.error_text = "Please select a client"
            self.update()
            return

        if self.contractId is None:
            self.contractsField.error_text = "Please specify the contract"
            self.update()
            return

        self.show_progress_bar_disable_action()
        result = self.intentHandler.save_project(
            title=self.title,
            description=self.description,
            startDate=startDate,
            endDate=endDate,
            tag=self.tag,
            clientId=self.clientId,
            contractId=self.contractId,
        )
        msg = (
            "New project created successfully"
            if result.wasIntentSuccessful
            else result.errorMsg
        )
        isError = not result.wasIntentSuccessful
        self.enable_action_remove_progress_bar()
        self.showSnack(msg, isError)

    def build(self):
        self.titleField = texts.get_std_txt_field(
            lbl="Title",
            hint="Project's title",
            onChangeCallback=self.on_title_changed,
            onFocusCallback=self.clear_title_error,
        )
        self.descriptionField = texts.get_std_multiline_field(
            lbl="Description",
            hint="Project's description",
            onChangeCallback=self.on_description_changed,
            onFocusCallback=self.clear_description_error,
        )
        self.tagField = texts.get_std_txt_field(
            lbl="Tag",
            hint="an optional tag",
            onChangeCallback=self.on_tag_changed,
        )
        self.clientsField = selectors.get_dropdown(
            lbl="Client",
            onChange=self.on_client_selected,
            items=self.get_clients_as_list(),
        )
        self.contractsField = selectors.get_dropdown(
            lbl="Contract",
            onChange=self.on_contract_selected,
            items=self.get_contracts_as_list(),
        )
        self.startDateField = selectors.DateSelector(label="Start Date")
        self.endDateField = selectors.DateSelector(label="End Date")
        self.submitButton = get_primary_btn(
            label="Create Project" if self.projectId is None else "Update Project",
            onClickCallback=self.on_save,
        )
        self.clientsEditor = Row(
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
        )
        self.contractsEditor = Row(
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
        )

        """used to display client and contract ids 
        for when editing the project"""
        self.clientIdView = Text(size=BODY_1_SIZE, color=GRAY_COLOR, visible=False)
        self.contractIdView = Text(size=BODY_1_SIZE, color=GRAY_COLOR, visible=False)
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
                                        title="New Project"
                                        if self.projectId is None
                                        else "Edit Project",
                                        subtitle="Create a new project"
                                        if self.projectId is None
                                        else "Update existing project",
                                    ),
                                ]
                            ),
                            self.loadingBar,
                            mdSpace,
                            self.titleField,
                            smSpace,
                            self.descriptionField,
                            smSpace,
                            self.clientsEditor,
                            self.clientIdView,
                            smSpace,
                            self.contractsEditor,
                            self.contractIdView,
                            smSpace,
                            self.tagField,
                            mdSpace,
                            self.startDateField,
                            mdSpace,
                            self.endDateField,
                            mdSpace,
                            self.submitButton,
                        ],
                    ),
                    padding=padding.all(spacing.SPACE_MD),
                    width=MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def will_unmount(self):
        try:
            if self.newClientPopUp:
                self.newClientPopUp.dimiss_open_dialogs()
            if self.newContractPopUp:
                self.newContractPopUp.dimiss_open_dialogs()
        except Exception as e:
            print(e)
