"""
JNZ — Module Def Setup  (§3)

Guarantees Module Def records exist with the correct app_name so no DocType
is treated as orphaned and deleted on bench migrate.

Wire into hooks.py:
    after_install = "jnz.module_def_setup.ensure_module_defs"
    after_migrate  = "jnz.module_def_setup.ensure_module_defs"
"""

import json
import os

import frappe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME    = "jnz"
APP_MODULES = [
    "JNZ",
]
WORKSPACE_FIXTURE = ("fixtures", "workspace.json")

# ---------------------------------------------------------------------------
# Roles referenced by the JNZ DocType permissions. They must exist (with desk
# access) so users can be granted them; otherwise only Administrator, who
# bypasses permissions, can open any JNZ DocType.
# ---------------------------------------------------------------------------
ROLES = [
    "JNZ_ROLE_CEO",
    "JNZ_ROLE_Site_Supervisor",
    "JNZ_ROLE__CEO_Office",
    "JNZ_ROLE__HR",
    "JNZ_ROLE__Project_Manager",
    "JNZ_ROLE__Security_Department",
]

# ---------------------------------------------------------------------------
# Dashboard building blocks — created live against the JNZ DocTypes so the
# workspace dashboard reflects real data (Number Cards + time-series Charts).
# Labels are English (§9); Farsi lives in translations/fa.csv.
# ---------------------------------------------------------------------------
NUMBER_CARDS = [
    {
        "name": "JNZ Active Projects",
        "label": "JNZ Active Projects",
        "type": "Document Type",
        "document_type": "JNZ Project",
        "function": "Count",
        "filters_json": json.dumps([["JNZ Project", "active", "=", 1]]),
        "is_public": 1,
        "show_percentage_stats": 1,
        "stats_time_interval": "Monthly",
        "color": "#2e7d32",
    },
    {
        "name": "JNZ Ration Items",
        "label": "JNZ Ration Items",
        "type": "Document Type",
        "document_type": "JNZ Item",
        "function": "Count",
        "filters_json": json.dumps([["JNZ Item", "active", "=", 1]]),
        "is_public": 1,
        "show_percentage_stats": 1,
        "stats_time_interval": "Monthly",
        "color": "#ff8f00",
    },
    {
        "name": "JNZ Ration Requests",
        "label": "JNZ Ration Requests",
        "type": "Document Type",
        "document_type": "JNZ Ration Request",
        "function": "Count",
        "filters_json": "[]",
        "is_public": 1,
        "show_percentage_stats": 1,
        "stats_time_interval": "Monthly",
        "color": "#388e3c",
    },
    {
        "name": "JNZ Food Requests",
        "label": "JNZ Food Requests",
        "type": "Document Type",
        "document_type": "JNZ Food Request",
        "function": "Count",
        "filters_json": "[]",
        "is_public": 1,
        "show_percentage_stats": 1,
        "stats_time_interval": "Monthly",
        "color": "#43a047",
    },
]

DASHBOARD_CHARTS = [
    {
        "name": "JNZ Ration Requests Trend",
        "chart_name": "JNZ Ration Requests Trend",
        "chart_type": "Count",
        "document_type": "JNZ Ration Request",
        "based_on": "rreq_request_date",
        "timeseries": 1,
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "type": "Bar",
        "filters_json": "[]",
        "is_public": 1,
        "color": "#2e7d32",
    },
    {
        "name": "JNZ Food Requests Trend",
        "chart_name": "JNZ Food Requests Trend",
        "chart_type": "Count",
        "document_type": "JNZ Food Request",
        "based_on": "freq_request_date",
        "timeseries": 1,
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "type": "Line",
        "filters_json": "[]",
        "is_public": 1,
        "color": "#ff8f00",
    },
]


def ensure_module_defs():
    for module_name in APP_MODULES:
        existing = frappe.db.get_value(
            "Module Def",
            module_name,
            ["name", "app_name"],
            as_dict=True,
        )
        if not existing:
            doc             = frappe.new_doc("Module Def")
            doc.module_name = module_name
            doc.app_name    = APP_NAME
            doc.insert(ignore_permissions=True)
        elif existing.app_name != APP_NAME:
            frappe.db.set_value("Module Def", module_name, "app_name", APP_NAME)

    frappe.db.commit()


def _upsert(doctype, records):
    """Create or update each record by its explicit `name`."""
    for record in records:
        record = dict(record)
        name = record.get("name")
        if name and frappe.db.exists(doctype, name):
            doc = frappe.get_doc(doctype, name)
            doc.update(record)
        else:
            doc = frappe.new_doc(doctype)
            doc.update(record)
            if name:
                doc.name = name
        doc.flags.ignore_permissions = True
        doc.save()
    frappe.db.commit()


def ensure_roles():
    """Create the JNZ roles (with desk access) if they don't exist yet."""
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)
    frappe.db.commit()


def ensure_number_cards():
    """Upsert the JNZ dashboard Number Cards (live counts from DocTypes)."""
    _upsert("Number Card", NUMBER_CARDS)


def ensure_dashboard_charts():
    """Upsert the JNZ dashboard time-series Charts."""
    _upsert("Dashboard Chart", DASHBOARD_CHARTS)


def ensure_jnz_workspace():
    """
    Upsert the JNZ workspace from fixtures/workspace.json on every migrate.

    Workspace fixtures import unreliably (link validation against roles, cache
    state), so we create/update the record directly here instead. Runs from
    after_install and after_migrate.
    """
    path = os.path.join(frappe.get_app_path(APP_NAME), *WORKSPACE_FIXTURE)
    if not os.path.exists(path):
        return

    with open(path) as f:
        data = json.load(f)

    for record in data:
        name = record["name"]
        if frappe.db.exists("Workspace", name):
            doc = frappe.get_doc("Workspace", name)
            doc.update(record)
        else:
            doc = frappe.new_doc("Workspace")
            doc.update(record)
            doc.name = name
        doc.flags.ignore_permissions = True
        doc.flags.ignore_links = True
        doc.save()

    frappe.db.commit()
