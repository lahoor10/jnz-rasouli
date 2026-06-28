import frappe
from frappe.model.document import Document
from frappe import _

class JNZProcurement(Document):
    
    def validate(self):
        self.validate_reference_document()
        self.extract_and_validate_winner()

    def before_workflow_action(self):
        self.execute_pessimistic_lock()
        self.validate_commission_decision()

    def on_submit(self):
        """زمانی که فاز ۲ برنده را تعیین کرد و سابمیت شد، فاز ۳ (Contract) را بساز"""
        if self.workflow_state == "Winner Awarded":
            if not frappe.db.exists("JNZ Contract", {"procurement_ref": self.name}):
                contract = frappe.get_doc({
                    "doctype": "JNZ Contract",
                    "procurement_ref": self.name
                })
                # متد pull_data_from_procurement در داکتایپ قرارداد، اطلاعات را خودکار می‌کشد
                contract.flags.ignore_permissions = True
                contract.insert()
                frappe.msgprint(_("پیش‌نویس قرارداد (JNZ Contract) به صورت خودکار ایجاد شد: {0}").format(contract.name))

    # --- Business Logic Methods ---
    def validate_reference_document(self):
        """اطمینان از وجود سند اولیه خدمات و وضعیت معتبر آن"""
        if self.civil_service_request:
            req_state = frappe.db.get_value("JNZ Civil Service Request", self.civil_service_request, "workflow_state")
            if req_state != "Approved for Procurement":
                frappe.throw(_("سند درخواست خدمات مرجع در وضعیت مناسب جهت استعلام قرار ندارد."))
                
        # اطمینان از قفل ماندن مرجع اصلی
        if not self.is_new():
            old = self.get_doc_before_save()
            if old and old.civil_service_request != self.civil_service_request:
                frappe.throw(_("امکان تغییر سند مرجع پس از ذخیره اولیه وجود ندارد."))

    def extract_and_validate_winner(self):
        """محاسبه مبلغ نهایی بر اساس تیک برنده و جلوگیری از انتخاب چند برنده"""
        winners_count = 0
        winning_bid = 0
        
        if self.vendor_bids:
            for row in self.vendor_bids:
                if row.is_winner:
                    winners_count += 1
                    winning_bid = row.bid_amount
                    
        if winners_count > 1:
            frappe.throw(_("بیش از یک وندور به عنوان برنده انتخاب شده است! تنها امکان انتخاب یک برنده وجود دارد."))
            
        self.winning_amount = winning_bid if winners_count == 1 else 0

    def validate_commission_decision(self):
        """اعتبارسنجی الزامات در لحظه تایید کمیسیون"""
        action = frappe.request.form_dict.get('workflow_action')
        
        if action == "Approve & Award Contract":
            # در صورتی که روش استعلام از لیست است، حتما باید برنده مشخص شده باشد
            if self.procurement_method == "استعلام از وندور لیست" and not self.winning_amount:
                frappe.throw(_("جهت تصویب نهایی استعلام، حتماً باید یک پیمانکار از لیست پیشنهادها به عنوان 'برنده' مشخص گردد."))
            
            # ثبت صورت‌جلسه برای تایید نهایی الزامی است
            if not self.commission_minutes:
                frappe.throw(_("ثبت متن یا چکیده صورت‌جلسه کمیسیون جهت تعیین برنده الزامی است."))

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

        workflow = frappe.get_doc("Workflow", "JNZ Procurement Workflow")
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
            frappe.throw(_("شما در کارگاه/پروژه '{0}' دارای نقش '{1}' نیستید و مجوز لازم برای این عملیات را ندارید.").format(self.project, allowed_role))