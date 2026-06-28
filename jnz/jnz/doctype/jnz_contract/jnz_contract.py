import frappe
from frappe.model.document import Document

class JNZContract(Document):
    def validate(self):
        self.pull_data_from_procurement()

    def pull_data_from_procurement(self):
        """در لحظه انتخاب سند استعلام، نام پیمانکار و مبلغ را از سند Procurement می‌کشد"""
        if self.procurement_ref:
            proc = frappe.get_doc("JNZ Procurement", self.procurement_ref)
            
            # پیدا کردن پیمانکار برنده
            for row in proc.vendor_bids:
                if row.is_winner:
                    self.contractor_name = row.vendor_name
                    break
            
            self.final_amount = proc.winning_amount

    def on_submit(self):
        """پس از امضای نهایی توسط مدیرعامل، می‌توان عملیات ابلاغ خودکار را اینجا پیاده کرد"""
        if self.workflow_state == "Signed & Executed":
            # کد ارجاع به دپارتمان‌های مربوطه (مثلاً حسابداری یا انبار)
            pass