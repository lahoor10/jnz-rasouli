import frappe


WORKFLOW_NAME = "JNZ Food Request Approval Workflow"
DOCTYPE = "JNZ Food Request"


def ensure_workflow_state(state, docstatus=0, is_start=0, is_end=0):
    if not frappe.db.exists("Workflow State", state):
        frappe.get_doc({
            "doctype": "Workflow State",
            "workflow_state_name": state,
            "doc_status": docstatus,
            "is_start_state": is_start,
            "is_end_state": is_end
        }).insert(ignore_permissions=True)


def create_workflow():
    # جلوگیری از دوباره‌سازی
    if frappe.db.exists("Workflow", WORKFLOW_NAME):
        print("Workflow already exists")
        return

    # -----------------------
    # 1. CREATE STATES FIRST
    # -----------------------
    ensure_workflow_state("Draft", docstatus=0, is_start=1)
    ensure_workflow_state("Pending Site Supervisor")
    ensure_workflow_state("Pending Project Manager")
    ensure_workflow_state("Pending Security")
    ensure_workflow_state("Pending HR")
    ensure_workflow_state("Pending CEO Office")
    ensure_workflow_state("Pending CEO")
    ensure_workflow_state("Approved", docstatus=1, is_end=1)

    # -----------------------
    # 2. CREATE WORKFLOW
    # -----------------------
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": WORKFLOW_NAME,
        "document_type": DOCTYPE,
        "is_active": 1,
        "override_status": 1,

        "states": [
            {"state": "Draft", "doc_status": 0, "is_start_state": 1},

            {"state": "Pending Site Supervisor", "doc_status": 0},
            {"state": "Pending Project Manager", "doc_status": 0},
            {"state": "Pending Security", "doc_status": 0},
            {"state": "Pending HR", "doc_status": 0},
            {"state": "Pending CEO Office", "doc_status": 0},
            {"state": "Pending CEO", "doc_status": 0},

            {"state": "Approved", "doc_status": 1, "is_end_state": 1},
        ],

        "transitions": [
            {
                "state": "Draft",
                "action": "Submit",
                "next_state": "Pending Site Supervisor",
                "allowed": "JNZ_ROLE_Site_Supervisor"
            },
            {
                "state": "Pending Site Supervisor",
                "action": "Approve",
                "next_state": "Pending Project Manager",
                "allowed": "JNZ_ROLE_Site_Supervisor"
            },
            {
                "state": "Pending Project Manager",
                "action": "Approve",
                "next_state": "Pending Security",
                "allowed": "JNZ_ROLE__Project_Manager"
            },
            {
                "state": "Pending Security",
                "action": "Approve",
                "next_state": "Pending HR",
                "allowed": "JNZ_ROLE__Security_Department"
            },
            {
                "state": "Pending HR",
                "action": "Approve",
                "next_state": "Pending CEO Office",
                "allowed": "JNZ_ROLE__HR"
            },
            {
                "state": "Pending CEO Office",
                "action": "Approve",
                "next_state": "Pending CEO",
                "allowed": "JNZ_ROLE__CEO_Office"
            },
            {
                "state": "Pending CEO",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "JNZ_ROLE_CEO"
            },
        ]
    })

    workflow.insert(ignore_permissions=True)
    frappe.db.commit()

    print("✅ Workflow created successfully")


# ❗ مهم: فقط وقتی مستقیم اجرا شد
# if __name__ == "__main__":
#     create_workflow()   