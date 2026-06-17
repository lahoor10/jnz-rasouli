from frappe import _


def get_data():
    return {
        "heatmap": True,
        "heatmap_message": _("Food Requests over time"),
        "fieldname": "freq_project",
        "transactions": [
            {
                "label": _("Food"),
                "items": ["JNZ Food Request"],
            },
        ],
    }
