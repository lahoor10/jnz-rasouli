import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days, getdate, get_time, nowtime
from frappe.utils.data import get_url_to_form
import jdatetime

DOCTYPE_FOOD_REQUEST = "JNZ Food Request"

class JNZFoodRequest(Document):

    def on_update(self):
        self.send_custom_workflow_email()

    def on_submit(self):
        self.send_custom_workflow_email()

    def on_cancel(self):
        self.send_custom_workflow_email()

    def send_custom_workflow_email(self):
        doc_before_save = self.get_doc_before_save()
        if not doc_before_save:
            return

        previous_state = doc_before_save.workflow_state
        current_state = self.workflow_state

        if current_state == previous_state:
            return

        state_role_map = {
            "Pending Site Supervisor Approval": "JNZ_ROLE_Site_Supervisor",
            "Pending Project Manager Approval": "JNZ_ROLE__Project_Manager",
            "Pending Security Approval": "JNZ_ROLE__Security_Department",
            "Pending HR Approval": "JNZ_ROLE__HR",
            "Pending CEO Office Approval": "JNZ_ROLE__CEO_Office",
            "Pending CEO Approval": "JNZ_ROLE_CEO",
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

    def before_save(self):
        if not self.freq_request_date:
            self.freq_request_date = today()
        self._audit_food_days_changes()

    def validate(self):
        self._validate_dates()
        self._validate_positive_counts()
        self._validate_no_overlapping_requests()
        self._validate_datetime_restrictions()

    def before_update_after_submit(self):
        self._validate_datetime_restrictions()
        self._audit_food_days_changes()

    def _audit_food_days_changes(self):
        if not self.name or not self.freq_project: return
        
        old_doc = self.get_doc_before_save()
        old_state = old_doc.workflow_state if old_doc else None
        current_state = self.workflow_state
        
        is_workflow_action = old_state and (old_state != current_state)
        
        user_fullname = frappe.session.user_fullname or frappe.session.user
        user_roles = frappe.get_all("JNZ Project Members CT", filters={"parent": self.freq_project, "member": frappe.session.user}, pluck="role")
        
        if user_roles:
            role_label = frappe.db.get_value("Role", user_roles[0], "role_name") or user_roles[0]
        else:
            role_label = "مدیر سیستم" if "System Manager" in frappe.get_roles() else "کاربر"

        current_date_str = str(getdate(today()))

        for row in self.get("freq_days") or []:
            if row.frd_base_breakfast is None: row.frd_base_breakfast = row.frd_breakfast_count or 0
            if row.frd_base_lunch is None: row.frd_base_lunch = row.frd_lunch_count or 0
            if row.frd_base_dinner is None: row.frd_base_dinner = row.frd_dinner_count or 0

            if self.docstatus == 1 and str(getdate(row.frd_day_date)) == current_date_str:
                changes = []
                
                old_b = int(row.frd_base_breakfast or 0)
                new_b = int(row.frd_breakfast_count or 0)
                if new_b > old_b:
                    changes.append(f"صبحانه {new_b - old_b} عدد مازاد درخواست شد")
                    row.frd_served_breakfast = new_b

                old_l = int(row.frd_base_lunch or 0)
                new_l = int(row.frd_lunch_count or 0)
                if new_l > old_l:
                    changes.append(f"ناهار {new_l - old_l} عدد مازاد درخواست شد")
                    row.frd_served_lunch = new_l

                old_d = int(row.frd_base_dinner or 0)
                new_d = int(row.frd_dinner_count or 0)
                if new_d > old_d:
                    changes.append(f"شام {new_d - old_d} عدد مازاد درخواست شد")
                    row.frd_served_dinner = new_d

                if changes:
                    audit_text = f"کاربر {user_fullname} با نقش {_(role_label)}: " + " و ".join(changes) + "."
                    row.frd_audit_text = audit_text
                    row.frd_user_note = ""
                    
                    row.frd_base_breakfast = new_b
                    row.frd_base_lunch = new_l
                    row.frd_base_dinner = new_d

            elif is_workflow_action:
                changes = []
                
                old_b = int(row.frd_base_breakfast or 0)
                new_b = int(row.frd_breakfast_count or 0)
                if new_b != old_b: changes.append(f"صبحانه را از {old_b} به {new_b}")

                old_l = int(row.frd_base_lunch or 0)
                new_l = int(row.frd_lunch_count or 0)
                if new_l != old_l: changes.append(f"ناهار را از {old_l} به {new_l}")

                old_d = int(row.frd_base_dinner or 0)
                new_d = int(row.frd_dinner_count or 0)
                if new_d != old_d: changes.append(f"شام را از {old_d} به {new_d}")

                if changes:
                    meal_changes_text = " و ".join(changes)
                    audit_text = f"کاربر {user_fullname} با نقش {_(role_label)} مقدار {meal_changes_text} تغییر داد."
                    row.frd_audit_text = audit_text
                    row.frd_user_note = ""
                
                row.frd_base_breakfast = new_b
                row.frd_base_lunch = new_l
                row.frd_base_dinner = new_d
                    
    @frappe.whitelist()
    def get_calculated_end_date(self):
        if not self.freq_project or not self.freq_start_date:
            return None

        settings = frappe.db.get_value(
            "JNZ Project",
            self.freq_project,
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
        if not self.freq_start_date or not self.freq_end_date: return
        start = getdate(self.freq_start_date)
        end   = getdate(self.freq_end_date)
        if end < start: return

        b_default = self.default_breakfast or 0
        l_default = self.default_lunch or 0
        d_default = self.default_dinner or 0

        existing = {
            getdate(row.frd_day_date): {
                "frd_breakfast_count": row.frd_breakfast_count or 0,
                "frd_served_breakfast": row.frd_served_breakfast or 0,
                "frd_lunch_count":     row.frd_lunch_count     or 0,
                "frd_served_lunch":     row.frd_served_lunch     or 0,
                "frd_dinner_count":    row.frd_dinner_count    or 0,
                "frd_served_dinner":    row.frd_served_dinner    or 0,
                "frd_audit_text":      row.frd_audit_text,
                "frd_user_note":       row.frd_user_note,
                "frd_base_breakfast":  row.frd_base_breakfast,
                "frd_base_lunch":      row.frd_base_lunch,
                "frd_base_dinner":     row.frd_base_dinner,
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
                    "frd_served_breakfast": saved.get("frd_served_breakfast", 0),
                    "frd_lunch_count":     saved.get("frd_lunch_count",     0),
                    "frd_served_lunch":     saved.get("frd_served_lunch",     0),
                    "frd_dinner_count":    saved.get("frd_dinner_count",    0),
                    "frd_served_dinner":    saved.get("frd_served_dinner",    0),
                    "frd_audit_text":      saved.get("frd_audit_text"),
                    "frd_user_note":       saved.get("frd_user_note"),
                    "frd_base_breakfast":  saved.get("frd_base_breakfast"),
                    "frd_base_lunch":      saved.get("frd_base_lunch"),
                    "frd_base_dinner":     saved.get("frd_base_dinner"),
                })
            else:
                self.append("freq_days", {
                    "frd_day_date":        str(current),
                    "frd_breakfast_count": b_default,
                    "frd_served_breakfast": b_default,
                    "frd_lunch_count":     l_default,
                    "frd_served_lunch":     l_default,
                    "frd_dinner_count":    d_default,
                    "frd_served_dinner":    d_default,
                })
            current = add_days(current, 1)

    @frappe.whitelist()
    def apply_default_counts_to_table(self):
        b_count = self.default_breakfast or 0
        l_count = self.default_lunch or 0
        d_count = self.default_dinner or 0
        for row in self.freq_days or []:
            row.frd_breakfast_count = b_count
            row.frd_served_breakfast = b_count
            row.frd_lunch_count = l_count
            row.frd_served_lunch = l_count
            row.frd_dinner_count = d_count
            row.frd_served_dinner = d_count

    def _validate_datetime_restrictions(self):
        if "System Manager" in frappe.get_roles(): return
        if not self.freq_project: return

        settings = frappe.db.get_value(
            "JNZ Project", self.freq_project,
            ["projset_request_deadline_days", "projset_edit_start_time", "projset_edit_end_time"], as_dict=True
        )
        if not settings: return

        current_date = getdate(today())
        user_roles = frappe.get_roles()
        is_supervisor = "JNZ_ROLE_Site_Supervisor" in user_roles

        if self.docstatus == 0 and self.freq_start_date:
            deadline_days = settings.get("projset_request_deadline_days") or 2
            min_allowed_start_date = add_days(current_date, deadline_days)
            if getdate(self.freq_start_date) < min_allowed_start_date:
                shamsi_limit = jdatetime.date.fromgregorian(date=min_allowed_start_date).strftime("%Y/%m/%d")
                frappe.throw(_("ثبت درخواست برای این بازه مجاز نیست. تاریخ شروع نمی‌تواند زودتر از {0} باشد.").format(shamsi_limit))

        old_doc = self.get_doc_before_save()
        if old_doc:
            old_rows = {str(getdate(r.frd_day_date)): r for r in old_doc.get("freq_days") or []}
            
            # رفع باگ: تبدیل زمان فعلی و زمان‌های تنظیمات به شیء واقعی زمان (Time Object) جهت مقایسه معتبر ریاضی
            current_time = get_time(nowtime())
            start_time = get_time(settings.get("projset_edit_start_time") or "08:00:00")
            end_time = get_time(settings.get("projset_edit_end_time") or "11:00:00")

            for row in self.get("freq_days") or []:
                row_date_str = str(getdate(row.frd_day_date))
                if row_date_str in old_rows:
                    old_row = old_rows[row_date_str]
                    
                    is_modified = (
                        int(row.frd_breakfast_count or 0) != int(old_row.frd_breakfast_count or 0) or
                        int(row.frd_lunch_count or 0) != int(old_row.frd_lunch_count or 0) or
                        int(row.frd_dinner_count or 0) != int(old_row.frd_dinner_count or 0)
                    )

                    if is_modified:
                        row_date = getdate(row.frd_day_date)
                        
                        if self.docstatus == 1:
                            if not is_supervisor:
                                frappe.throw(_("پس از تایید نهایی سند، فقط سرپرست کارگاه مجاز به ثبت درخواست مازاد است."))
                            if row_date != current_date:
                                frappe.throw(_("سرپرست کارگاه پس از تایید نهایی سند، فقط مجاز به ویرایش آمار روز جاری (امروز) است."))
                            if not (start_time <= current_time <= end_time):
                                frappe.throw(_("ثبت درخواست مازاد روز جاری فقط در بازه ساعت {0} تا {1} امکان‌پذیر است.").format(start_time.strftime("%H:%M"), end_time.strftime("%H:%M")))
                            if (int(row.frd_breakfast_count or 0) < int(old_row.frd_breakfast_count or 0) or
                                int(row.frd_lunch_count or 0) < int(old_row.frd_lunch_count or 0) or
                                int(row.frd_dinner_count or 0) < int(old_row.frd_dinner_count or 0)):
                                frappe.throw(_("پس از تایید نهایی، شما فقط مجاز به افزایش آمار (درخواست مازاد) هستید و نمی‌توانید تعداد را کاهش دهید."))
                        else:
                            if row_date < current_date:
                                frappe.throw(_("امکان ویرایش آمار روزهای گذشته وجود ندارد."))
                            if row_date == current_date:
                                if not (start_time <= current_time <= end_time):
                                    frappe.throw(_("ویرایش آمار غذای روز جاری خارج از بازه مجاز (ساعت {0} تا {1}) امکان‌پذیر نیست.").format(start_time.strftime("%H:%M"), end_time.strftime("%H:%M")))

    def _validate_no_overlapping_requests(self):
        if not self.freq_project or not self.freq_start_date or not self.freq_end_date: return
        overlapping_request = frappe.db.exists(DOCTYPE_FOOD_REQUEST, {
            "freq_project": self.freq_project, "name": ["!=", self.name],
            "docstatus": ["<=", 1], "freq_start_date": ["<=", self.freq_end_date], "freq_end_date": [">=", self.freq_start_date]
        })
        if overlapping_request:
            start, end = frappe.db.get_value(DOCTYPE_FOOD_REQUEST, overlapping_request, ["freq_start_date", "freq_end_date"])
            shamsi_start = jdatetime.date.fromgregorian(date=getdate(start)).strftime("%Y/%m/%d")
            shamsi_end = jdatetime.date.fromgregorian(date=getdate(end)).strftime("%Y/%m/%d")
            frappe.throw(_("The selected date range overlaps with an existing request. The existing request date is from {0} to {1} in request {2}.").format(shamsi_start, shamsi_end, overlapping_request))
            
    def _validate_dates(self):
        errors = []
        if not self.freq_start_date: errors.append(_("Start Date is required."))
        if not self.freq_end_date: errors.append(_("End Date is required. Use 'Fill End Date' button if needed."))
        if self.docstatus == 0 and self.freq_start_date and getdate(self.freq_start_date) < getdate(today()):
            errors.append(_("Start Date cannot be before today."))
        if (self.freq_start_date and self.freq_end_date and getdate(self.freq_end_date) < getdate(self.freq_start_date)):
            errors.append(_("End Date cannot be before Start Date."))
        if errors: frappe.throw("\n".join(errors))
            
    def _validate_positive_counts(self):
        for row in self.freq_days or []:
            if (row.frd_breakfast_count or 0) < 0 or (row.frd_lunch_count or 0) < 0 or (row.frd_dinner_count or 0) < 0:
                miladi_date = getdate(row.frd_day_date)
                shamsi_str = jdatetime.date.fromgregorian(date=miladi_date).strftime("%Y/%m/%d")
                frappe.throw(_("Row for date {0} cannot have negative food counts. Please enter 0 or more.").format(shamsi_str))