import typing
from typing import Callable, Mapping, Optional
from projects.project_model import Project
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

from core.abstractions import TuttleView
from core.views import (
    horizontal_progress,
    update_dropdown_items,
    get_dropdown,
    get_std_txt_field,
    get_std_multiline_field,
    DateSelector,
    get_headline_with_subtitle,
)
from core.models import IntentResult
from core.views import get_primary_btn
from core.constants_and_enums import CENTER_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from core.views import mdSpace, smSpace
from projects.intent_impl import ProjectsIntentImpl
from res import dimens
from res.dimens import MIN_WINDOW_WIDTH
from res.colors import GRAY_COLOR
from res.fonts import BODY_1_SIZE
from res.utils import CONTRACT_EDITOR_SCREEN_ROUTE


class ProjectEditorScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
        project_id: str,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
            horizontal_alignment_in_parent=CENTER_ALIGNMENT,
        )
        self.intent_handler = ProjectsIntentImpl(local_storage=local_storage)

        self.contracts_map = {}
        self.loading_indicator = horizontal_progress
        # info of project being edited / created
        self.project_id: Optional[int] = project_id

        self.project_being_edited: Optional[Project] = None
        self.title = ""
        self.description = ""
        self.contract = None
        self.tag = ""

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_description_changed(self, e):
        self.description = e.control.value

    def on_tag_changed(self, e):
        self.tag = e.control.value

    # DROP DOWN ITEMS
    def add_tag_to_dropdown_item_id(self, id, value):
        """given id and value, prepends a # symbol and returns as str"""
        return f"#{id} {value}"

    def get_contracts_as_list(self):
        """transforms a map of id-contract_desc to a list for dropdown options"""
        contracts = []
        for key in self.contracts_map:
            contracts.append(
                self.add_tag_to_dropdown_item_id(
                    id=key, value=self.contracts_map[key].title
                )
            )
        return contracts

    def get_id_from_dropdown_selection(self, selected: str):
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c
        return id

    def on_contract_selected(self, e):
        # parse selected value to extract id
        contract_id = self.get_id_from_dropdown_selection(selected=e.control.value)
        if int(contract_id) in self.contracts_map:
            self.contract = self.contracts_map[int(contract_id)]
        if self.contracts_field.error_text:
            self.contracts_field.error_text = None
            self.update()

    def clear_title_error(self, e):
        if self.title_field.error_text:
            self.title_field.error_text = None
            self.update()

    def clear_description_error(self, e):
        if self.description_field.error_text:
            self.description_field.error_text = None
            self.update()

    # LOADING DATA
    def did_mount(self):
        self.show_progress_bar_disable_action()
        if self.project_id:
            # user is editing an existing project
            result: IntentResult = self.intent_handler.get_project_by_id(
                self.project_id
            )
            if result.was_intent_successful:
                self.project_being_edited = result.data
                self.set_edited_project_info()
            else:
                self.show_snack(result.error_msg, True)
        else:
            # user is creating a new project
            self.reload_load_contracts()
        self.enable_action_remove_progress_bar()
        self.update()

    def show_progress_bar_disable_action(self):
        self.loading_indicator.visible = True
        self.submit_btn.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loading_indicator.visible = False
        self.submit_btn.disabled = False

    def set_edited_project_info(self):
        """if user is editing a project
        set the data of the project as form values
        """
        self.title_field.value = self.project_being_edited.title
        self.title = self.project_being_edited.title
        self.description_field.value = self.project_being_edited.description
        self.description = self.project_being_edited.description
        self.tag_field.value = self.project_being_edited.unique_tag
        self.tag = self.project_being_edited.unique_tag
        self.start_date_field.set_date(self.project_being_edited.start_date)
        self.end_date_field.set_date(self.project_being_edited.end_date)
        self.contractsEditor.visible = False
        self.contract = self.project_being_edited.contract
        self.contract_title_view.value = f"Contract {self.contract.title}"
        self.contract_title_view.visible = True

    def reload_load_contracts(
        self,
    ):
        self.contracts_map = self.intent_handler.get_all_contracts_as_map()
        self.contracts_field.error_text = (
            "Please create a new contract" if len(self.contracts_map) == 0 else None
        )
        update_dropdown_items(self.contracts_field, self.get_contracts_as_list())

    def on_add_contract(self, e):
        # todo confirm? before re routing
        self.navigate_to_route(CONTRACT_EDITOR_SCREEN_ROUTE)

    def on_save(self, e):
        if not self.title:
            self.title_field.error_text = "Project title is required"
            self.update()
            return

        if not self.description:
            self.description_field.error_text = "Project description is required"
            self.update()
            return

        start_date_value = self.start_date_field.get_date()
        if start_date_value is None:
            self.show_snack("Please specify the start date", True)
            return

        end_date_value = self.end_date_field.get_date()
        if end_date_value is None:
            self.show_snack("Please specify the end date", True)
            return

        if start_date_value > end_date_value:
            self.show_snack(
                "The end date of the project cannot be before the start date", True
            )
            return

        if self.contract is None:
            self.contracts_field.error_text = "Please specify the contract"
            self.update()
            return

        self.show_progress_bar_disable_action()
        result: IntentResult = self.intent_handler.save_project(
            title=self.title,
            description=self.description,
            start_date=start_date_value,
            end_date=end_date_value,
            unique_tag=self.tag,
            contract=self.contract,
            project=self.project_being_edited,
        )
        successMsg = (
            "Updated project successfully"
            if self.project_id is None
            else "New project created successfully"
        )
        msg = successMsg if result.was_intent_successful else result.error_msg
        isError = not result.was_intent_successful
        self.enable_action_remove_progress_bar()
        self.show_snack(msg, isError)

    def build(self):
        self.title_field = get_std_txt_field(
            lbl="Title",
            hint="Project's title",
            on_change=self.on_title_changed,
            on_focus=self.clear_title_error,
        )
        self.description_field = get_std_multiline_field(
            lbl="Description",
            hint="Project's description",
            on_change=self.on_description_changed,
            on_focus=self.clear_description_error,
        )
        self.tag_field = get_std_txt_field(
            lbl="Tag",
            hint="an optional tag",
            on_change=self.on_tag_changed,
        )

        self.contracts_field = get_dropdown(
            lbl="Contract",
            on_change=self.on_contract_selected,
            items=self.get_contracts_as_list(),
        )
        self.start_date_field = DateSelector(label="Start Date")
        self.end_date_field = DateSelector(label="End Date")
        self.submit_btn = get_primary_btn(
            label="Create Project" if self.project_id is None else "Update Project",
            on_click=self.on_save,
        )

        self.contractsEditor = Row(
            alignment=SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            spacing=dimens.SPACE_STD,
            controls=[
                self.contracts_field,
                IconButton(
                    icon=icons.ADD_CIRCLE_OUTLINE,
                    on_click=self.on_add_contract,
                ),
            ],
        )

        """used to display contract id
        for when editing the project"""
        self.contract_title_view = Text(
            size=BODY_1_SIZE, color=GRAY_COLOR, visible=False
        )
        view = Container(
            expand=True,
            padding=padding.all(dimens.SPACE_MD),
            margin=margin.symmetric(vertical=dimens.SPACE_MD),
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
                                        on_click=self.on_navigate_back,
                                    ),
                                    get_headline_with_subtitle(
                                        title="New Project"
                                        if self.project_id is None
                                        else "Edit Project",
                                        subtitle="Create a new project"
                                        if self.project_id is None
                                        else "Update existing project",
                                    ),
                                ]
                            ),
                            self.loading_indicator,
                            mdSpace,
                            self.title_field,
                            smSpace,
                            self.description_field,
                            smSpace,
                            self.contractsEditor,
                            self.contract_title_view,
                            smSpace,
                            self.tag_field,
                            mdSpace,
                            self.start_date_field,
                            mdSpace,
                            self.end_date_field,
                            mdSpace,
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view
