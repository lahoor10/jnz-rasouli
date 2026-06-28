import frappe

def run():
    frappe.flags.in_setup = True
    print("🚀 Starting Setup for JNZ Civil Service Request (Phase 1) - Flexible Workflow...")
    
    try:
        ensure_roles()
        ensure_workflow_states()
        ensure_workflow_actions()
        ensure_doctype()
        ensure_workflow()
        
        frappe.db.commit()
        print("✅ Setup completed successfully!")
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Setup failed: {str(e)}")

def ensure_roles():
    roles = [
        "JNZ_ROLE_Executive_Expert",
        "JNZ_ROLE_Project_Technical_Office",
        "JNZ_ROLE_Site_Supervisor",
        "JNZ_ROLE_Department_Manager",
        "JNZ_ROLE_HQ_Technical_Office"
    ]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)

def ensure_workflow_states():
    # تمام مراحل میانی روی 0 هستند تا فرم قابل ویرایش باشد
    states = [
        {"name": "Draft Initialization", "doc_status": 0},
        {"name": "Under Technical Review", "doc_status": 0},
        {"name": "Awaiting Site Confirmation", "doc_status": 0},
        {"name": "Under Departmental Assessment", "doc_status": 0},
        {"name": "Pending HQ Final Validation", "doc_status": 0},
        {"name": "Returned for Revision", "doc_status": 0}, # وضعیت عودت برای اصلاح (اضافه شد)
        {"name": "Approved for Procurement", "doc_status": 1}, # فقط این مرحله فرم را سابمیت و قفل می‌کند
        {"name": "Request Cancelled", "doc_status": 2} # ابطال کامل
    ]
    
    for state in states:
        if not frappe.db.exists("Workflow State", state["name"]):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state["name"],
                "doc_status": state["doc_status"],
                "style": "Danger" if "Cancelled" in state["name"] else "Success" if "Approved" in state["name"] else "Warning" if "Returned" in state["name"] else "Primary"
            }).insert(ignore_permissions=True)

def ensure_workflow_actions():
    actions = [
        "Submit Initial Request",
        "Endorse Technical Merits",
        "Validate Site Necessity",
        "Confirm Departmental Scope",
        "Finalize Technical Approval",
        "Return for Revision", # دکمه مشترک برای عودت به کارشناس اجرایی
        "Re-submit Request", # ارسال مجدد پس از اصلاح
        "Cancel Request" # ابطال قطعی
    ]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)

def ensure_doctype():
    doctype_name = "JNZ Civil Service Request"
    if frappe.db.exists("DocType", doctype_name):
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "JNZ",
        "custom": 1,
        "is_submittable": 1,
        "track_changes": 1,
        "naming_rule": "Expression",
        "autoname": "JNZ-CSR-.YYYY.-.#####",
        "fields": [
            {"fieldname": "title", "label": "عنوان درخواست خدمات", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
            {"fieldname": "project", "label": "کارگاه/پروژه مبدا", "fieldtype": "Link", "options": "JNZ Project", "reqd": 1, "in_list_view": 1},
            {"fieldname": "request_date", "label": "تاریخ ایجاد", "fieldtype": "Date", "default": "Today", "read_only": 1, "in_list_view": 1},
            {"fieldname": "description", "label": "شرح دقیق خدمات مورد نیاز", "fieldtype": "Text Editor", "reqd": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "workflow_state", "label": "وضعیت فرآیند", "fieldtype": "Link", "options": "Workflow State", "read_only": 1, "in_list_view": 1},
            {"fieldname": "amended_from", "label": "اصلاح شده از", "fieldtype": "Link", "options": "JNZ Civil Service Request", "read_only": 1, "print_hide": 1}
        ],
        "permissions": [
            {"role": "JNZ_ROLE_Executive_Expert", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            {"role": "JNZ_ROLE_Project_Technical_Office", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Site_Supervisor", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Department_Manager", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_HQ_Technical_Office", "read": 1, "write": 1}
        ]
    })
    doc.insert(ignore_permissions=True)

def ensure_workflow():
    workflow_name = "JNZ Civil Service Request Workflow"
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name)

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": "JNZ Civil Service Request",
        "is_active": 1,
        "send_email_alert": 0,
        "states": [
            {"state": "Draft Initialization", "doc_status": 0, "allow_edit": "JNZ_ROLE_Executive_Expert"},
            {"state": "Under Technical Review", "doc_status": 0, "allow_edit": "JNZ_ROLE_Project_Technical_Office"},
            {"state": "Awaiting Site Confirmation", "doc_status": 0, "allow_edit": "JNZ_ROLE_Site_Supervisor"},
            {"state": "Under Departmental Assessment", "doc_status": 0, "allow_edit": "JNZ_ROLE_Department_Manager"},
            {"state": "Pending HQ Final Validation", "doc_status": 0, "allow_edit": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Returned for Revision", "doc_status": 0, "allow_edit": "JNZ_ROLE_Executive_Expert"},
            {"state": "Approved for Procurement", "doc_status": 1, "allow_edit": "System Manager"},
            {"state": "Request Cancelled", "doc_status": 2, "allow_edit": "System Manager"}
        ],
        "transitions": [
            # شروع فرآیند
            {"state": "Draft Initialization", "action": "Submit Initial Request", "next_state": "Under Technical Review", "allowed": "JNZ_ROLE_Executive_Expert"},
            
            # دفتر فنی پروژه
            {"state": "Under Technical Review", "action": "Endorse Technical Merits", "next_state": "Awaiting Site Confirmation", "allowed": "JNZ_ROLE_Project_Technical_Office"},
            {"state": "Under Technical Review", "action": "Return for Revision", "next_state": "Returned for Revision", "allowed": "JNZ_ROLE_Project_Technical_Office"},
            
            # سرپرست کارگاه
            {"state": "Awaiting Site Confirmation", "action": "Validate Site Necessity", "next_state": "Under Departmental Assessment", "allowed": "JNZ_ROLE_Site_Supervisor"},
            {"state": "Awaiting Site Confirmation", "action": "Return for Revision", "next_state": "Returned for Revision", "allowed": "JNZ_ROLE_Site_Supervisor"},
            
            # مدیر بخش
            {"state": "Under Departmental Assessment", "action": "Confirm Departmental Scope", "next_state": "Pending HQ Final Validation", "allowed": "JNZ_ROLE_Department_Manager"},
            {"state": "Under Departmental Assessment", "action": "Return for Revision", "next_state": "Returned for Revision", "allowed": "JNZ_ROLE_Department_Manager"},
            
            # دفتر فنی ستاد (تایید نهایی و سابمیت، یا رد)
            {"state": "Pending HQ Final Validation", "action": "Finalize Technical Approval", "next_state": "Approved for Procurement", "allowed": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Pending HQ Final Validation", "action": "Return for Revision", "next_state": "Returned for Revision", "allowed": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Pending HQ Final Validation", "action": "Cancel Request", "next_state": "Request Cancelled", "allowed": "JNZ_ROLE_HQ_Technical_Office"},

            # ارسال مجدد توسط کارشناس پس از اصلاح
            {"state": "Returned for Revision", "action": "Re-submit Request", "next_state": "Under Technical Review", "allowed": "JNZ_ROLE_Executive_Expert"},
            {"state": "Returned for Revision", "action": "Cancel Request", "next_state": "Request Cancelled", "allowed": "JNZ_ROLE_Executive_Expert"}
        ]
    })
    doc.insert(ignore_permissions=True)