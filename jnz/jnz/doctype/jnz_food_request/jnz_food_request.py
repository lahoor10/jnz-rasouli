import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days, getdate

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

    def validate(self):
        self._validate_dates()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_dates(self):
        errors = []
        if not self.freq_start_date:
            errors.append(_("Start Date is required."))
        if (
            self.freq_start_date
            and self.freq_end_date
            and getdate(self.freq_end_date) < getdate(self.freq_start_date)
        ):
            errors.append(_("End Date cannot be before Start Date."))
        if errors:
            frappe.throw("\n".join(errors))

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
