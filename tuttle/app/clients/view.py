from typing import Callable, Mapping, Optional

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    Icon,
    ListTile,
    ResponsiveRow,
    Row,
    UserControl,
    border_radius,
    padding,
)

from clients.intent import ClientsIntent
from core import utils, views
from core.abstractions import DialogHandler, TView, TViewParams
from core.intent_result import IntentResult
from res import colors, dimens, fonts, res_utils

from tuttle.model import Address, Client, Contact


class ClientCard(UserControl):
    """Formats a single client info into a card ui display"""

    def __init__(
        self,
        client: Client,
        on_edit: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
    ):
        super().__init__()
        self.client = client
        self.client_info_container = Column(spacing=0, run_spacing=0)
        self.on_edit_clicked = on_edit
        self.on_delete_clicked = on_delete

    def build(self):
        """Builds the client card"""
        if self.client.invoicing_contact:
            invoicing_contact_info = self.client.invoicing_contact.print_address()
        else:
            invoicing_contact_info = "*not specified"
        editable = True if self.on_edit_clicked or self.on_delete_clicked else None

        editor_controls = (
            views.TContextMenu(
                on_click_delete=lambda e: self.on_delete_clicked(self.client),
                on_click_edit=lambda e: self.on_edit_clicked(self.client),
            )
            if editable
            else views.Spacer(sm_space=True)
        )

        self.client_info_container.controls = [
            ListTile(
                leading=Icon(
                    utils.TuttleComponentIcons.client_icon,
                    size=dimens.MD_ICON_SIZE,
                ),
                title=views.TBodyText(self.client.name),
                trailing=editor_controls,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="Invoicing Contact",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    views.TBodyText(
                        txt=invoicing_contact_info,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
        ]

        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(dimens.SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.client_info_container,
            ),
        )
        return card


class ClientViewPopUp(DialogHandler, UserControl):
    """Pop up used to displaying a client"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        client: Client,
    ):
        # dimensions of the pop up and the elements inside
        # accounting for margins and paddings

        pop_up_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)

        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[ClientCard(client=client)],
                ),
                width=pop_up_width,
            ),
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)


class ClientEditorPopUp(DialogHandler, UserControl):
    """Pop up used for creating or updating a client"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        on_error: Callable[[str], None],
        contacts_map: Mapping[int, Contact],
        client: Optional[Client] = None,
    ):
        # dimensions of the pop up and the elements inside
        # accounting for margins and paddings
        pop_up_height = dimens.MIN_WINDOW_HEIGHT
        pop_up_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        half_of_pop_up_width = int(dimens.MIN_WINDOW_WIDTH * 0.35)

        self.client = client if client is not None else Client()
        self.invoicing_contact = (
            self.client.invoicing_contact
            if self.client.invoicing_contact is not None
            else Contact()
        )
        self.address = (
            self.invoicing_contact.address
            if self.invoicing_contact.address is not None
            else Address()
        )
        if not self.invoicing_contact.address:
            self.invoicing_contact.address = self.address
        self.contacts_as_map = contacts_map
        self.contact_options = self.get_contacts_as_list()

        title = "Edit Client" if client is not None else "New Client"

        initial_selected_contact = self.get_contact_dropdown_item(
            self.invoicing_contact.id
        )

        self.first_name_field = views.TTextField(
            label="First Name",
            hint=self.invoicing_contact.first_name,
            initial_value=self.invoicing_contact.first_name,
        )

        self.last_name_field = views.TTextField(
            label="Last Name",
            hint=self.invoicing_contact.last_name,
            initial_value=self.invoicing_contact.last_name,
        )
        self.company_field = views.TTextField(
            label="Company",
            hint=self.invoicing_contact.company,
            initial_value=self.invoicing_contact.company,
        )
        self.email_field = views.TTextField(
            label="Email",
            hint=self.invoicing_contact.email,
            initial_value=self.invoicing_contact.email,
        )

        self.street_field = views.TTextField(
            label="Street",
            hint=self.invoicing_contact.address.street,
            initial_value=self.invoicing_contact.address.street,
            width=half_of_pop_up_width,
        )
        self.street_num_field = views.TTextField(
            label="Street No.",
            hint=self.invoicing_contact.address.number,
            initial_value=self.invoicing_contact.address.number,
            width=half_of_pop_up_width,
        )
        self.postal_code_field = views.TTextField(
            label="Postal code",
            hint=self.invoicing_contact.address.postal_code,
            initial_value=self.invoicing_contact.address.postal_code,
            width=half_of_pop_up_width,
        )
        self.city_field = views.TTextField(
            label="City",
            hint=self.invoicing_contact.address.city,
            initial_value=self.invoicing_contact.address.city,
            width=half_of_pop_up_width,
        )
        self.country_field = views.TTextField(
            label="Country",
            hint=self.invoicing_contact.address.country,
            initial_value=self.invoicing_contact.address.country,
        )
        self.client_name_field = views.TTextField(
            label="Client's name",
            hint=self.client.name,
            initial_value=self.client.name,
        )

        self.contacts_dropdown = views.TDropDown(
            on_change=self.on_contact_selected,
            label="Select contact",
            items=self.contact_options,
            initial_value=initial_selected_contact,
        )
        self.form_error_field = views.TErrorText(txt="", show=False)

        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.THeading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.Spacer(xs_space=True),
                        self.form_error_field,
                        views.Spacer(xs_space=True),
                        self.client_name_field,
                        views.Spacer(xs_space=True),
                        views.THeading(
                            title="Invoicing Contact",
                            size=fonts.SUBTITLE_2_SIZE,
                            color=colors.GRAY_COLOR,
                        ),
                        views.Spacer(xs_space=True),
                        self.contacts_dropdown,
                        views.Spacer(xs_space=True),
                        self.first_name_field,
                        self.last_name_field,
                        self.company_field,
                        self.email_field,
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[self.street_field, self.street_num_field],
                        ),
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                self.postal_code_field,
                                self.city_field,
                            ],
                        ),
                        self.country_field,
                        views.Spacer(),
                    ],
                ),
                width=pop_up_width,
            ),
            actions=[
                views.TPrimaryButton(label="Done", on_click=self.on_submit_btn_clicked),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_submit_callback = on_submit
        self.on_error_callback = on_error
        self.form_error = ""

    def get_contacts_as_list(self):
        """transforms a map of id-contact_name to a list for dropdown options"""
        contacts_list = []
        for key in self.contacts_as_map:
            item = self.get_contact_dropdown_item(key)
            if item:
                contacts_list.append(item)
        return contacts_list

    def get_contact_dropdown_item(self, contact_id):
        """appends an id to the contact name for dropdown options"""
        if contact_id is not None and contact_id in self.contacts_as_map:
            return f"{contact_id}. {self.contacts_as_map[contact_id].name}"
        return ""

    def on_contact_selected(self, e):
        # parse selected value to extract id
        selected = e.control.value
        id = ""
        for c in selected:
            if c == ".":
                break
            id = id + c
        if int(id) in self.contacts_as_map:
            self.invoicing_contact: Contact = self.contacts_as_map[int(id)]
            self.set_invoicing_contact_fields()

    def set_invoicing_contact_fields(self):
        self.first_name_field.value = self.invoicing_contact.first_name
        self.last_name_field.value = self.invoicing_contact.last_name
        self.company_field.value = self.invoicing_contact.company
        self.email_field.value = self.invoicing_contact.email
        self.street_field.value = self.invoicing_contact.address.street
        self.street_num_field.value = self.invoicing_contact.address.number
        self.postal_code_field.value = self.invoicing_contact.address.postal_code
        self.city_field.value = self.invoicing_contact.address.city
        self.country_field.value = self.invoicing_contact.address.country
        self.dialog.update()

    def toggle_form_error(self):
        """toggles the form error field visibility"""
        self.form_error_field.value = self.form_error
        self.form_error_field.visible = True if self.form_error else False
        self.dialog.update()

    def on_submit_btn_clicked(self, e):
        """validates the form and calls the on_submit callback"""
        self.form_error = ""
        self.toggle_form_error()

        # get values from fields
        client_name = self.client_name_field.value.strip()
        first_name = self.first_name_field.value.strip()
        last_name = self.last_name_field.value.strip()
        company = self.company_field.value.strip()
        email = self.email_field.value.strip()
        street = self.street_field.value.strip()
        street_num = self.street_num_field.value.strip()
        postal_code = self.postal_code_field.value.strip()
        city = self.city_field.value.strip()
        country = self.country_field.value.strip()

        # update where updated else keep old value
        self.client.name = client_name if client_name else self.client.name
        self.invoicing_contact.first_name = (
            first_name if first_name else self.invoicing_contact.first_name
        )
        self.invoicing_contact.last_name = (
            last_name if last_name else self.invoicing_contact.last_name
        )
        self.invoicing_contact.company = (
            company if company else self.invoicing_contact.company
        )
        self.invoicing_contact.email = email if email else self.invoicing_contact.email
        self.address.street = (
            street if street else self.invoicing_contact.address.street
        )

        self.address.number = (
            street_num if street_num else self.invoicing_contact.address.number
        )
        self.address.postal_code = (
            postal_code if postal_code else self.invoicing_contact.address.postal_code
        )
        self.address.city = city if city else self.invoicing_contact.address.city
        self.address.country = (
            country if country else self.invoicing_contact.address.country
        )
        self.invoicing_contact.address = self.address
        self.client.invoicing_contact = self.invoicing_contact
        if not self.is_valid():
            self.toggle_form_error()
            return
        self.close_dialog()
        self.on_submit_callback(self.client)

    def is_valid(self) -> bool:
        """Checks if the provided client info is valid"""
        if not self.client.name:
            self.form_error = "Please provide the client's name"
            self.on_error_callback(self.form_error)
            return False
        if not self.client.invoicing_contact:
            self.form_error = "Please set the invoicing contact"
            self.on_error_callback(self.form_error)
            return False
        if (
            not self.client.invoicing_contact.first_name
            or not self.client.invoicing_contact.last_name
        ):
            self.form_error = "Please provide the contact's name"
            self.on_error_callback(self.form_error)
            return False
        if self.client.invoicing_contact.address.is_empty:
            self.form_error = "Please provide the invoice contact's address"
            self.on_error_callback(self.form_error)
            return False
        return True

    def build(self):
        """Builds the dialog"""
        return self.dialog


class ClientsListView(TView, UserControl):
    """View for displaying a list of clients"""

    def __init__(self, params: TViewParams):
        super().__init__(params=params)
        self.intent = ClientsIntent()
        self.loading_indicator = views.TProgressBar()
        self.no_clients_control = views.TBodyText(
            txt="You have not added any clients yet.",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.THeading(title="My Clients", size=fonts.HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_clients_control,
                    ],
                )
            ]
        )
        self.clients_container = views.THomeGrid()
        self.clients_to_display = {}
        self.contacts = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        """Handles intents from the parent view"""
        if intent == res_utils.ADD_CLIENT_INTENT:
            # Open the client editor
            if self.editor is not None:
                self.editor.close_dialog()
            self.editor = ClientEditorPopUp(
                self.dialog_controller,
                on_submit=self.on_save_client,
                contacts_map=self.contacts,
                on_error=lambda error: self.show_snack(
                    error,
                    is_error=True,
                ),
            )
            self.editor.open_dialog()
        elif intent == res_utils.RELOAD_INTENT:
            # Reload all data for the view
            self.reload_all_data()

    def load_all_clients(self):
        """Loads all clients from the store"""
        self.clients_to_display = self.intent.get_all_clients_as_map()

    def load_all_contacts(self):
        """Loads all contacts from the store"""
        self.contacts = self.intent.get_all_contacts_as_map()

    def refresh_clients(self):
        """Refreshes the clients list"""
        self.clients_container.controls.clear()
        for key in self.clients_to_display:
            client = self.clients_to_display[key]
            clientCard = ClientCard(
                client=client,
                on_edit=self.on_edit_client_clicked,
                on_delete=self.on_delete_client_clicked,
            )
            self.clients_container.controls.append(clientCard)

    def on_edit_client_clicked(self, client: Client):
        """Handles the edit button click event"""
        if self.editor is not None:
            self.editor.close_dialog()
        self.editor = ClientEditorPopUp(
            self.dialog_controller,
            on_submit=self.on_save_client,
            contacts_map=self.contacts,
            client=client,
            on_error=lambda error: self.show_snack(
                error,
                is_error=True,
            ),
        )
        self.editor.open_dialog()

    def on_delete_client_clicked(self, client: Client):
        """Handles the delete button click event"""
        if self.editor is not None:
            self.editor.close_dialog()
        # Open a confirmation dialog
        self.editor = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this client's info?\n{client.name}",
            on_proceed=self.on_delete_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=client.id,
        )
        self.editor.open_dialog()

    def on_delete_confirmed(self, client_id):
        """called when the user confirms the deletion of a client"""
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_client_by_id(client_id)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Client deleted!"
        self.show_snack(msg, is_error)
        if not is_error and client_id in self.clients_to_display:
            del self.clients_to_display[client_id]
            self.refresh_clients()
        self.loading_indicator.visible = False
        self.update_self()

    def on_save_client(self, client_to_save: Client):
        """Handles the save event from the client editor"""
        is_updating = client_to_save.id is not None
        self.loading_indicator.visible = True
        self.update_self()
        result: IntentResult = self.intent.save_client(client_to_save)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.clients_to_display[result.data.id] = result.data
            self.refresh_clients()
            msg = (
                "The client's info has been updated"
                if is_updating
                else "A new client has been added"
            )
            self.show_snack(msg, False)
        self.loading_indicator.visible = False
        self.update_self()

    def did_mount(self):
        """Called when the view is mounted"""
        self.reload_all_data()

    def reload_all_data(self):
        """Reloads all data for the view when the view is mounted or a reload-intent is received"""
        self.mounted = True
        self.loading_indicator.visible = True
        self.load_all_clients()
        count = len(self.clients_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            self.no_clients_control.visible = True
            self.clients_container.controls.clear()
        else:
            self.no_clients_control.visible = False
            self.refresh_clients()
        self.load_all_contacts()
        self.update_self()

    def build(self):
        """Builds the view"""
        view = Column(
            controls=[
                self.title_control,
                views.Spacer(md_space=True),
                Container(self.clients_container, expand=True),
            ],
        )
        return view

    def will_unmount(self):
        """Called when the view is unmounted"""
        self.mounted = False
        if self.editor:
            self.editor.dimiss_open_dialogs()
