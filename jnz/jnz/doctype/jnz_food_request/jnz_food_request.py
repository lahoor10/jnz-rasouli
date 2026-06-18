import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days, getdate
from frappe.utils.data import format_date
import jdatetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOCTYPE_FOOD_REQUEST     = "JNZ Food Request"
DOCTYPE_PROJECT_SETTINGS = "JNZ Project Settings"


class JNZFoodRequest(Document):

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def before_save(self):
        if not self.freq_request_date:
            self.freq_request_date = today()
        self._auto_set_end_date()
        self._generate_day_rows()
        self._validate_no_overlapping_requests()

    def validate(self):
        self._validate_dates()
        self._validate_positive_counts()
        self._validate_no_overlapping_requests()
        

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_no_overlapping_requests(self):
        """
        جلوگیری از ثبت دو درخواست برای یک پروژه در بازه زمانی مشترک
        """
        if not self.freq_project or not self.freq_start_date or not self.freq_end_date:
            return

        # بررسی وجود تداخل در دیتابیس
        overlapping_request = frappe.db.exists(DOCTYPE_FOOD_REQUEST, {
            "freq_project": self.freq_project,
            "name": ["!=", self.name], # خود این سند را در نظر نگیرد (برای زمان ویرایش)
            "docstatus": ["<=", 1],     # سندهای کنسل شده را در نظر نگیرد
            "freq_start_date": ["<=", self.freq_end_date],
            "freq_end_date": [">=", self.freq_start_date]
        })

        if overlapping_request:
            # دریافت تاریخ‌های میلادی سند متداخل
            start, end = frappe.db.get_value(DOCTYPE_FOOD_REQUEST, overlapping_request, ["freq_start_date", "freq_end_date"])
            
            # تبدیل تاریخ‌ها به شمسی با jdatetime
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
        """
        بررسی تک‌تک سطرهای جدول فرزند؛ 
        کاربر نباید بتواند آمار صبحانه، ناهار یا شام را منفی وارد کند.
        """
        for row in self.freq_days or []:
            # چک کردن اینکه آیا یکی از فیلدها منفی است؟
            if (row.frd_breakfast_count or 0) < 0 or \
               (row.frd_lunch_count or 0) < 0 or \
               (row.frd_dinner_count or 0) < 0:
                
               # تبدیل تاریخ میلادی ردیف به شیء تاریخ پایتون و سپس تبدیل به شمسی
                miladi_date = getdate(row.frd_day_date)
                shamsi_obj = jdatetime.date.fromgregorian(date=miladi_date)
                
                # فرمت‌دهی به شکل سال/ماه/روز (مثلا ۱۴۰۵/۰۴/۲۷)
                shamsi_str = shamsi_obj.strftime("%Y/%m/%d")
                frappe.throw(
                    _("Row for date {0} cannot have negative food counts. Please enter 0 or more.")
                    .format(shamsi_str)
                )
    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def _auto_set_end_date(self):
        """
        When freq_end_date is empty and Project Settings has
        projset_auto_generate_end_date enabled, derive:
            freq_end_date = freq_start_date + (projset_request_period_days - 1)
        """
        if self.freq_end_date or not self.freq_start_date:
            return

        settings = frappe.db.get_value(
            DOCTYPE_PROJECT_SETTINGS,
            {"projset_project": self.freq_project},
            ["projset_auto_generate_end_date", "projset_request_period_days"],
            as_dict=True,
        )

        if settings and settings.projset_auto_generate_end_date:
            period_days = (settings.projset_request_period_days or 10) - 1
            self.freq_end_date = add_days(getdate(self.freq_start_date), period_days)

    def _generate_day_rows(self):
        """
        Auto-create one child row per calendar day in [freq_start_date, freq_end_date].
        Preserves user-entered breakfast/lunch/dinner counts for existing dates.
        frd_day_date is read-only — users only edit the count columns.
        """
        if not self.freq_start_date or not self.freq_end_date:
            return

        start = getdate(self.freq_start_date)
        end   = getdate(self.freq_end_date)
        

        
        if end < start:
            return  # _validate_dates will already throw

        # Preserve existing user-entered data keyed by date
        existing = {
            getdate(row.frd_day_date): {
                "frd_breakfast_count": row.frd_breakfast_count or 0,
                "frd_lunch_count":     row.frd_lunch_count     or 0,
                "frd_dinner_count":    row.frd_dinner_count    or 0,
            }
            for row in (self.freq_days or [])
        }

        self.freq_days = []
        
        current        = start

        while current <= end:
            saved = existing.get(current, {})
            self.append("freq_days", {
                "frd_day_date":        str(current),
                "frd_breakfast_count": saved.get("frd_breakfast_count", 0),
                "frd_lunch_count":     saved.get("frd_lunch_count",     0),
                "frd_dinner_count":    saved.get("frd_dinner_count",    0),
            })
            current = add_days(current, 1)
