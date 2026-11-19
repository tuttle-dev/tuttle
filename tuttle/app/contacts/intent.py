from ...model import Address, ClientContact, Contact
from ..core.abstractions import CrudIntent
from ..core.intent_result import IntentResult, fails_with


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

    @fails_with("Failed to load clients for this contact", append_exception=True)
    def get_clients_for_contact(self, contact_id: int) -> IntentResult:
        """Return ClientContact associations enriched with client_name."""
        assocs = self.query_where(ClientContact, "contact_id", contact_id)
        result = []
        for a in assocs:
            d = a.model_dump()
            if a.client:
                d["client_name"] = a.client.name
            result.append(d)
        return IntentResult(was_intent_successful=True, data=result)

    @fails_with("Failed to add client to contact", append_exception=True)
    def add_client_to_contact(self, contact_id: int, client_id: int, role: str | None = None) -> IntentResult:
        """Create a ClientContact association from the contact side."""
        assoc = ClientContact(client_id=client_id, contact_id=contact_id, role=role)
        self.store(assoc)
        return IntentResult(was_intent_successful=True, data=assoc)

    @fails_with("Failed to remove client from contact", append_exception=True)
    def remove_client_contact(self, association_id: int) -> IntentResult:
        """Delete a ClientContact association by its id."""
        self.delete_by_id(ClientContact, association_id)
        return IntentResult(was_intent_successful=True)

    @fails_with("Failed to update contact role", append_exception=True)
    def update_client_contact_role(self, association_id: int, role: str | None) -> IntentResult:
        """Update the role on a ClientContact association."""
        assoc = self.query_by_id(ClientContact, association_id)
        if assoc is None:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Association not found.",
            )
        assoc.role = role
        self.store(assoc)
        return IntentResult(was_intent_successful=True, data=assoc)

    def _validated_save(self, contact: Contact) -> IntentResult:
        if contact.address and contact.address.is_empty:
            contact.address = None
            contact.address_id = None
        return self.save(contact)
