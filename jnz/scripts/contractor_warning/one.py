import frappe

def create_roles():
    roles = [
        "JNZ_ROLE_Notifier", 
        "JNZ_ROLE_Technical_Office_Manager", 
        "JNZ_ROLE_Technical_Engineering_Deputy", 
        "JNZ_ROLE_Legal_Department", 
        "JNZ_ROLE_Secretariat"
    ]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

def create_workflow_actions_and_states():
    # Create States
    states = [
        "Draft", "Technical Review", "Engineering Deputy Review", 
        "Legal Review", "Approved for Issue", 
        "Pending Dispatch", "Issued"
    ]
    for state in states:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert(ignore_permissions=True)

    # Create Actions
    actions = [
    "Submit for Technical Review",
    "Return for Revision",
    "Forward to Engineering Deputy",
    "Request Legal Review",
    "Approve for Letter Issuance",
    "Issue Warning Letter"
]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)

def create_doctypes():
    # 0. JNZ Contractor (Because it was NOT in your list, we must create it first)
    if not frappe.db.exists("DocType", "JNZ Contractor"):
        doc0 = frappe.get_doc({
            "doctype": "DocType",
            "name": "JNZ Contractor",
            "module": "JNZ",
            "custom": 0,
            "autoname": "field:contractor_name",
            "fields": [
                {"fieldname": "contractor_name", "label": "Contractor Name", "fieldtype": "Data", "reqd": 1, "unique": 1},
                {"fieldname": "phone", "label": "Phone Number", "fieldtype": "Data"}
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
        })
        doc0.insert(ignore_permissions=True)

    # 1. JNZ Contractor Warning (Process Split 1)
    if not frappe.db.exists("DocType", "JNZ Contractor Warning"):
        doc1 = frappe.get_doc({
            "doctype": "DocType",
            "name": "JNZ Contractor Warning",
            "module": "JNZ",
            "custom": 0,
            "autoname": "format:WARN-{YYYY}-{#####}", 
            "fields": [
                {"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "JNZ Project", "reqd": 1}, # Exists in your list
                {"fieldname": "contractor", "label": "Contractor", "fieldtype": "Link", "options": "JNZ Contractor", "reqd": 1}, # Created above
                {"fieldname": "reason", "label": "Reason for Warning", "fieldtype": "Text Editor", "reqd": 1},
                {"fieldname": "letter_created", "label": "Letter Created", "fieldtype": "Check", "hidden": 1, "default": "0"}
            ],
            "permissions": [{"role": "JNZ_ROLE_Notifier", "read": 1, "write": 1, "create": 1}]
        })
        doc1.insert(ignore_permissions=True)

    # 2. JNZ Warning Letter (Process Split 2)
    if not frappe.db.exists("DocType", "JNZ Warning Letter"):
        doc2 = frappe.get_doc({
            "doctype": "DocType",
            "name": "JNZ Warning Letter",
            "module": "JNZ",
            "custom": 0,
            "autoname": "format:LTR-{YYYY}-{#####}", 
            "fields": [
                {"fieldname": "warning_reference", "label": "Warning Reference", "fieldtype": "Link", "options": "JNZ Contractor Warning", "reqd": 1, "read_only": 1},
                {"fieldname": "automation_number", "label": "Automation Number", "fieldtype": "Data"},
                {"fieldname": "postal_tracking", "label": "Postal Tracking Number", "fieldtype": "Data"}
            ],
            "permissions": [{"role": "JNZ_ROLE_Secretariat", "read": 1, "write": 1}]
        })
        doc2.insert(ignore_permissions=True)

def create_workflows():
    # 1. Workflow for JNZ Contractor Warning
    if not frappe.db.exists("Workflow", "JNZ Contractor Warning Workflow"):
        wf1 = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "JNZ Contractor Warning Workflow",
            "document_type": "JNZ Contractor Warning",
            "is_active": 1,
            "states": [
                {"state": "Draft", "doc_status": 0, "allow_edit": "JNZ_ROLE_Notifier"},
                {"state": "Technical Review", "doc_status": 0, "allow_edit": "JNZ_ROLE_Technical_Office_Manager"},
                {"state": "Engineering Deputy Review", "doc_status": 0, "allow_edit": "JNZ_ROLE_Technical_Engineering_Deputy"},
                {"state": "Legal Review", "doc_status": 0, "allow_edit": "JNZ_ROLE_Legal_Department"},
                {"state": "Approved for Issue", "doc_status": 1, "allow_edit": "JNZ_ROLE_Notifier"}
            ],
            "transitions": [
                {
                    "state": "Draft",
                    "action": "Submit for Technical Review",
                    "next_state": "Technical Review",
                    "allowed": "JNZ_ROLE_Notifier"
                },
                {
                    "state": "Technical Review",
                    "action": "Return for Revision",
                    "next_state": "Draft",
                    "allowed": "JNZ_ROLE_Technical_Office_Manager"
                },
                {
                    "state": "Technical Review",
                    "action": "Forward to Engineering Deputy",
                    "next_state": "Engineering Deputy Review",
                    "allowed": "JNZ_ROLE_Technical_Office_Manager"
                },
                {
                    "state": "Engineering Deputy Review",
                    "action": "Return for Revision",
                    "next_state": "Draft",
                    "allowed": "JNZ_ROLE_Technical_Engineering_Deputy"
                },
                {
                    "state": "Engineering Deputy Review",
                    "action": "Request Legal Review",
                    "next_state": "Legal Review",
                    "allowed": "JNZ_ROLE_Technical_Engineering_Deputy"
                },
                {
                    "state": "Engineering Deputy Review",
                    "action": "Approve for Letter Issuance",
                    "next_state": "Approved for Issue",
                    "allowed": "JNZ_ROLE_Technical_Engineering_Deputy"
                },
                {
                    "state": "Legal Review",
                    "action": "Approve for Letter Issuance",
                    "next_state": "Approved for Issue",
                    "allowed": "JNZ_ROLE_Legal_Department"
                }
            ]
        })
        wf1.insert(ignore_permissions=True)

    # 2. Workflow for JNZ Warning Letter
    if not frappe.db.exists("Workflow", "JNZ Warning Letter Workflow"):
        wf2 = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "JNZ Warning Letter Workflow",
            "document_type": "JNZ Warning Letter",
            "is_active": 1,
            "states": [
                {"state": "Pending Dispatch", "doc_status": 0, "allow_edit": "JNZ_ROLE_Secretariat"},
                {"state": "Issued", "doc_status": 1, "allow_edit": "JNZ_ROLE_Secretariat"}
            ],
            "transitions": [
                {
                    "state": "Pending Dispatch",
                    "action": "Issue Warning Letter",
                    "next_state": "Issued",
                    "allowed": "JNZ_ROLE_Secretariat"
                }
            ]
        })
        wf2.insert(ignore_permissions=True)
def run_all():
    frappe.flags.in_test = True 
    create_roles()
    create_workflow_actions_and_states()
    create_doctypes()
    create_workflows()
    frappe.db.commit()
    print("JNZ Architecture for Warnings created successfully!")