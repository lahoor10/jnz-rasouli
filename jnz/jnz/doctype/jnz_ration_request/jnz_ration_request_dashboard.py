from frappe import _


def get_data():
    return {
        "heatmap": True,
        "heatmap_message": _("Ration Requests over time"),
        "fieldname": "rreq_project",
        "transactions": [
            {
                "label": _("Ration"),
                "items": ["JNZ Ration Request"],
            },
        ],
    }
