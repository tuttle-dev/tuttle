from ..core.abstractions import CrudIntent
from ..core.intent_result import IntentResult
from ...model import Address, Contact, ClientContact


class ContactsIntent(CrudIntent):
    """Contact CRUD with validation and referential integrity."""

    entity_type = Contact
    entity_name = "contact"
    deletion_guards = [
        ("invoicing_contact_of", "clients", lambda c: c.name),
    ]
    __save_nested__ = {"address": Address}
    __save_skip__ = {"invoicing_contact_of", "client_contacts"}

    def get_all_clients_as_map(self) -> dict:
        """Return all clients as {id: {id, name}} for the association picker."""
        from ...model import Client

        try:
            clients = self.query(Client)
            return {c.id: {"id": c.id, "name": c.name} for c in clients}
        except Exception:
            return {}

    def get_clients_for_contact(self, contact_id: int) -> IntentResult:
        """Return ClientContact associations enriched with client_name."""
        try:
            assocs = self.query_where(ClientContact, "contact_id", contact_id)
            result = []
            for a in assocs:
                d = a.model_dump()
                if a.client:
                    d["client_name"] = a.client.name
                result.append(d)
            return IntentResult(was_intent_successful=True, data=result)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load clients for this contact: {e}",
                log_message=f"get_clients_for_contact({contact_id}): {e}",
                exception=e,
            )

    def add_client_to_contact(
        self, contact_id: int, client_id: int, role: str | None = None
    ) -> IntentResult:
        """Create a ClientContact association from the contact side."""
        try:
            assoc = ClientContact(client_id=client_id, contact_id=contact_id, role=role)
            self.store(assoc)
            return IntentResult(was_intent_successful=True, data=assoc)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to add client to contact: {e}",
                log_message=f"add_client_to_contact({contact_id}, {client_id}): {e}",
                exception=e,
            )

    def remove_client_contact(self, association_id: int) -> IntentResult:
        """Delete a ClientContact association by its id."""
        try:
            self.delete_by_id(ClientContact, association_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to remove client from contact: {e}",
                log_message=f"remove_client_contact({association_id}): {e}",
                exception=e,
            )

    def update_client_contact_role(
        self, association_id: int, role: str | None
    ) -> IntentResult:
        """Update the role on a ClientContact association."""
        try:
            assoc = self.query_by_id(ClientContact, association_id)
            if assoc is None:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg="Association not found.",
                )
            assoc.role = role
            self.store(assoc)
            return IntentResult(was_intent_successful=True, data=assoc)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to update contact role: {e}",
                log_message=f"update_client_contact_role({association_id}): {e}",
                exception=e,
            )

    def _validated_save(self, contact: Contact) -> IntentResult:
        if not contact.first_name or not contact.last_name:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Saving contact failed. A name is required.",
            )
        if contact.address and contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Saving contact failed. Please specify the address.",
            )
        return self.save(contact)
