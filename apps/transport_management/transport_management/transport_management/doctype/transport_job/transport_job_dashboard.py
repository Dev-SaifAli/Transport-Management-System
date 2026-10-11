from frappe import _


def get_data():
	return {
		"fieldname": "transport_job",
		"transactions": [
			{
				"label": _("Execution"),
				"items": ["Transport Trip"],
			}
		],
	}
