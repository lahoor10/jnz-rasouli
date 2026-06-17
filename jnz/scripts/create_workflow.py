import frappe

def make_ration_request_workflow():
    workflow_name = "JNZ Ration Request Workflow"
    doctype_name = "JNZ Ration Request"

    # ۱. تعریف تمام استیت‌های مورد نیاز
    required_states = [
        "Draft", "Pending Support Approval", "Pending Commercial Approval",
        "Pending CEO Office Approval", "Pending Security Approval", 
        "Pending Finance Approval", "Pending CEO Approval", "Approved", "Rejected"
    ]

    # ساخت استیت‌ها در منوی اصلی سیستم (اگر وجود نداشته باشند)
    for state_name in required_states:
        if not frappe.db.exists("Workflow State", state_name):
            d = frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state_name})
            d.insert(ignore_permissions=True)

    # ۲. تعریف تمام اکشن‌های مورد نیاز ورک‌فلو
    required_actions = [
        "Send to Support", "Send to Commercial", "Send to CEO Office",
        "Send to Security", "Send to Finance", "Send to CEO", 
        "Final Approve and Submit", "Reject"
    ]

    # ساخت اکشن‌ها در سیستم (اگر وجود نداشته باشند)
    for action_name in required_actions:
        if not frappe.db.exists("Workflow Action Master", action_name):
            d = frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action_name})
            d.insert(ignore_permissions=True)

    frappe.db.commit()

    # ۳. پاک کردن ورک‌فلوی قبلی (در صورت وجود) برای جایگزینی بدون تداخل
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True)
        frappe.db.commit()

    # ۴. ساختار وضعیت‌های داخلی ورک‌فلو (مقادیر خالی با System Manager پر شدند)
    states_data = [
        {"doctype": "Workflow State Document", "state": "Draft", "status": "Draft", "doc_status": "0", "allow_edit": "All"},
        {"doctype": "Workflow State Document", "state": "Pending Support Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Support_Supervisor"},
        {"doctype": "Workflow State Document", "state": "Pending Commercial Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Commercial_Manager"},
        {"doctype": "Workflow State Document", "state": "Pending CEO Office Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__CEO_Office"},
        {"doctype": "Workflow State Document", "state": "Pending Security Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__Security_Department"},
        {"doctype": "Workflow State Document", "state": "Pending Finance Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Finance_Manager"},
        {"doctype": "Workflow State Document", "state": "Pending CEO Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_CEO"},
        {"doctype": "Workflow State Document", "state": "Approved", "status": "Approved", "doc_status": "1", "allow_edit": "System Manager"},
        {"doctype": "Workflow State Document", "state": "Rejected", "status": "Rejected", "doc_status": "0", "allow_edit": "System Manager"}
    ]

    # ۵. ساختار انتقال‌های ورک‌فلو
    transitions_data = [
        {"doctype": "Workflow Transition", "allowed": "All", "state": "Draft", "action": "Send to Support", "next_state": "Pending Support Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Support_Supervisor", "state": "Pending Support Approval", "action": "Send to Commercial", "next_state": "Pending Commercial Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Support_Supervisor", "state": "Pending Support Approval", "action": "Reject", "next_state": "Rejected"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Commercial_Manager", "state": "Pending Commercial Approval", "action": "Send to CEO Office", "next_state": "Pending CEO Office Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Commercial_Manager", "state": "Pending Commercial Approval", "action": "Reject", "next_state": "Rejected"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__CEO_Office", "state": "Pending CEO Office Approval", "action": "Send to Security", "next_state": "Pending Security Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__CEO_Office", "state": "Pending CEO Office Approval", "action": "Reject", "next_state": "Rejected"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Security_Department", "state": "Pending Security Approval", "action": "Send to Finance", "next_state": "Pending Finance Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Security_Department", "state": "Pending Security Approval", "action": "Reject", "next_state": "Rejected"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Finance_Manager", "state": "Pending Finance Approval", "action": "Send to CEO", "next_state": "Pending CEO Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Finance_Manager", "state": "Pending Finance Approval", "action": "Reject", "next_state": "Rejected"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_CEO", "state": "Pending CEO Approval", "action": "Final Approve and Submit", "next_state": "Approved"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_CEO", "state": "Pending CEO Approval", "action": "Reject", "next_state": "Rejected"}
    ]

    # ۶. ایجاد سند ورک‌فلو
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype_name,
        "is_active": 1,
        "override_status": 0,
        "send_email_alert": 0,
        "states": states_data,
        "transitions": transitions_data
    })

    # فلگ‌های دور زدن ولیدیشن‌ها
    workflow.flags.ignore_links = True
    workflow.flags.ignore_validate = True
    workflow.flags.ignore_permissions = True
    
    workflow.save()
    frappe.db.commit()

import frappe

