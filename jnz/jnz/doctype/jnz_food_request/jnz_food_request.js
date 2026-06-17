// JNZ Food Request — Form JS
// §8.1 OOP class-based  |  §8.4 cascade-safe set_value  |  §8.3 field clearing

const DOCTYPE = "JNZ Food Request";

frappe.ui.form.on(DOCTYPE, {
    refresh(frm) {
        new JNZFoodRequestFormController(frm).init();
    },

    freq_project(frm) {
        new JNZFoodRequestDateHandler(frm).on_project_change();
    },

    freq_start_date(frm) {
        new JNZFoodRequestDateHandler(frm).on_start_date_change();
    },

    freq_end_date(frm) {
        new JNZFoodRequestDateHandler(frm).on_end_date_change();
    },
});


// ---------------------------------------------------------------------------
// FormController — buttons, grid lock, indicator  (§8.1)
// ---------------------------------------------------------------------------

class JNZFoodRequestFormController {
    constructor(frm) {
        this.frm = frm;
    }

    init() {
        this._lockDayDateColumn();
        this._setStatusIndicator();
        if (this.frm.doc.docstatus === 0) {
            this._addRegenerateDaysButton();
        }
    }

    _lockDayDateColumn() {
        // §8.6 — structural change: use reset_grid (not refresh_field)
        const grid = this.frm.fields_dict["freq_days"]?.grid;
        if (!grid) return;
        grid.update_docfield_property("frd_day_date", "read_only", 1);
        grid.reset_grid();
    }

    _setStatusIndicator() {
        if (this.frm.doc.docstatus === 1) {
            this.frm.page.set_indicator(__("Submitted"), "green");
        }
    }

    _addRegenerateDaysButton() {
        this.frm.add_custom_button(__("Regenerate Days"), () => {
            if (!this.frm.doc.freq_start_date) {
                frappe.msgprint(__("Please set a Start Date first."));
                return;
            }
            this.frm.save().then(() => {
                frappe.show_alert({ message: __("Daily rows regenerated."), indicator: "green" });
            });
        }, __("Actions"));
    }
}


// ---------------------------------------------------------------------------
// DateHandler — reactive date field behaviour  (§8.1)
// ---------------------------------------------------------------------------

class JNZFoodRequestDateHandler {
    constructor(frm) {
        this.frm = frm;
    }

    on_project_change() {
        // Clear date range and rows so Project Settings can re-derive end_date  (§8.4)
        const updates = { freq_end_date: "", freq_days: [] };
        Object.assign(this.frm.doc, updates);
        this.frm.dirty();
        this.frm.refresh_fields(["freq_end_date", "freq_days"]);
    }

    on_start_date_change() {
        const doc = this.frm.doc;
        // If end_date is now before the new start_date, clear it so auto-calc re-fires on save
        if (
            doc.freq_end_date &&
            doc.freq_start_date &&
            frappe.datetime.str_to_obj(doc.freq_end_date) <
                frappe.datetime.str_to_obj(doc.freq_start_date)
        ) {
            Object.assign(this.frm.doc, { freq_end_date: "" });
            this.frm.dirty();
            this.frm.refresh_fields(["freq_end_date"]);
            frappe.show_alert({
                message: __("End Date cleared — it was before the new Start Date."),
                indicator: "orange",
            });
        }
    }

    on_end_date_change() {
        const doc = this.frm.doc;
        if (
            doc.freq_end_date &&
            doc.freq_start_date &&
            frappe.datetime.str_to_obj(doc.freq_end_date) <
                frappe.datetime.str_to_obj(doc.freq_start_date)
        ) {
            frappe.msgprint(__("End Date cannot be before Start Date."));
            Object.assign(this.frm.doc, { freq_end_date: "" });
            this.frm.dirty();
            this.frm.refresh_fields(["freq_end_date"]);
        }
    }
}
