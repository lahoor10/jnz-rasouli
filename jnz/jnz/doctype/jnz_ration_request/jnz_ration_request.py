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

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def before_save(self):
        if not self.rreq_request_date:
            self.rreq_request_date = now_datetime()
        self._remove_old_drafts()
        self._calculate_items()

    def validate(self):
        self._validate_inputs()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_inputs(self):
        errors = []
        if self.rreq_workers_count is not None and self.rreq_workers_count < 0:
            errors.append(_("Workers Count cannot be negative."))
        if errors:
            frappe.throw("\n".join(errors))

    # ------------------------------------------------------------------
    # Item calculation
    # ------------------------------------------------------------------

    def _calculate_items(self):
        """
        Rebuild rreq_items from scratch. Iterates all active Ration Rules,
        applies condition gates and period eligibility. Items that fail any
        check are silently excluded — not shown as 0.
        """
        self.rreq_items = []

        project_doc = frappe.get_doc(DOCTYPE_PROJECT, self.rreq_project)

        rules = frappe.get_all(
            DOCTYPE_RATION_RULE,
            filters={"active": 1},
            fields=["name", "rrul_item", "rrul_calc_type", "rrul_amount", "rrul_period"],
        )

        excluded = []

        for rule in rules:
            conditions = frappe.get_all(
                DOCTYPE_RATION_RULE_COND,
                filters={"parent": rule.name},
                fields=["rrc_condition", "rrc_condition_type"],
            )

            if not self._conditions_met(conditions):
                continue

            if rule.rrul_period and rule.rrul_period != "per_request":
                if not self._period_eligible(rule):
                    continue

            qty = self._calculate_qty(rule, project_doc)
            if qty is None or qty <= 0:
                excluded.append(rule.rrul_item)
                continue

            item_doc = frappe.get_doc(DOCTYPE_ITEM, rule.rrul_item)
            self.append("rreq_items", {
                "rri_item":      rule.rrul_item,
                "rri_item_name": item_doc.itm_name,
                "rri_quantity":  qty,
                "rri_unit":      item_doc.itm_default_unit,
            })

        if excluded:
            item_list = "\n".join(f"  \u2022 {i}" for i in excluded)
            frappe.msgprint(
                _("The following items were excluded due to zero quantity:\n{0}").format(item_list),
                title=_("Items Excluded"),
                indicator="orange",
            )

    def _conditions_met(self, conditions):
        """Return True only when ALL conditions on the rule are satisfied."""
        if not conditions:
            return True
        for cond in conditions:
            ctype = (cond.rrc_condition_type or "").lower()
            if ctype == COND_MEETING and not self.rreq_has_meeting:
                return False
            if ctype == COND_LUNCH and not self.rreq_has_lunch:
                return False
            # management-approval / special-request / event conditions
            # are resolved outside auto-calculation and do not block here.
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

    def _calculate_qty(self, rule, project_doc):
        calc   = rule.rrul_calc_type
        amount = rule.rrul_amount or 0
        days   = self.days or 1   # ⭐ مهم‌ترین خط

        if calc == CALC_PER_PERSON:
            return amount * (self.rreq_workers_count or 0) * days

        if calc == CALC_PER_ROOM:
            return amount * (project_doc.proj_rooms_count or 0) * days

        if calc == CALC_PER_PROJECT:
            return amount * days

        if calc == CALC_PER_MEETING:
            return (amount * days) if self.rreq_has_meeting else None

        return None

    def _remove_old_drafts(self):
        """Keep only one draft per project."""

        if not self.rreq_project:
            return

        old_drafts = frappe.get_all(
            DOCTYPE_RATION_REQUEST,
            filters={
                "rreq_project": self.rreq_project,
                "docstatus": 0,
                "name": ["!=", self.name or "__new__"],
            },
            pluck="name",
        )

        for draft_name in old_drafts:
            frappe.delete_doc(
                DOCTYPE_RATION_REQUEST,
                draft_name,
                force=True,
                ignore_permissions=True,
            )