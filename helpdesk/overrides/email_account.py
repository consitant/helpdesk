import re
from email import message_from_string

import frappe
from frappe import _
from frappe.core.doctype.communication.communication import Communication
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.email.doctype.email_queue.email_queue import EmailQueue
from frappe.email.receive import InboundMail

# Eine im Betreff genannte Ticketnummer, an JEDER Position: "#2062", "(#2062)", "# 2062".
# Frappe selbst liest nur das Betreffs-ENDE (receive.py get_reference_name_from_subject).
TICKET_TOKEN = re.compile(r"#\s?(\d{3,5})")

# Absenderdomänen, deren Mitarbeiter die #nummer als Ablageanweisung setzen dürfen.
# Bewusst NICHT über die Rolle "Agent" geprüft: die externen Partner tragen sie ebenfalls.
# Die Domänenprüfung schlägt bei einem neuen externen Absender fehl (fail closed),
# eine Rollenprüfung würde ihn stillschweigend mit aufnehmen (fail open).
INTERNAL_EMAIL_DOMAINS = ("axovend.com",)


class CustomInboundMail(InboundMail):
    """
    Extend InboundMail with robust thread stitching for forwarded emails.
       1. Run the standard Frappe parent_communication lookups first (In-Reply-To → Communication, EmailQueue, communication-name fallback)
       2. If still no parent, use the References header from emails, which may contain multiple message IDs in a thread

    Zusätzlich: eine von einem internen Mitarbeiter in den Betreff geschriebene Ticketnummer
    schlägt die Thread-Kopfzeilen (siehe reference_document).
    """

    def _find_communication_by_message_id(self, msg_id: str):
        """Return a Communication for msg_id, checking both Communication and EmailQueue."""
        # Direct hit: incoming email stored its message_id on Communication
        comm = Communication.find_one_by_filters(
            message_id=msg_id, order_by="creation DESC"
        )
        if comm:
            return comm

        # Outgoing email: message_id lives in EmailQueue, not on Communication
        eq = EmailQueue.find_one_by_filters(message_id=msg_id)
        if eq and eq.communication:
            return Communication.find(eq.communication, ignore_error=True) or None

        return None

    def parent_communication(self):
        # Respect cached result from any prior call on this instance
        if self._parent_communication is not None:
            return self._parent_communication

        # Run the standard Frappe lookup method first. Checks for finding in reply to in Communication then if not found it looks in EmailQueue
        result = super().parent_communication()
        if result:
            return result

        # fallback: use the References header from emails
        references_raw = self.mail.get("References") or ""
        ref_ids = re.findall(r"<([^>]+)>", references_raw)

        for ref_id in reversed(ref_ids):
            communication = self._find_communication_by_message_id(ref_id)
            if communication:
                self._parent_communication = communication
                return self._parent_communication

        self._parent_communication = ""
        return self._parent_communication

    def _sender_is_internal(self) -> bool:
        """True, wenn die Mail von einem aktiven internen Systemnutzer kommt."""
        sender = (self.from_email or "").lower()
        if not sender.endswith(tuple(f"@{d}" for d in INTERNAL_EMAIL_DOMAINS)):
            return False
        return bool(
            frappe.db.get_value(
                "User",
                {"email": sender, "enabled": 1, "user_type": "System User"},
                cache=True,
            )
        )

    def ticket_from_subject(self):
        """Ticketnummer, die der Betreff eindeutig benennt — sonst None.

        Regel: alle "#nnnn" im Betreff einsammeln, nur die behalten, die ein existierendes
        HD Ticket sind, und nur bei GENAU EINEM Treffer entscheiden. Damit fallen
        Fremdreferenzen (maxcrc #43778, #37051, Jira-Nummern) ohne Sonderregeln heraus,
        und ein mehrdeutiger Betreff wird der nativen Logik überlassen statt geraten.
        """
        if not self.subject:
            return None

        candidates = {int(n) for n in TICKET_TOKEN.findall(self.subject)}
        if not candidates:
            return None

        existing = frappe.get_all(
            "HD Ticket",
            filters={"name": ("in", sorted(candidates))},
            pluck="name",
        )
        return existing[0] if len(existing) == 1 else None

    def reference_document(self):
        """Eine vom eigenen Personal getippte #nummer schlägt die Thread-Kopfzeilen.

        Nativ entscheidet Frappe in dieser Reihenfolge: In-Reply-To -> Email Queue,
        In-Reply-To -> Communication, und ERST DANN der Betreff. Outlook hängt an jede
        Antwort und jede Weiterleitung eine Thread-Kennung, deshalb wurde der Betreff
        praktisch nie gelesen — gemessen am Bestand 091226: 23 von 23 Fehlablagen hingen
        an einem Thread, 5 davon trugen die Nummer sogar korrekt am Betreffsende.

        Die #nummer ist eine bewusste Ablageanweisung unserer Leute, keine Kundendatei.
        Deshalb gilt der Vorrang nur für interne Absender.
        """
        if self._reference_document is not None:
            return self._reference_document

        append_to = self.append_to if self.email_account.use_imap else self.email_account.append_to
        if append_to == "HD Ticket" and self._sender_is_internal():
            ticket = self.ticket_from_subject()
            if ticket:
                document = self.get_doc("HD Ticket", ticket, ignore_error=True)
                if document:
                    # Der Thread-Elternteil darf nur stehen bleiben, wenn er am selben
                    # Ticket hängt. Sonst zeigte in_reply_to (receive.py _build_communication_doc)
                    # auf eine Communication an einem FREMDEN Ticket und die
                    # Antwort-Verkettung liefe über Ticketgrenzen.
                    parent = self.parent_communication()
                    if parent and str(getattr(parent, "reference_name", "")) != str(document.name):
                        self._parent_communication = ""

                    self._reference_document = document
                    return self._reference_document

        return super().reference_document()


