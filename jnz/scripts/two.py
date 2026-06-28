import frappe

def run():
    frappe.flags.in_setup = True
    print("🚀 Starting Setup for JNZ Procurement (Phase 2) - Standard DocTypes...")
    
    # اطمینان از روشن بودن Developer Mode برای ساخت داکتایپ استاندارد
    if not frappe.conf.developer_mode:
        print("❌ ERROR: Developer mode is not enabled. Cannot create standard (custom=0) DocTypes.")
        return

    try:
        ensure_roles()
        ensure_workflow_states()
        ensure_workflow_actions()
        ensure_child_tables()
        ensure_doctype()
        ensure_workflow()
        
        frappe.db.commit()
        print("✅ Phase 2 Setup completed successfully! Standard files generated.")
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Setup failed: {str(e)}")

def ensure_roles():
    roles = [
        "JNZ_ROLE_Inquiry_Clerk",
        "JNZ_ROLE_Transactions_Commission",
        "JNZ_ROLE_Tender_Waiver_Commission"
    ]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)

def ensure_workflow_states():
    # تمام مراحل میانی صفر هستند
    states = [
        {"name": "Inquiry Preparation", "doc_status": 0},
        {"name": "Awaiting Vendor Bids", "doc_status": 0},
        {"name": "Under Transactions Commission", "doc_status": 0},
        {"name": "Under Tender Waiver Commission", "doc_status": 0},
        {"name": "Returned for Correction", "doc_status": 0},
        {"name": "Winner Awarded", "doc_status": 1}, # سابمیت و قفل نهایی
        {"name": "Inquiry Cancelled", "doc_status": 2}
    ]
    for state in states:
        if not frappe.db.exists("Workflow State", state["name"]):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state["name"],
                "doc_status": state["doc_status"],
                "style": "Success" if state["name"] == "Winner Awarded" else "Danger" if "Cancelled" in state["name"] else "Warning" if "Returned" in state["name"] else "Primary"
            }).insert(ignore_permissions=True)

def ensure_workflow_actions():
    actions = [
        "Issue Inquiries to Vendors",
        "Submit Bids to Commission",
        "Request Tender Waiver",
        "Approve & Award Contract",
        "Return to Clerk",
        "Re-submit Bids",
        "Re-request Tender Waiver",
        "Reject & Cancel Inquiry"
    ]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)

def ensure_child_tables():
    dt_name = "JNZ Vendor Bid CT"
    if not frappe.db.exists("DocType", dt_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": dt_name,
            "module": "JNZ",
            "custom": 0, # استاندارد (تولید فایل)
            "istable": 1,
            "fields": [
                {"fieldname": "vendor_name", "label": "نام پیمانکار/تامین‌کننده", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"fieldname": "bid_amount", "label": "مبلغ پیشنهادی (ریال)", "fieldtype": "Currency", "reqd": 1, "in_list_view": 1},
                {"fieldname": "is_winner", "label": "برنده؟", "fieldtype": "Check", "default": 0, "in_list_view": 1},
                {"fieldname": "remarks", "label": "ملاحظات", "fieldtype": "Small Text"}
            ]
        })
        doc.insert(ignore_permissions=True)

def ensure_doctype():
    doctype_name = "JNZ Procurement"
    if frappe.db.exists("DocType", doctype_name):
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "JNZ",
        "custom": 0, # استاندارد (تولید فایل)
        "is_submittable": 1,
        "track_changes": 1,
        "naming_rule": "Expression",
        "autoname": "JNZ-PROC-.YYYY.-.#####",
        "fields": [
            {"fieldname": "civil_service_request", "label": "سند درخواست خدمات مرجع", "fieldtype": "Link", "options": "JNZ Civil Service Request", "reqd": 1, "in_list_view": 1},
            {"fieldname": "project", "label": "کارگاه/پروژه", "fieldtype": "Link", "options": "JNZ Project", "reqd": 1, "in_list_view": 1},
            {"fieldname": "procurement_method", "label": "روش تامین", "fieldtype": "Select", "options": "\nاستعلام از وندور لیست\nترک تشریفات", "reqd": 1},
            {"fieldname": "estimated_value_category", "label": "رده قیمتی استعلام", "fieldtype": "Select", "options": "\nزیر ۴۰ میلیون تومان\nبین ۴۰ تا ۳۰۰ میلیون تومان\nبالای ۳۰۰ میلیون تومان"},
            {"fieldname": "vendor_bids_section", "label": "پیشنهادهای مالی", "fieldtype": "Section Break"},
            {"fieldname": "vendor_bids", "label": "لیست قیمت‌های دریافتی", "fieldtype": "Table", "options": "JNZ Vendor Bid CT"},
            {"fieldname": "commission_section", "label": "تصمیمات کمیسیون", "fieldtype": "Section Break"},
            {"fieldname": "commission_minutes", "label": "متن صورت‌جلسه کمیسیون", "fieldtype": "Text Editor"},
            {"fieldname": "winning_amount", "label": "مبلغ نهایی توافق شده (ریال)", "fieldtype": "Currency", "read_only": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "workflow_state", "label": "وضعیت فرآیند", "fieldtype": "Link", "options": "Workflow State", "read_only": 1, "in_list_view": 1}
        ],
        "permissions": [
            {"role": "JNZ_ROLE_Inquiry_Clerk", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            {"role": "JNZ_ROLE_Transactions_Commission", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Tender_Waiver_Commission", "read": 1, "write": 1}
        ]
    })
    doc.insert(ignore_permissions=True)

