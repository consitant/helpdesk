import frappe
from frappe.query_builder import DocType, Query


def query_get_one(q: Query) -> dict:
    r = q.run(as_dict=True)

    if len(r) != 1:
        return

    return r.pop()


def default_outgoing_email_account():
    QBEmailAccount = DocType("Email Account")

    r = (
        frappe.qb.from_(QBEmailAccount)
        .select(QBEmailAccount.star)
        .where(QBEmailAccount.default_outgoing == 1)
        .limit(1)
    )

    return query_get_one(r)


def is_ticket_mailbox(email_account: str) -> bool:
    """Check whether an `Email Account` is a helpdesk mailbox.

    Only accounts that receive tickets (`Append To` = HD Ticket, either on the
    account itself or on one of its IMAP folders) may act as the sender of an
    agent reply. Departmental outgoing accounts a user happens to have linked
    in `User Email` (purchasing, accounting, ...) must never leak into customer
    facing ticket mails.
    """
    if not email_account:
        return False

    if frappe.db.get_value("Email Account", email_account, "append_to") == "HD Ticket":
        return True

    QBImapFolder = DocType("IMAP Folder")

    r = (
        frappe.qb.from_(QBImapFolder)
        .select(QBImapFolder.name)
        .where(QBImapFolder.parent == email_account)
        .where(QBImapFolder.append_to == "HD Ticket")
        .limit(1)
    ).run()

    return bool(r)


def default_ticket_outgoing_email_account():
    QBEmailAccount = DocType("Email Account")
    QBImapFolder = DocType("IMAP Folder")

    r = (
        frappe.qb.from_(QBEmailAccount)
        .select(QBEmailAccount.star)
        .where(QBEmailAccount.default_outgoing == 1)
        .inner_join(QBImapFolder)
        .on(QBImapFolder.parent == QBEmailAccount.name)
        .where(QBImapFolder.append_to == "HD Ticket")
        .limit(1)
    )

    return query_get_one(r)
