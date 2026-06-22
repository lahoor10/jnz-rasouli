import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, add_months, getdate
import jdatetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOCTYPE_RATION_RULE        = "JNZ Ration Rule"
DOCTYPE_RATION_RULE_COND   = "JNZ Ration Rule Condition CT"
DOCTYPE_ITEM               = "JNZ Item"
DOCTYPE_PROJECT            = "JNZ Project"

CALC_PER_PERSON  = "per_person"
CALC_PER_ROOM    = "per_room"
CALC_PER_PROJECT = "per_project"
CALC_PER_MEETING = "per_meeting"

PERIOD_MONTH     = "per_month"
PERIOD_TWO_MONTH = "per_two_month"

PERIOD_MONTHS_MAP = {
    PERIOD_MONTH:     1,
    PERIOD_TWO_MONTH: 2,
}

WORKFLOW_ROLE_MAP = {
    "Draft": "support_supervisor", # در حالت درفت بگذارید روی ساپورت محاسبات انجام شود
    "Pending Support Approval": "support_supervisor",
    "Pending Commercial Approval": "commercial_manager",
    "Pending CEO Office Approval": "ceo_office",
    "Pending Security Approval": "security",
    "Pending Finance Approval": "finance",
    "Pending CEO Approval": "ceo",
    "Approved": "ceo" # در حالت نهایی بر اساس آخرین نظر مدیرعامل بماند
}