def ensure_workflow():
    workflow_name = "JNZ Procurement Workflow"
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name)

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": "JNZ Procurement",
        "is_active": 1,
        "states": [
            {"state": "Inquiry Preparation", "doc_status": 0, "allow_edit": "JNZ_ROLE_Inquiry_Clerk"},
            {"state": "Awaiting Vendor Bids", "doc_status": 0, "allow_edit": "JNZ_ROLE_Inquiry_Clerk"},
            {"state": "Under Transactions Commission", "doc_status": 0, "allow_edit": "JNZ_ROLE_Transactions_Commission"},
            {"state": "Under Tender Waiver Commission", "doc_status": 0, "allow_edit": "JNZ_ROLE_Tender_Waiver_Commission"},
            {"state": "Returned for Correction", "doc_status": 0, "allow_edit": "JNZ_ROLE_Inquiry_Clerk"},
            {"state": "Winner Awarded", "doc_status": 1, "allow_edit": "System Manager"},
            {"state": "Inquiry Cancelled", "doc_status": 2, "allow_edit": "System Manager"}
        ],
        "transitions": [
            {"state": "Inquiry Preparation", "action": "Issue Inquiries to Vendors", "next_state": "Awaiting Vendor Bids", "allowed": "JNZ_ROLE_Inquiry_Clerk"},
            {"state": "Inquiry Preparation", "action": "Request Tender Waiver", "next_state": "Under Tender Waiver Commission", "allowed": "JNZ_ROLE_Inquiry_Clerk"},
            
            {"state": "Awaiting Vendor Bids", "action": "Submit Bids to Commission", "next_state": "Under Transactions Commission", "allowed": "JNZ_ROLE_Inquiry_Clerk"},
            
            {"state": "Under Transactions Commission", "action": "Approve & Award Contract", "next_state": "Winner Awarded", "allowed": "JNZ_ROLE_Transactions_Commission"},
            {"state": "Under Transactions Commission", "action": "Return to Clerk", "next_state": "Returned for Correction", "allowed": "JNZ_ROLE_Transactions_Commission"},
            {"state": "Under Transactions Commission", "action": "Reject & Cancel Inquiry", "next_state": "Inquiry Cancelled", "allowed": "JNZ_ROLE_Transactions_Commission"},
            
            {"state": "Under Tender Waiver Commission", "action": "Approve & Award Contract", "next_state": "Winner Awarded", "allowed": "JNZ_ROLE_Tender_Waiver_Commission"},
            {"state": "Under Tender Waiver Commission", "action": "Return to Clerk", "next_state": "Returned for Correction", "allowed": "JNZ_ROLE_Tender_Waiver_Commission"},
            {"state": "Under Tender Waiver Commission", "action": "Reject & Cancel Inquiry", "next_state": "Inquiry Cancelled", "allowed": "JNZ_ROLE_Tender_Waiver_Commission"},

            {"state": "Returned for Correction", "action": "Re-submit Bids", "next_state": "Under Transactions Commission", "allowed": "JNZ_ROLE_Inquiry_Clerk"},
            {"state": "Returned for Correction", "action": "Re-request Tender Waiver", "next_state": "Under Tender Waiver Commission", "allowed": "JNZ_ROLE_Inquiry_Clerk"}
        ]
    })
    doc.insert(ignore_permissions=True)