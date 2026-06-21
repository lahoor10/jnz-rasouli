import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days, getdate
from frappe.utils.data import get_url_to_form
import jdatetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOCTYPE_FOOD_REQUEST     = "JNZ Food Request"
DOCTYPE_PROJECT_SETTINGS = "JNZ Project Settings"


class JNZFoodRequest(Document):

   # اجرا هنگام ذخیره در حالت پیش‌نویس (Draft - Docstatus 0)
    def on_update(self):
        self.send_custom_workflow_email()

    # اجرا هنگام تایید و نهایی شدن (Submit - Docstatus 1)
    def on_submit(self):
        self.send_custom_workflow_email()

    # اجرا هنگام لغو یا رد شدن (Cancel - Docstatus 2)
    def on_cancel(self):
        self.send_custom_workflow_email()

    def send_custom_workflow_email(self):
        doc_before_save = self.get_doc_before_save()
        if not doc_before_save:
            return

        previous_state = doc_before_save.workflow_state
        current_state = self.workflow_state

        # جلوگیری از ارسال ایمیل تکراری در صورت عدم تغییر وضعیت ورک‌فلو
        if current_state == previous_state:
            return

        state_role_map = {
            "Pending Site Supervisor Approval": "JNZ_ROLE_Site_Supervisor",
            "Pending Project Manager Approval": "JNZ_ROLE__Project_Manager",
            "Pending Security Approval": "JNZ_ROLE__Security_Department",
            "Pending HR Approval": "JNZ_ROLE__HR",
            "Pending CEO Office Approval": "JNZ_ROLE__CEO_Office",
            "Pending CEO Approval": "JNZ_ROLE_CEO",
            # اگر می‌خواهی در حالت Approved یا Rejected هم به کسی (مثلاً سیستم منیجر) 
            # ایمیل برود، باید نقش‌های آن‌ها را هم اینجا اضافه کنی.
        }

        if current_state not in state_role_map:
            return

        target_role = state_role_map[current_state]

        if not self.freq_project:
            return

        recipients = frappe.get_all(
            "JNZ Project Members CT",
            filters={
                "parent": self.freq_project,
                "parenttype": "JNZ Project",
                "role": target_role
            },
            pluck="member"
        )
        
        frappe.msgprint(f"لیست گیرندگان پیدا شده برای نقش {target_role}: {recipients}")

        if recipients:
            project_name = frappe.db.get_value("JNZ Project", self.freq_project, "proj_name") or self.freq_project
            doc_url = get_url_to_form(self.doctype, self.name)
            
            subject = f"درخواست غذای جدید - پروژه: {project_name}"
            message = f"""
            <div style="direction: rtl; text-align: right; font-family: Tahoma, sans-serif;">
                <p>با سلام،</p>
                <p>درخواست غذای شماره <b>{self.name}</b> تغییر وضعیت داده و هم‌اکنون در مرحله <b>{_(current_state)}</b> منتظر بررسی و تایید شماست.</p>
                <p><b>نام پروژه:</b> {project_name}</p>
                <p>جهت مشاهده و ثبت تاییدیه، روی لینک زیر کلیک کنید:</p>
                <p><a href="{doc_url}">مشاهده درخواست</a></p>
            </div>
            """

            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                reference_doctype=self.doctype,
                reference_name=self.name,
                now=False
            )
    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def before_save(self):
        if not self.freq_request_date:
            self.freq_request_date = today()

    def validate(self):
        self._validate_dates()
        self._validate_positive_counts()
        self._validate_no_overlapping_requests()

    # ------------------------------------------------------------------
    # Whitelisted Methods for UI Interaction
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def get_calculated_end_date(self):
        if not self.freq_project or not self.freq_start_date:
            return None

        settings = frappe.db.get_value(
            DOCTYPE_PROJECT_SETTINGS,
            {"projset_project": self.freq_project},
            ["projset_auto_generate_end_date", "projset_request_period_days"],
            as_dict=True,
        )

        if settings and settings.projset_auto_generate_end_date:
            period_days = (settings.projset_request_period_days or 10) - 1
            calculated_end = add_days(getdate(self.freq_start_date), period_days)
            return calculated_end
        
        return None

    @frappe.whitelist()
    def sync_table_with_dates(self):
        """
        همگام‌سازی سطرها با بازه جدید. حفظ داده‌های قدیمی و پر کردن ردیف‌های جدید با مقادیر پیش‌فرض.
        """
        if not self.freq_start_date or not self.freq_end_date:
            return

        start = getdate(self.freq_start_date)
        end   = getdate(self.freq_end_date)
        
        if end < start:
            return

        b_default = self.default_breakfast or 0
        l_default = self.default_lunch or 0
        d_default = self.default_dinner or 0

        existing = {
            getdate(row.frd_day_date): {
                "frd_breakfast_count": row.frd_breakfast_count or 0,
                "frd_lunch_count":     row.frd_lunch_count     or 0,
                "frd_dinner_count":    row.frd_dinner_count    or 0,
            }
            for row in (self.freq_days or []) if row.frd_day_date
        }

        self.freq_days = []
        current = start

        while current <= end:
            if current in existing:
                saved = existing[current]
                self.append("freq_days", {
                    "frd_day_date":        str(current),
                    "frd_breakfast_count": saved.get("frd_breakfast_count", 0),
                    "frd_lunch_count":     saved.get("frd_lunch_count",     0),
                    "frd_dinner_count":    saved.get("frd_dinner_count",    0),
                })
            else:
                self.append("freq_days", {
                    "frd_day_date":        str(current),
                    "frd_breakfast_count": b_default,
                    "frd_lunch_count":     l_default,
                    "frd_dinner_count":    d_default,
                })
            current = add_days(current, 1)

    @frappe.whitelist()
    def apply_default_counts_to_table(self):
        b_count = self.default_breakfast or 0
        l_count = self.default_lunch or 0
        d_count = self.default_dinner or 0

        for row in self.freq_days or []:
            row.frd_breakfast_count = b_count
            row.frd_lunch_count = l_count
            row.frd_dinner_count = d_count

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_no_overlapping_requests(self):
        if not self.freq_project or not self.freq_start_date or not self.freq_end_date:
            return

        overlapping_request = frappe.db.exists(DOCTYPE_FOOD_REQUEST, {
            "freq_project": self.freq_project,
            "name": ["!=", self.name],
            "docstatus": ["<=", 1],
            "freq_start_date": ["<=", self.freq_end_date],
            "freq_end_date": [">=", self.freq_start_date]
        })

        if overlapping_request:
            start, end = frappe.db.get_value(DOCTYPE_FOOD_REQUEST, overlapping_request, ["freq_start_date", "freq_end_date"])
            shamsi_start = jdatetime.date.fromgregorian(date=getdate(start)).strftime("%Y/%m/%d")
            shamsi_end = jdatetime.date.fromgregorian(date=getdate(end)).strftime("%Y/%m/%d")
            
            frappe.throw(
                _("The selected date range overlaps with an existing request. The existing request date is from {0} to {1} in request {2}.")
                .format(shamsi_start, shamsi_end, overlapping_request)
            )
            
    def _validate_dates(self):
        errors = []
        if not self.freq_start_date:
            errors.append(_("Start Date is required."))
        if not self.freq_end_date:
            errors.append(_("End Date is required. Use 'Fill End Date' button if needed."))
        if self.freq_start_date and getdate(self.freq_start_date) < getdate(today()):
            errors.append(_("Start Date cannot be before today."))
        if (
            self.freq_start_date
            and self.freq_end_date
            and getdate(self.freq_end_date) < getdate(self.freq_start_date)
        ):
            errors.append(_("End Date cannot be before Start Date."))
        if errors:
            frappe.throw("\n".join(errors))
            
    def _validate_positive_counts(self):
        for row in self.freq_days or []:
            if (row.frd_breakfast_count or 0) < 0 or \
               (row.frd_lunch_count or 0) < 0 or \
               (row.frd_dinner_count or 0) < 0:
                
                miladi_date = getdate(row.frd_day_date)
                shamsi_str = jdatetime.date.fromgregorian(date=miladi_date).strftime("%Y/%m/%d")
                
                frappe.throw(
                    _("Row for date {0} cannot have negative food counts. Please enter 0 or more.")
                    .format(shamsi_str)
                )