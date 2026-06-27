import frappe
from frappe import _

def check_secretariat_fields(doc, method=None):
    """
    بررسی پر بودن فیلدهای دبیرخانه دقیقا قبل از نهایی شدن ورک‌فلو
    """
    # فراپه در زمان تغییر ورک‌فلو، وضعیت جدید را روی داکیومنت ست می‌کند
    if doc.workflow_state == "Completed":
        
        # اگر تیک "نیاز به ابلاغ رسمی" خورده باشد
        if doc.needs_official_notification == 1 and not doc.postal_tracking_number:
            frappe.throw(_("For postal dispatch, entering the 'Postal Tracking Number' is mandatory."))
            
        # اگر تیک "نیاز به ابلاغ رسمی" نخورده باشد (فقط اتوماسیون)
        elif doc.needs_official_notification == 0 and not doc.automation_letter_number:
            frappe.throw(_("For automation dispatch, entering the 'Automation Letter Number' is mandatory."))

def notify_parties(doc, method=None):
    """
    ارسال نوتیفیکیشن و ایمیل پس از پایان فرآیند (Submit)
    """
    users_with_role = frappe.get_all("Has Role", filters={"role": "JNZ_ROLE_Technical_Office_Manager"}, fields=["parent"])
    for u in users_with_role:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": _("New warning issued to contractor: {0}").format(doc.contractor),
            "email_content": _("A warning for contractor {0} in project {1} has been issued and dispatched by the Secretariat.").format(doc.contractor, doc.project),
            "document_type": doc.doctype,
            "document_name": doc.name,
            "for_user": u.parent
        }).insert(ignore_permissions=True)

    if doc.contractor:
        contractor_email = frappe.db.get_value("JNZ Contractor", doc.contractor, "email")
        if contractor_email:
            frappe.sendmail(
                recipients=[contractor_email],
                subject=_("Warning Notification - Project {0}").format(doc.project),
                message=_("Dear Contractor,<br><br>Following contract {0}, the following warning is hereby issued to you:<br><br>{1}<br><br>Best regards.").format(doc.contract, doc.warning_reason),
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )