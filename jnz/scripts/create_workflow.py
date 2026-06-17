import frappe

def make_food_request_workflow():
    workflow_name = "JNZ Food Request Workflow"
    doctype_name = "JNZ Food Request"

    # ۱. اگر ورک‌فلو از قبل وجود دارد، آن را حذف می‌کنیم تا تغییرات جدید جایگزین شوند
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True)
        frappe.db.commit()

    # ۲. تعریف وضعیت‌ها (States) - با قابلیت ویرایش انحصاری برای رول مربوطه در هر مرحله
    states = [
        {
            "state": "Draft",
            "status": "Draft",
            "doc_status": "0",
            "allow_edit": "All Roles"
        },
        {
            "state": "Pending Support Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE_Support_Supervisor"
        },
        {
            "state": "Pending Commercial Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE_Commercial_Manager"
        },
        {
            "state": "Pending CEO Office Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE__CEO_Office"
        },
        {
            "state": "Pending Security Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE__Security_Department"
        },
        {
            "state": "Pending Finance Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE_Finance_Manager"
        },
        {
            "state": "Pending CEO Approval",
            "status": "Open",
            "doc_status": "0",
            "allow_edit": "JNZ_ROLE_CEO"
        },
        {
            "state": "Approved",
            "status": "Approved",
            "doc_status": "1",
            "allow_edit": ""
        },
        {
            "state": "Rejected",
            "status": "Rejected",
            "doc_status": "0",
            "allow_edit": ""
        }
    ]

    # ۳. تعریف انتقال‌ها (Transitions) و اکشن‌های مربوط به هر مرحله
    transitions = [
        {
            "allowed": "All Roles",
            "state": "Draft",
            "action": "Send to Support",
            "next_state": "Pending Support Approval"
        },
        {
            "allowed": "JNZ_ROLE_Support_Supervisor",
            "state": "Pending Support Approval",
            "action": "Send to Commercial",
            "next_state": "Pending Commercial Approval"
        },
        {
            "allowed": "JNZ_ROLE_Support_Supervisor",
            "state": "Pending Support Approval",
            "action": "Reject",
            "next_state": "Rejected"
        },
        {
            "allowed": "JNZ_ROLE_Commercial_Manager",
            "state": "Pending Commercial Approval",
            "action": "Send to CEO Office",
            "next_state": "Pending CEO Office Approval"
        },
        {
            "allowed": "JNZ_ROLE_Commercial_Manager",
            "state": "Pending Commercial Approval",
            "action": "Reject",
            "next_state": "Rejected"
        },
        {
            "allowed": "JNZ_ROLE__CEO_Office",
            "state": "Pending CEO Office Approval",
            "action": "Send to Security",
            "next_state": "Pending Security Approval"
        },
        {
            "allowed": "JNZ_ROLE__CEO_Office",
            "state": "Pending CEO Office Approval",
            "action": "Reject",
            "next_state": "Rejected"
        },
        {
            "allowed": "JNZ_ROLE__Security_Department",
            "state": "Pending Security Approval",
            "action": "Send to Finance",
            "next_state": "Pending Finance Approval"
        },
        {
            "allowed": "JNZ_ROLE__Security_Department",
            "state": "Pending Security Approval",
            "action": "Reject",
            "next_state": "Rejected"
        },
        {
            "allowed": "JNZ_ROLE_Finance_Manager",
            "state": "Pending Finance Approval",
            "action": "Send to CEO",
            "next_state": "Pending CEO Approval"
        },
        {
            "allowed": "JNZ_ROLE_Finance_Manager",
            "state": "Pending Finance Approval",
            "action": "Reject",
            "next_state": "Rejected"
        },
        {
            "allowed": "JNZ_ROLE_CEO",
            "state": "Pending CEO Approval",
            "action": "Final Approve and Submit",
            "next_state": "Approved"
        },
        {
            "allowed": "JNZ_ROLE_CEO",
            "state": "Pending CEO Approval",
            "action": "Reject",
            "next_state": "Rejected"
        }
    ]

    # ۴. ساخت آبجکت اصلی ورک‌فلو با فیلدهای مورد نظر
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype_name,
        "is_active": 1,
        "override_status": 0,
        "send_email_alert": 0,
        "workflow_states": states,
        "transitions": transitions
    })

    # ۵. درج در دیتابیس و کامیت کردن تغییرات
    workflow.insert(ignore_permissions=True)
    frappe.db.commit()