class JNZRationRequest(Document):

    def before_save(self):
        if not self.rreq_request_date:
            self.rreq_request_date = now_datetime()
        
        # مقداردهی اولیه فیلدهای تعدیل تاییدکنندگان (جلوگیری از کد تکراری)
        self.set_default_approver_counts()
                
        self._calculate_items()

    def validate(self):
        self._validate_inputs()
        self._validate_ration_period_and_duplicate()

    def _validate_inputs(self):
        if (self.draft_resident_workers_count or 0) < 0 or (self.draft_non_resident_workers_count or 0) < 0:
            frappe.throw(_("Workers Count cannot be negative."))

    def _validate_ration_period_and_duplicate(self):
        """بررسی بازه زمانی ثبت و جلوگیری سخت‌گیرانه از ایجاد بیش از یک درخواست در ماه شمسی برای پروژه"""
        
        raw_date = getdate(self.rreq_request_date or now_datetime())
        pure_date = raw_date.date() if hasattr(raw_date, "date") else raw_date
        
        # تبدیل تاریخ میلادی به شمسی
        j_date = jdatetime.date.fromgregorian(date=pure_date)
        j_year, j_month, j_day = j_date.year, j_date.month, j_date.day
        
        # جلوگیری از ثبت بیش از یک درخواست در ماه شمسی جاری برای پروژه
        if j_month <= 6:
            last_day = 31
        elif j_month <= 11:
            last_day = 30
        else:
            last_day = 30 if jdatetime.date(j_year, 1, 1).is_leap() else 29

        start_gregorian = jdatetime.date(j_year, j_month, 1).togregorian()
        end_gregorian = jdatetime.date(j_year, j_month, last_day).togregorian()

        # بررسی وجود هرگونه درخواست تکراری برای کارگاه بدون فیلتر کردن docstatus
        duplicate_request = frappe.db.exists(
            "JNZ Ration Request",
            {
                "rreq_project": self.rreq_project,
                "rreq_request_date": ["between", [start_gregorian, end_gregorian]],
                "name": ["!=", self.name]
            }
        )

        if duplicate_request:
            frappe.throw(
                _("A ration request has already been created for this project in the current month ({0}). Only one request is allowed.")
                .format(duplicate_request)
            )
        
        # بررسی بازه زمانی ۲۰ تا ۲۵ هر ماه شمسی (بند ۴ و ۵)
        has_special_role = "Administrator" in frappe.get_roles() or "JNZ_ROLE_Ration_Officer" in frappe.get_roles()

        if not has_special_role:
            if not (20 <= j_day <= 25):
                frappe.throw(_("Ration Requests can only be submitted between the 20th and 25th of each Jalali month."))

    def _calculate_items(self):
        # تغییر تسک ۹ و ۱۰: نگهداری سهمیه‌های دستی وارد شده قبل از پاک شدن جدول
        old_allocations = {}
        for row in self.get("rreq_items") or []:
            old_allocations[row.rri_item] = {
                "allocated": row.rri_allocated_quantity,
                "delivered": row.rri_delivered_quantity
            }

        self.rreq_items = []
        if not self.rreq_project:
            return

        project_doc = frappe.get_doc(DOCTYPE_PROJECT, self.rreq_project)
        
        current_state = self.get("workflow_state")
        role_prefix = WORKFLOW_ROLE_MAP.get(current_state)

        if role_prefix:
            resident_count = self.get(f"{role_prefix}_resident_count") or 0
            non_resident_count = self.get(f"{role_prefix}_non_resident_count") or 0
        else:
            resident_count = self.draft_resident_workers_count or 0
            non_resident_count = self.draft_non_resident_workers_count or 0

        rules = frappe.get_all(
            DOCTYPE_RATION_RULE,
            filters={"active": 1},
            fields=["name", "rrul_item", "rrul_calc_type", "rrul_amount", "rrul_period", "is_for_resident"]
        )

        rules_by_item = {}
        for rule in rules:
            conditions = frappe.get_all(DOCTYPE_RATION_RULE_COND, filters={"parent": rule.name}, fields=["rrc_condition", "rrc_condition_type"])
            if not self._conditions_met(conditions): continue
        
            if rule.rrul_item not in rules_by_item: 
                rules_by_item[rule.rrul_item] = {"general": None, "resident": None}
            
            if rule.get("is_for_resident"): 
                rules_by_item[rule.rrul_item]["resident"] = rule
            else: 
                rules_by_item[rule.rrul_item]["general"] = rule

        for item_code, rule_set in rules_by_item.items():
            total_qty = 0
            
            if rule_set["general"]:
                total_qty += self._calculate_qty(rule_set["general"], project_doc, non_resident_count)
            
            res_rule = rule_set["resident"] or rule_set["general"]
            if res_rule:
                total_qty += self._calculate_qty(res_rule, project_doc, resident_count)

            if total_qty > 0:
                item_doc = frappe.get_doc(DOCTYPE_ITEM, item_code)
                
                # تغییر تسک ۹ و ۱۰: بازیابی مقادیر ویرایش‌شده دستی قبلی، در غیر این صورت برابر مقدار درخواستی
                alloc = old_allocations.get(item_code, {}).get("allocated", total_qty)
                deliv = old_allocations.get(item_code, {}).get("delivered", total_qty)

                self.append("rreq_items", {
                    "rri_item": item_code,
                    "rri_item_name": item_doc.itm_name,
                    "rri_quantity": total_qty,
                    "rri_allocated_quantity": alloc,  # تسک ۹
                    "rri_delivered_quantity": deliv,  # تسک ۱۰
                    "rri_unit": item_doc.itm_default_unit,
                })

    def _calculate_qty(self, rule, project_doc, worker_count):
        calc = rule.rrul_calc_type
        amount = rule.rrul_amount or 0
        days = self.days or 1

        if calc == CALC_PER_PERSON:
            return amount * (worker_count or 0) * days
        elif calc == CALC_PER_ROOM:
            return amount * (project_doc.proj_rooms_count or 0) * days
        elif calc == CALC_PER_PROJECT:
            return amount * days
        elif calc == CALC_PER_MEETING:
            # تغییر این بخش برای بند ۴: اعمال تعداد جلسات کارگاه در جیره روزانه
            if self.rreq_has_meeting:
                meetings_count = project_doc.get("meetings_count") or 1
                return amount * days * meetings_count
            return 0
        return 0

    def _conditions_met(self, conditions):
        for cond in conditions:
            ctype = (cond.rrc_condition_type or "").lower()
            if ctype == "meeting" and not self.rreq_has_meeting: return False
            if ctype == "lunch" and not self.rreq_has_lunch: return False
        return True

    def _period_eligible(self, rule):
        months = PERIOD_MONTHS_MAP.get(rule.rrul_period)
        if months is None:
            return True

        last = frappe.db.sql(
            """
            SELECT rr.rreq_request_date
              FROM `tabJNZ Ration Request`         AS rr
              JOIN `tabJNZ Ration Request Item CT` AS rri
                ON rri.parent = rr.name
             WHERE rr.rreq_project = %s
               AND rri.rri_item    = %s
               AND rr.name        != %s
               AND rr.docstatus    = 1
             ORDER BY rr.rreq_request_date DESC
             LIMIT 1
            """,
            (self.rreq_project, rule.rrul_item, self.name or "__new__"),
            as_dict=False,
        )

        if not last:
            return True

        threshold = add_months(last[0][0], months)
        return now_datetime() >= threshold
    
    def set_default_approver_counts(self):
        # ۱. بررسی اینکه آیا واقعاً تغییر وضعیت (ورک‌فلو) اتفاق افتاده است یا خیر
        old_state = self.db_get("workflow_state") if self.name else None
        new_state = self.get("workflow_state")
        
        # اگر کاربر فقط دارد فرم را در همان مرحله ذخیره/ویرایش می‌کند، اصلاً فیلدها را اوررایت نکن
        # تا بتواند عمداً عدد 0 یا هر عدد دیگری را وارد و ذخیره کند.
        if old_state == new_state and old_state is not None:
            return

        # ترتیب ترتیبی مراحل ورک‌فلو و پیشوندهای آن‌ها
        order = [
            'support_supervisor',
            'commercial_manager',
            'ceo_office',
            'security',
            'finance',
            'ceo'
        ]
        
        # مپ کردن وضعیت قبلی به پیشوند فیلد (یعنی فیلدی که کاربر تازه رویش تغییرات داده و تایید کرده)
        state_to_prefix = {
            "Draft": "draft", # شروع کار
            "Pending Support Approval": "support_supervisor",
            "Pending Commercial Approval": "commercial_manager",
            "Pending CEO Office Approval": "ceo_office",
            "Pending Security Approval": "security",
            "Pending Finance Approval": "finance",
            "Pending CEO Approval": "ceo"
        }
        
        old_prefix = state_to_prefix.get(old_state or "Draft")
        
        # ۲. تعیین مقدار مبنا (Source):
        # اگر از درفت داریم خارج می‌شویم، مبنا ورودی اصلی فرم است.
        # در غیر این صورت، مبنا عددی است که مسئولِ مرحله‌ی قبلی تایید کرده است.
        if old_prefix == "draft":
            source_res = self.get("draft_resident_workers_count") or 0
            source_non_res = self.get("draft_non_resident_workers_count") or 0
            start_update_idx = 0 # از اولین مسئول به بعد آپدیت شوند
        else:
            source_res = self.get(f"{old_prefix}_resident_count") or 0
            source_non_res = self.get(f"{old_prefix}_non_resident_count") or 0
            start_update_idx = order.index(old_prefix) + 1 # از مسئول بعدی به بعد آپدیت شوند

        # ۳. تزریق آبشاری به آینده (Forward Cascade):
        # این حلقه فقط فیلدهای مراحل «آینده» را با این مبنای جدید بروزرسانی می‌کند 
        # و به مراحل «گذشته» هیچ کاری ندارد تا تاریخچه دست‌نخورده بماند.
        for j in range(start_update_idx, len(order)):
            future_prefix = order[j]
            self.set(f"{future_prefix}_resident_count", source_res)
            self.set(f"{future_prefix}_non_resident_count", source_non_res)

@frappe.whitelist()
def get_user_project_roles(project, user):
    """
    دریافت لیست نقش‌های یک کاربر در یک پروژه خاص از جدول JNZ Project Members CT
    """
    if not project or not user:
        return []
        
    roles = frappe.get_all(
        "JNZ Project Members CT",
        filters={"parent": project, "member": user},
        pluck="role"
    )
    return roles