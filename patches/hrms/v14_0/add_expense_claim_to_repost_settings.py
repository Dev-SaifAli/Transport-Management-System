import frappe


LEGACY_REPOST_SETTINGS_DOCTYPE = "Repost Accounting Ledger Settings"
# Frappe v16 moved repost configuration out of the legacy single DocType and
# into Accounts Settings. See erpnext.patches.v16_0.merge_repost_settings_to_accounts_settings.
ACCOUNTS_SETTINGS_DOCTYPE = "Accounts Settings"


def execute():
	"""
	Add `Expense Claim` to Repost settings.

	Frappe/ERPNext v16 removed the legacy `Repost Accounting Ledger Settings`
	single DocType and replaced it with `Accounts Settings.repost_allowed_types`.
	When the legacy DocType is absent the equivalent v16 setting is applied
	instead, so this patch stays idempotent and correct on both generations.
	"""
	allowed_types = ["Expense Claim"]

	if frappe.db.exists("DocType", LEGACY_REPOST_SETTINGS_DOCTYPE):
		repost_settings = frappe.get_doc(LEGACY_REPOST_SETTINGS_DOCTYPE)
		for document_type in allowed_types:
			repost_settings.append(
				"allowed_types", {"document_type": document_type, "allowed": True}
			)
		repost_settings.save()
		return

	# v16 and later: the equivalent setting lives on Accounts Settings.
	accounts_settings = frappe.get_doc(ACCOUNTS_SETTINGS_DOCTYPE)
	existing = {row.document_type for row in accounts_settings.repost_allowed_types}
	changed = False
	for document_type in allowed_types:
		if document_type not in existing:
			accounts_settings.append("repost_allowed_types", {"document_type": document_type})
			changed = True

	if changed:
		accounts_settings.save()
