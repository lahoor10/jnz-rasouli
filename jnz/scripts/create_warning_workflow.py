import frappe

def make_contractor_warning_workflow():
    workflow_name = "JNZ Contractor Warning Workflow"
    doctype_name = "JNZ Contractor Warning"

    # ۱. تعریف تمام استیت‌های مورد نیاز
    required_states = [
        "Draft", 
        "Pending Technical Office Approval", 
        "Pending Engineering Deputy Approval", 
        "Pending Legal Approval",
        "Pending Official Dispatch", 
        "Pending Internal Dispatch", 
        "Completed"
    ]

    for state_name in required_states:
        if not frappe.db.exists("Workflow State", state_name):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state_name}).insert(ignore_permissions=True)

    # ۲. تعریف تمام اکشن‌های مورد نیاز ورک‌فلو
    required_actions = [
        "Send for Approval", "Approve", "Reject", "Reject By Deputy",
        "Approve - Needs Official", "Approve - Internal Only",
        "Approve Legal", "Reject Legal to Internal",
        "Issue and Post Letter", "Send via Automation"
    ]

    for action_name in required_actions:
        if not frappe.db.exists("Workflow Action Master", action_name):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action_name}).insert(ignore_permissions=True)

    frappe.db.commit()

    # ۳. پاک کردن ورک‌فلوی قبلی (در صورت وجود)
    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True)
        frappe.db.commit()

    # ۴. ساختار وضعیت‌های داخلی ورک‌فلو
    states_data = [
        {"doctype": "Workflow State Document", "state": "Draft", "status": "Draft", "doc_status": "0", "allow_edit": "JNZ_ROLE_Notifier"},
        {"doctype": "Workflow State Document", "state": "Pending Technical Office Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Technical_Office_Manager"},
        {"doctype": "Workflow State Document", "state": "Pending Engineering Deputy Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Technical_Engineering_Deputy"},
        {"doctype": "Workflow State Document", "state": "Pending Legal Approval", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Legal_Department"},
        {"doctype": "Workflow State Document", "state": "Pending Official Dispatch", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Secretariat"},
        {"doctype": "Workflow State Document", "state": "Pending Internal Dispatch", "status": "Open", "doc_status": "0", "allow_edit": "JNZ_ROLE_Secretariat"},
        {"doctype": "Workflow State Document", "state": "Completed", "status": "Approved", "doc_status": "1", "allow_edit": "System Manager"}
    ]

    # ۵. ساختار انتقال‌های ورک‌فلو همراه با شروط (Conditions)
    transitions_data = [
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Notifier", "state": "Draft", "action": "Send for Approval", "next_state": "Pending Technical Office Approval"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Technical_Office_Manager", "state": "Pending Technical Office Approval", "action": "Approve", "next_state": "Pending Engineering Deputy Approval"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Technical_Office_Manager", "state": "Pending Technical Office Approval", "action": "Reject", "next_state": "Draft"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Technical_Engineering_Deputy", "state": "Pending Engineering Deputy Approval", "action": "Reject By Deputy", "next_state": "Draft"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Technical_Engineering_Deputy", "state": "Pending Engineering Deputy Approval", "action": "Approve - Needs Official", "next_state": "Pending Legal Approval", "condition": "doc.needs_official_notification == 1"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Technical_Engineering_Deputy", "state": "Pending Engineering Deputy Approval", "action": "Approve - Internal Only", "next_state": "Pending Internal Dispatch", "condition": "doc.needs_official_notification == 0"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Legal_Department", "state": "Pending Legal Approval", "action": "Approve Legal", "next_state": "Pending Official Dispatch"},
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Legal_Department", "state": "Pending Legal Approval", "action": "Reject Legal to Internal", "next_state": "Pending Internal Dispatch"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Secretariat", "state": "Pending Official Dispatch", "action": "Issue and Post Letter", "next_state": "Completed"},
        
        {"doctype": "Workflow Transition", "allowed": "JNZ_ROLE_Secretariat", "state": "Pending Internal Dispatch", "action": "Send via Automation", "next_state": "Completed"}
    ]

    # ۶. ایجاد نهایی سند ورک‌فلو
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype_name,
        "is_active": 1,
        "override_status": 1,
        "send_email_alert": 0,
        "states": states_data,
        "transitions": transitions_data
    })

    workflow.flags.ignore_links = True
    workflow.flags.ignore_validate = True
    workflow.flags.ignore_permissions = True
    
    workflow.save()
    frappe.db.commit()
    print(f"✅ Workflow '{workflow_name}' created successfully!")

def run():
    make_contractor_warning_workflow()