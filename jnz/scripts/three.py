import frappe

def run():
    frappe.flags.in_setup = True
    print("🚀 Starting Setup for JNZ Contract (Phase 3)...")

    if not frappe.conf.developer_mode:
        print("❌ ERROR: Developer mode is not enabled.")
        return

    try:
        ensure_roles()
        ensure_workflow_states()
        ensure_workflow_actions()
        ensure_doctype()
        ensure_workflow()
        
        frappe.db.commit()
        print("✅ Phase 3 Setup completed!")
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Setup failed: {str(e)}")

def ensure_roles():
    roles = ["JNZ_ROLE_Technical_Office_Manager", "JNZ_ROLE_CEO", "JNZ_ROLE_Secretariat"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)

def ensure_workflow_states():
    states = [
        {"name": "Contract Drafting", "doc_status": 0},
        {"name": "Legal Review", "doc_status": 0},
        {"name": "Awaiting CEO Signature", "doc_status": 0},
        {"name": "Signed & Executed", "doc_status": 1},
        {"name": "Contract Void", "doc_status": 2}
    ]
    for state in states:
        if not frappe.db.exists("Workflow State", state["name"]):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state["name"],
                "doc_status": state["doc_status"]
            }).insert(ignore_permissions=True)

def ensure_workflow_actions():
    actions = ["Send to Legal", "Approve for Signature", "Sign & Execute", "Void Contract"]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)

def ensure_doctype():
    doctype_name = "JNZ Contract"
    if frappe.db.exists("DocType", doctype_name): return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "JNZ",
        "custom": 0,
        "is_submittable": 1,
        "naming_rule": "Expression",
        "autoname": "JNZ-CONT-.YYYY.-.#####",
        "fields": [
            {"fieldname": "procurement_ref", "label": "سند استعلام مرجع", "fieldtype": "Link", "options": "JNZ Procurement", "reqd": 1},
            {"fieldname": "contractor_name", "label": "پیمانکار", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "final_amount", "label": "مبلغ نهایی قرارداد", "fieldtype": "Currency", "read_only": 1},
            {"fieldname": "contract_text", "label": "متن قرارداد", "fieldtype": "Text Editor", "reqd": 1},
            {"fieldname": "workflow_state", "label": "وضعیت فرآیند", "fieldtype": "Link", "options": "Workflow State", "read_only": 1}
        ],
        "permissions": [
            {"role": "JNZ_ROLE_Technical_Office_Manager", "read": 1, "write": 1, "create": 1},
            {"role": "JNZ_ROLE_CEO", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Secretariat", "read": 1}
        ]
    })
    doc.insert(ignore_permissions=True)

def ensure_workflow():
    workflow_name = "JNZ Contract Workflow"
    if frappe.db.exists("Workflow", workflow_name): frappe.delete_doc("Workflow", workflow_name)

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": "JNZ Contract",
        "is_active": 1,
        "states": [
            {"state": "Contract Drafting", "doc_status": 0, "allow_edit": "JNZ_ROLE_Technical_Office_Manager"},
            {"state": "Legal Review", "doc_status": 0, "allow_edit": "JNZ_ROLE_Secretariat"},
            {"state": "Awaiting CEO Signature", "doc_status": 0, "allow_edit": "JNZ_ROLE_CEO"},
            {"state": "Signed & Executed", "doc_status": 1, "allow_edit": "System Manager"},
            {"state": "Contract Void", "doc_status": 2, "allow_edit": "System Manager"}
        ],
        "transitions": [
            {"state": "Contract Drafting", "action": "Send to Legal", "next_state": "Legal Review", "allowed": "JNZ_ROLE_Technical_Office_Manager"},
            {"state": "Legal Review", "action": "Approve for Signature", "next_state": "Awaiting CEO Signature", "allowed": "JNZ_ROLE_Secretariat"},
            {"state": "Awaiting CEO Signature", "action": "Sign & Execute", "next_state": "Signed & Executed", "allowed": "JNZ_ROLE_CEO"}
        ]
    })
    doc.insert(ignore_permissions=True)