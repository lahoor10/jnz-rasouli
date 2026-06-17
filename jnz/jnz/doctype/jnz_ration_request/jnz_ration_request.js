// JNZ Ration Request — Form JS
// §8.1 OOP class-based  |  §8.3 field clearing  |  §8.4 cascade-safe set_value
// §4.5 depends_on preferred for static behaviour

const DOCTYPE = "JNZ Ration Request";

frappe.ui.form.on(DOCTYPE, {
    refresh(frm) {
        new JNZRationRequestFormController(frm).init();
    },

    rreq_project(frm) {
        new JNZRationRequestFieldHandler(frm).on_project_change();
    },

    rreq_has_meeting(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },

    rreq_has_lunch(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },

    rreq_workers_count(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },
});


// ---------------------------------------------------------------------------
// FormController — buttons, grid, indicators  (§8.1)
// ---------------------------------------------------------------------------

class JNZRationRequestFormController {
    constructor(frm) {
        this.frm = frm;
    }

    init() {
        this._lockItemsGrid();
        this._setStatusIndicator();
        if (this.frm.doc.docstatus === 0) {
            this._addRecalcButton();
        }
    }

    _lockItemsGrid() {
        // §8.6 — use update_docfield_property + reset_grid for structural changes
        const grid = this.frm.fields_dict["rreq_items"]?.grid;
        if (!grid) return;
        grid.update_docfield_property("rri_item",     "read_only", 1);
        grid.update_docfield_property("rri_quantity", "read_only", 1);
        grid.update_docfield_property("rri_unit",     "read_only", 1);
        grid.reset_grid();
    }

    _setStatusIndicator() {
        const doc       = this.frm.doc;
        const itemCount = (doc.rreq_items || []).length;
        if (doc.docstatus === 1) {
            this.frm.page.set_indicator(__("Submitted"), "green");
        } else if (itemCount === 0 && doc.rreq_project) {
            this.frm.page.set_indicator(__("No Items"), "orange");
        }
    }

    _addRecalcButton() {
        this.frm.add_custom_button(__("Recalculate Items"), () => {
            // Actual recalc runs server-side in before_save
            this.frm.save().then(() => {
                frappe.show_alert({ message: __("Items recalculated."), indicator: "green" });
            });
        }, __("Actions"));
    }
}


// ---------------------------------------------------------------------------
// FieldHandler — reactive field behaviour  (§8.1)
// ---------------------------------------------------------------------------

class JNZRationRequestFieldHandler {
    constructor(frm) {
        this.frm = frm;
    }

    on_project_change() {
        // Clear stale items from the previous project  (§8.4 cascade-safe)
        if ((this.frm.doc.rreq_items || []).length) {
            Object.assign(this.frm.doc, { rreq_items: [] });
            this.frm.dirty();
            this.frm.refresh_fields(["rreq_items"]);
        }
    }

    on_flag_change() {
        // Nudge user to save so server recalculates
        if (this.frm.doc.rreq_project && !this.frm.is_new()) {
            frappe.show_alert({
                message: __("Save the document to refresh item quantities."),
                indicator: "blue",
            });
        }
    }
}
