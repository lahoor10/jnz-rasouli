import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, add_months, getdate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOCTYPE_RATION_RULE        = "JNZ Ration Rule"
DOCTYPE_RATION_RULE_COND   = "JNZ Ration Rule Condition CT"
DOCTYPE_ITEM               = "JNZ Item"
DOCTYPE_CONDITION          = "JNZ Condition"
DOCTYPE_RATION_REQUEST     = "JNZ Ration Request"
DOCTYPE_PROJECT            = "JNZ Project"

CALC_PER_PERSON  = "per_person"
CALC_PER_ROOM    = "per_room"
CALC_PER_PROJECT = "per_project"
CALC_PER_MEETING = "per_meeting"

# condition_type values stored on JNZ Condition (cond_type field)
COND_MEETING = "meeting"
COND_LUNCH   = "lunch"

PERIOD_MONTH     = "per_month"
PERIOD_TWO_MONTH = "per_two_month"

PERIOD_MONTHS_MAP = {
    PERIOD_MONTH:     1,
    PERIOD_TWO_MONTH: 2,
}


class JNZRationRequest(Document):

    def before_save(self):
        if not self.rreq_request_date:
            self.rreq_request_date = now_datetime()
        self._calculate_items()

    def validate(self):
        self._validate_inputs()

    def _validate_inputs(self):
        if (self.resident_workers_count or 0) < 0 or (self.non_resident_workers_count or 0) < 0:
            frappe.throw(_("Workers Count cannot be negative."))

    def _calculate_items(self):
        self.rreq_items = []
        project_doc = frappe.get_doc(DOCTYPE_PROJECT, self.rreq_project)
        
        # دریافت تمام قوانین فعال
        rules = frappe.get_all(
            DOCTYPE_RATION_RULE,
            filters={"active": 1},
            fields=["name", "rrul_item", "rrul_calc_type", "rrul_amount", "rrul_period", "is_for_resident"]
        )

        # دسته‌بندی قوانین برای هر کالا: {item_code: {"general": rule, "resident": rule}}
        rules_by_item = {}
        for rule in rules:
            # بررسی شرایط و دوره زمانی
            conditions = frappe.get_all(DOCTYPE_RATION_RULE_COND, filters={"parent": rule.name}, fields=["rrc_condition_type"])
            if not self._conditions_met(conditions): continue
            if rule.rrul_period != "per_request" and not self._period_eligible(rule): continue
            
            if rule.rrul_item not in rules_by_item: rules_by_item[rule.rrul_item] = {"general": None, "resident": None}
            if rule.get("is_for_resident"): rules_by_item[rule.rrul_item]["resident"] = rule
            else: rules_by_item[rule.rrul_item]["general"] = rule

        # محاسبه نهایی
        for item_code, rule_set in rules_by_item.items():
            total_qty = 0
            
            # محاسبه برای بدون بیتوته (فقط قانون عمومی)
            if rule_set["general"]:
                total_qty += self._calculate_qty(rule_set["general"], project_doc, self.non_resident_workers_count)
            
            # محاسبه برای با بیتوته (اختصاصی اگر بود، وگرنه Fallback به عمومی)
            res_rule = rule_set["resident"] or rule_set["general"]
            if res_rule:
                total_qty += self._calculate_qty(res_rule, project_doc, self.resident_workers_count)

            if total_qty > 0:
                item_doc = frappe.get_doc(DOCTYPE_ITEM, item_code)
                self.append("rreq_items", {
                    "rri_item": item_code,
                    "rri_item_name": item_doc.itm_name,
                    "rri_quantity": total_qty,
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
            return (amount * days) if self.rreq_has_meeting else 0
        return 0

    def _conditions_met(self, conditions):
        for cond in conditions:
            ctype = (cond.rrc_condition_type or "").lower()
            if ctype == "meeting" and not self.rreq_has_meeting: return False
            if ctype == "lunch" and not self.rreq_has_lunch: return False
        return True

    def _period_eligible(self, rule):
        """
        True if enough time has elapsed since the last Ration Request for
        the same project that included this item. Always True when no prior
        request exists.
        """
        months = PERIOD_MONTHS_MAP.get(rule.rrul_period)
        if months is None:
            return True  # per_week or unknown — always eligible

        last = frappe.db.sql(
            """
            SELECT rr.rreq_request_date
              FROM `tabJNZ Ration Request`         AS rr
              JOIN `tabJNZ Ration Request Item CT` AS rri
                ON rri.parent = rr.name
             WHERE rr.rreq_project = %s
               AND rri.rri_item    = %s
               AND rr.name        != %s
               AND rr.docstatus   != 1
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