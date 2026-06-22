// JNZ Food Request — Form JS
// §8.1 OOP class-based  |  §8.4 cascade-safe set_value  |  §8.3 field clearing

const DOCTYPE = "JNZ Food Request";

frappe.ui.form.on(DOCTYPE, {
    // خلاقیت دولوپر: تبدیل کل لایوت فرم به عرض ۱۰۰٪ صفحه جهت جلوگیری از فشرده شدن جدول عریض
    onload(frm) {
        $(".form-container").css({
            "max-width": "100%",
            "padding-left": "30px",
            "padding-right": "30px"
        });
        $(".layout-main-section").css("max-width", "100%");
    },

    // تزریق استایل‌های گرافیکی (Formatter) برای زیباسازی فیلد ممیزی در جدول
    setup(frm) {
        let audit_df = frappe.meta.get_docfield("JNZ Food Request Day CT", "frd_audit_text", frm.docname);
        if (audit_df) {
            audit_df.formatter = function(value) {
                if (!value) return "";
                return `<div style="max-height: 65px; overflow-y: auto; font-size: 11px; line-height: 1.6; color: #2c5282; background-color: #ebf8ff; border: 1px solid #bee3f8; padding: 4px 6px; border-radius: 4px; white-space: pre-wrap; direction: rtl; text-align: right;">${value}</div>`;
            };
        }
    },

    refresh(frm) {
        new JNZFoodRequestFormController(frm).init();
        // مخفی کردن دکمه‌های غیرمجاز ورک‌فلو
        if (!frm.is_new() && frm.doc.workflow_state) {
            
            // گرفتن نام پروژه با توجه به داک‌تایپ (جیره یا غذا)
            let proj_name = frm.doc.rreq_project || frm.doc.freq_project;
            
            if (proj_name) {
                frappe.call({
                    method: "jnz.permissions.get_unauthorized_workflow_actions",
                    args: {
                        doctype: frm.doctype,
                        project_name: proj_name,
                        current_state: frm.doc.workflow_state
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            let css_rules = "";
                            
                            r.message.forEach(action => {
                                let translated_action = __(action);
                                
                                // ساخت قوانین CSS برای مخفی کردن قطعی
                                css_rules += `
                                    [data-label="${action}"] { display: none !important; }
                                    [data-label="${translated_action}"] { display: none !important; }
                                    button:contains('${action}') { display: none !important; }
                                    button:contains('${translated_action}') { display: none !important; }
                                    a.dropdown-item:contains('${action}') { display: none !important; }
                                    a.dropdown-item:contains('${translated_action}') { display: none !important; }
                                `;
                            });

                            if (css_rules) {
                                // تزریق استایل به مرورگر
                                $("<style type='text/css'>" + css_rules + "</style>").appendTo("head");
                            }
                        }
                    }
                });
            }
        }
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

    autofill_end_date(frm) {
        new JNZFoodRequestDateHandler(frm).handle_autofill_end_date();
    },

    update_tab(frm) {
        new JNZFoodRequestFormController(frm).handle_update_table_click();
    }
});


// ارث‌بری خودکار آمار سرو شده به محض تغییر تعداد دستی توسط کاربر
frappe.ui.form.on("JNZ Food Request Day CT", {
    frd_breakfast_count: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        frappe.model.set_value(cdt, cdn, "frd_served_breakfast", row.frd_breakfast_count || 0);
    },
    frd_lunch_count: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        frappe.model.set_value(cdt, cdn, "frd_served_lunch", row.frd_lunch_count || 0);
    },
    frd_dinner_count: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        frappe.model.set_value(cdt, cdn, "frd_served_dinner", row.frd_dinner_count || 0);
    }
});


// ---------------------------------------------------------------------------
// FormController — Grid adjustments & Bulk Defaults Action
// ---------------------------------------------------------------------------

class JNZFoodRequestFormController {
    constructor(frm) {
        this.frm = frm;
    }

    init() {
        this._lockDayDateColumn();
        this._setStatusIndicator();
        
        this.frm.__old_start_date = this.frm.doc.freq_start_date;
        this.frm.__old_end_date = this.frm.doc.freq_end_date;
    }

    _lockDayDateColumn() {
        const grid = this.frm.fields_dict["freq_days"]?.grid;
        if (!grid) return;
        grid.update_docfield_property("frd_day_date", "read_only", 1);
        grid.update_docfield_property("frd_audit_text", "read_only", 1);
        grid.reset_grid();
    }

    _setStatusIndicator() {
        if (this.frm.doc.docstatus === 1) {
            this.frm.page.set_indicator(__("Submitted"), "green");
        }
    }

