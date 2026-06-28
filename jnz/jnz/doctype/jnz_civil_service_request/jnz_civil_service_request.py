import frappe
from frappe.model.document import Document
from frappe import _

class JNZCivilServiceRequest(Document):
    
    def validate(self):
        self.validate_project_status()
        self.ensure_anti_tamper()

    def before_workflow_action(self):
        self.execute_pessimistic_lock()
        
    def on_update(self):
        self.handle_approved_event()

    # --- Business Rules Implementation ---

    def validate_project_status(self):
        """تضمین اینکه نمی‌توان برای پروژه‌های غیرفعال، درخواست ثبت کرد"""
        if self.project:
            is_active = frappe.db.get_value("JNZ Project", self.project, "active")
            if not is_active:
                frappe.throw(_("پروژه انتخاب شده ({0}) غیرفعال است. امکان پردازش درخواست وجود ندارد.").format(self.project))

    def ensure_anti_tamper(self):
        """
        با وجود اینکه فرم در وضعیت 0 (ذخیره شده) می‌ماند تا قابل ویرایش باشد،
        نباید اجازه دهیم 'پروژه' در میانه‌راه تغییر کند، زیرا مجوزها بر اساس پروژه صادر شده‌اند.
        """
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.project != self.project:
                # فقط در مرحله پیش‌نویس یا عودت مجاز به تغییر پروژه هستند
                if old_doc.workflow_state not in ["Draft Initialization", "Returned for Revision"]:
                    frappe.throw(_("امکان تغییر پروژه پس از جریان افتادن فرآیند تاییدات وجود ندارد. برای تغییر پروژه، فرم باید به کارشناس اجرایی عودت داده شود."))

    def execute_pessimistic_lock(self):
        """
        قفل بدبینانه برای ورک‌فلو:
        آیا کاربر دکمه‌زننده، دارای نقشِ تعیین‌شده در 'همان پروژه خاص' است؟
        """
        user = frappe.session.user
        if user == "Administrator":
            return
            
        action = frappe.request.form_dict.get('workflow_action')
        if not action:
            return

        workflow = frappe.get_doc("Workflow", "JNZ Civil Service Request Workflow")
        allowed_role = None
        for transition in workflow.transitions:
            if transition.state == self.workflow_state and transition.action == action:
                allowed_role = transition.allowed
                break
                
        if not allowed_role:
            return

        has_role_in_project = frappe.db.exists("JNZ Project Members CT", {
            "parent": self.project,
            "member": user,
            "role": allowed_role
        })
        
        if not has_role_in_project:
            frappe.throw(_("شما در کارگاه/پروژه '{0}' دارای نقش '{1}' نیستید، بنابراین مجوز انجام این عملیات را ندارید.").format(self.project, allowed_role))

    def handle_approved_event(self):
        """زمانی که فاز ۱ تایید نهایی شد، فاز ۲ (Procurement) را خودکار بساز"""
        if self.workflow_state == "Approved for Procurement":
            # چک کن آیا قبلاً ساخته شده یا نه (برای جلوگیری از دو بار ساخته شدن)
            if not frappe.db.exists("JNZ Procurement", {"civil_service_request": self.name}):
                proc = frappe.get_doc({
                    "doctype": "JNZ Procurement",
                    "civil_service_request": self.name,
                    "project": self.project
                })
                proc.flags.ignore_permissions = True # دسترسی ادمین برای ساخت خودکار
                proc.insert()
                frappe.msgprint(_("سند استعلام (JNZ Procurement) به صورت خودکار ایجاد شد: {0}").format(proc.name))