def make_food_request_workflow():
    workflow_name = "JNZ Food Request Workflow"
    doctype_name = "JNZ Food Request"

    # ۱. تعریف تمام استیت‌های مورد نیاز گردش کار جدید غذا
    required_states = [
        "Draft", "Pending Site Supervisor Approval", "Pending Project Manager Approval",
        "Pending Security Approval", "Pending HR Approval", "Pending CEO Office Approval", 
        "Pending CEO Approval", "Approved", "Rejected"
    ]

    # ساخت استیت‌ها در منوی اصلی سیستم (اگر وجود نداشته باشند)
    for state_name in required_states:
        if not frappe.db.exists("Workflow State", state_name):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state_name}).insert(ignore_permissions=True)

    # ۲. تعریف تمام اکشن‌های مورد نیاز ورک‌فلو
    required_actions = [
        "Send to Site Supervisor", "Send to Project Manager", "Send to Security",
        "Send to HR", "Send to CEO Office", "Send to CEO", 
        "Final Approve and Submit", "Reject"
    ]

    # ساخت اکشن‌ها در سیستم (اگر وجود نداشته باشند)
    for action_name in required_actions:
        if not frappe.db.exists("Workflow Action Master", action_name):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action_name}).insert(ignore_permissions=True)

    frappe.db.commit()

    # ۳. پاک کردن ورک‌فلوی قبلی غذا (در صورت وجود) برای جایگزینی دقیق
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True)
        frappe.db.commit()

    # ۴. ساختار وضعیت‌های داخلی ورک‌فلو با رعایت رول‌های ارسالی شما
    states_data = [
        {"doctype": "Workflow State Document", "state": "Draft", "status": "Draft", "doc_status": "0", "allow_edit": "All"},
        {"doctype": "Workflow State Document", "state": "Pending Site Supervisor Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Site_Supervisor"},
        {"doctype": "Workflow State Document", "state": "Pending Project Manager Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__Project_Manager"},
        {"doctype": "Workflow State Document", "state": "Pending Security Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__Security_Department"},
        {"doctype": "Workflow State Document", "state": "Pending HR Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__HR"},
        {"doctype": "Workflow State Document", "state": "Pending CEO Office Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE__CEO_Office"},
        {"doctype": "Workflow State Document", "state": "Pending CEO Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_CEO"},
        {"doctype": "Workflow State Document", "state": "Approved", "status": "Approved", "doc_status": "1", "allow_edit": "System Manager"},
        {"doctype": "Workflow State Document", "state": "Rejected", "status": "Rejected", "doc_status": "0", "allow_edit": "System Manager"}
    ]

    # ۵. ساختار انتقال‌های ورک‌فلو با دکمه ریجکت اختصاصی برای تمام رول‌ها
    transitions_data = [
        {"doctype": "Workflow Transition", "allowed": "All", "state": "Draft", "action": "Send to Site Supervisor", "next_state": "Pending Site Supervisor Approval"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Site_Supervisor", "state": "Pending Site Supervisor Approval", "action": "Send to Project Manager", "next_state": "Pending Project Manager Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Site_Supervisor", "state": "Pending Site Supervisor Approval", "action": "Reject", "next_state": "Rejected"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Project_Manager", "state": "Pending Project Manager Approval", "action": "Send to Security", "next_state": "Pending Security Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Project_Manager", "state": "Pending Project Manager Approval", "action": "Reject", "next_state": "Rejected"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Security_Department", "state": "Pending Security Approval", "action": "Send to HR", "next_state": "Pending HR Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__Security_Department", "state": "Pending Security Approval", "action": "Reject", "next_state": "Rejected"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__HR", "state": "Pending HR Approval", "action": "Send to CEO Office", "next_state": "Pending CEO Office Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__HR", "state": "Pending HR Approval", "action": "Reject", "next_state": "Rejected"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__CEO_Office", "state": "Pending CEO Office Approval", "action": "Send to CEO", "next_state": "Pending CEO Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE__CEO_Office", "state": "Pending CEO Office Approval", "action": "Reject", "next_state": "Rejected"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_CEO", "state": "Pending CEO Approval", "action": "Final Approve and Submit", "next_state": "Approved"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_CEO", "state": "Pending CEO Approval", "action": "Reject", "next_state": "Rejected"}
    ]

    # ۶. ایجاد نهایی سند ورک‌فلو درخواست غذا
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype_name,
        "is_active": 1,
        "override_status": 0,
        "send_email_alert": 0,
        "states": states_data,
        "transitions": transitions_data
    })

    # فلگ‌های استاندارد پچ لول بالا برای دور زدن ولیدیشن‌های سخت‌گیرانه ساب‌داک
    workflow.flags.ignore_links = True
    workflow.flags.ignore_validate = True
    workflow.flags.ignore_permissions = True
    
    workflow.save()
    frappe.db.commit()
    

def run():
    # make_ration_request_workflow()
    # make_food_request_workflow()
    pass