    handle_update_table_click() {
        const doc = this.frm.doc;
        if (!doc.freq_start_date || !doc.freq_end_date) {
            frappe.msgprint(__("Please select both Start Date and End Date first."));
            return;
        }

        const b = doc.default_breakfast || 0;
        const l = doc.default_lunch || 0;
        const d = doc.default_dinner || 0;

        if (!doc.freq_days || doc.freq_days.length === 0) {
            new JNZFoodRequestDateHandler(this.frm).build_table_via_server();
            setTimeout(() => { this._apply_bulk_counts(b, l, d); }, 500);
        } else {
            frappe.confirm(
                __("Are you sure you want to overwrite all rows in the table with the default breakfast ({0}), lunch ({1}), and dinner ({2}) counts?", [b, l, d]),
                () => {
                    this._apply_bulk_counts(b, l, d);
                }
            );
        }
    }

    _apply_bulk_counts(b, l, d) {
        (this.frm.doc.freq_days || []).forEach(row => {
            frappe.model.set_value(row.doctype, row.name, "frd_breakfast_count", b);
            frappe.model.set_value(row.doctype, row.name, "frd_served_breakfast", b);
            frappe.model.set_value(row.doctype, row.name, "frd_lunch_count", l);
            frappe.model.set_value(row.doctype, row.name, "frd_served_lunch", l);
            frappe.model.set_value(row.doctype, row.name, "frd_dinner_count", d);
            frappe.model.set_value(row.doctype, row.name, "frd_served_dinner", d);
            frappe.model.set_value(row.doctype, row.name, "frd_user_note", "");
        });
        this.frm.refresh_field("freq_days");
        frappe.show_alert({ message: __("Default counts successfully applied to all rows."), indicator: "green" });
    }
}


// ---------------------------------------------------------------------------
// DateHandler — Manual Triggering & Clean Table Re-Generation
// ---------------------------------------------------------------------------

class JNZFoodRequestDateHandler {
    constructor(frm) {
        this.frm = frm;
    }

    on_project_change() {
        this.frm.set_value("freq_end_date", "");
        this.frm.clear_table("freq_days");
        this.frm.refresh_field("freq_days");
        this.frm.__old_start_date = "";
        this.frm.__old_end_date = "";
    }

    on_start_date_change() {
        const doc = this.frm.doc;
        if (doc.freq_start_date && doc.freq_end_date) {
            if (frappe.datetime.str_to_obj(doc.freq_end_date) < frappe.datetime.str_to_obj(doc.freq_start_date)) {
                this.frm.set_value("freq_end_date", "");
            } else {
                this._process_table_sync();
            }
        }
        this.frm.__old_start_date = doc.freq_start_date;
    }

    on_end_date_change() {
        this._process_table_sync();
    }

    handle_autofill_end_date() {
        const doc = this.frm.doc;
        if (!doc.freq_project || !doc.freq_start_date) {
            frappe.msgprint(__("Please select Project and Start Date first."));
            return;
        }

        frappe.call({
            doc: this.frm.doc,
            method: 'get_calculated_end_date',
            callback: (r) => {
                if (r.message) {
                    this.frm.set_value('freq_end_date', r.message);
                    frappe.show_alert({ message: __("End Date derived from Project Settings."), indicator: "blue" });
                } else {
                    frappe.msgprint(__("Could not calculate End Date. Please check Project Settings."));
                }
            }
        });
    }

    _process_table_sync() {
        const doc = this.frm.doc;
        if (!doc.freq_start_date || !doc.freq_end_date) return;

        if (frappe.datetime.str_to_obj(doc.freq_end_date) < frappe.datetime.str_to_obj(doc.freq_start_date)) {
            frappe.msgprint(__("End Date cannot be before Start Date."));
            this._revert_dates();
            return;
        }

        if (doc.freq_start_date !== this.frm.__old_start_date || doc.freq_end_date !== this.frm.__old_end_date) {
            if (!doc.freq_days || doc.freq_days.length === 0) {
                this.build_table_via_server();
                this.frm.__old_start_date = doc.freq_start_date;
                this.frm.__old_end_date = doc.freq_end_date;
            } else {
                frappe.confirm(
                    __("The date range has changed. This will update rows but preserve your existing data. New rows will use default counts. Proceed?"),
                    () => {
                        this.build_table_via_server();
                        this.frm.__old_start_date = doc.freq_start_date;
                        this.frm.__old_end_date = doc.freq_end_date;
                    },
                    () => {
                        this._revert_dates();
                    }
                );
            }
        }
    }

    build_table_via_server() {
        frappe.call({
            doc: this.frm.doc,
            method: 'sync_table_with_dates',
            callback: (r) => {
                if (!r.exc) {
                    this.frm.refresh_field("freq_days");
                    this.frm.dirty();
                }
            }
        });
    }

    _revert_dates() {
        this.frm.set_value('freq_start_date', this.frm.__old_start_date || "");
        this.frm.set_value('freq_end_date', this.frm.__old_end_date || "");
        frappe.show_alert({ message: __("Date change discarded."), indicator: "orange" });
    }
}