class CustomEmailAccount(EmailAccount):
    def get_inbound_mails(self) -> list[InboundMail]:
        """retrive and return inbound mails."""
        mails = []

        def process_mail(messages, append_to=None):
            for index, message in enumerate(messages.get("latest_messages", [])):
                try:
                    _msg = message_from_string(
                        message.decode("utf-8", errors="replace")
                    )

                    # Important: If the email is auto-generated, we do not create a ticket
                    if _msg.get("X-Auto-Generated"):
                        continue

                    uid = (
                        messages["uid_list"][index]
                        if messages.get("uid_list")
                        else None
                    )
                    seen_status = messages.get("seen_status", {}).get(uid)
                    if self.email_sync_option != "UNSEEN" or seen_status != "SEEN":
                        _inbound_mail = CustomInboundMail(
                            message,
                            self,
                            frappe.safe_decode(uid),
                            seen_status,
                            append_to,
                        )
                        mails.append(_inbound_mail)
                except Exception as e:
                    # Log the error but continue processing other emails
                    frappe.log_error(
                        title=_(
                            "Error processing email at index {0}, message: {1}"
                        ).format(index, e),
                        message=frappe.get_traceback(),
                    )
                    self.handle_bad_emails(index, message, frappe.get_traceback())
                    continue

        if not self.enable_incoming:
            return []

        try:
            if self.service == "Frappe Mail":
                frappe_mail_client = self.get_frappe_mail_client()
                messages = frappe_mail_client.pull_raw(
                    last_received_at=self.last_synced_at
                )
                process_mail(messages)
                self.db_set(
                    "last_synced_at",
                    messages["last_received_at"],
                    update_modified=False,
                )
            else:
                email_sync_rule = self.build_email_sync_rule()
                email_server = self.get_incoming_server(
                    in_receive=True, email_sync_rule=email_sync_rule
                )
                if self.use_imap:
                    # process all given imap folder
                    for folder in self.imap_folder:
                        if email_server.select_imap_folder(folder.folder_name):
                            email_server.settings["uid_validity"] = folder.uidvalidity
                            messages = (
                                email_server.get_messages(
                                    folder=f'"{folder.folder_name}"'
                                )
                                or {}
                            )
                            process_mail(messages, folder.append_to)
                else:
                    # process the pop3 account
                    messages = email_server.get_messages() or {}
                    process_mail(messages)

                # close connection to mailserver
                email_server.logout()
        except Exception:
            self.log_error(
                title=_("Error while connecting to email account {0}").format(self.name)
            )
            return []

        return mails
