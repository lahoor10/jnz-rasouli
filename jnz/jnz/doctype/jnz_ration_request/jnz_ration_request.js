// JNZ Ration Request — Form JS
// §8.1 OOP class-based  |  §8.3 field clearing  |  §8.4 cascade-safe set_value
// §4.5 depends_on preferred for static behaviour

const DOCTYPE = "JNZ Ration Request";

frappe.ui.form.on(DOCTYPE, {
    refresh(frm) {
        new JNZRationRequestFormController(frm).init();
        frm.trigger('toggle_approver_fields');
        
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
                        // این لاگ رو گذاشتم تا توی کنسول مرورگر (F12) ببینی آیا بک‌اند لیست رو درست می‌فرسته یا نه
                        console.log("Unauthorized Actions:", r.message); 

                        if (r.message && r.message.length > 0) {
                            let attempts = 0;
                            
                            // مکانیزم سرکوب مداوم: هر 200 میلی‌ثانیه چک می‌کند (تا 10 بار)
                            let hide_interval = setInterval(() => {
                                r.message.forEach(action => {
                                    let translated_action = __(action);

                                    // مخفی کردن دکمه اصلی (آبی رنگ)
                                    $(`[data-label="${action}"]`).hide();
                                    $(`[data-label="${translated_action}"]`).hide();

                                    // مخفی کردن کل ردیف (li) اگر دکمه داخل منوی کشویی Actions باشد
                                    $(`[data-label="${action}"]`).closest('li').hide();
                                    $(`[data-label="${translated_action}"]`).closest('li').hide();
                                });

                                attempts++;
                                if (attempts > 10) {
                                    clearInterval(hide_interval); // بعد از 2 ثانیه عملیات متوقف می‌شود تا رم مرورگر اشغال نشود
                                }
                            }, 200);
                        }
                    }
                });
            }
        }
    },

    workflow_state(frm) {
        frm.trigger('toggle_approver_fields');
    },

    rreq_project(frm) {
        new JNZRationRequestFieldHandler(frm).on_project_change();
        frm.trigger('toggle_approver_fields');
    },

    rreq_has_meeting(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },

    rreq_has_lunch(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },

    draft_resident_workers_count(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },
    draft_non_resident_workers_count(frm) {
        new JNZRationRequestFieldHandler(frm).on_flag_change();
    },

    toggle_approver_fields(frm) {
        // ۱. قفل کردن تمام فیلدهای تأییدکنندگان به‌صورت پیش‌فرض
        const approver_prefixes = [
            'support_supervisor', 'commercial_manager',
            'ceo_office', 'security', 'finance', 'ceo'
        ];

        approver_prefixes.forEach(prefix => {
            frm.set_df_property(prefix + '_resident_count', 'read_only', 1);
            frm.set_df_property(prefix + '_non_resident_count', 'read_only', 1);
        });

        if (!frm.doc.rreq_project || !frm.doc.workflow_state) return;

        // ۲. دریافت نقش‌های این کاربر در این پروژه خاص
        frappe.call({
            method: 'jnz.jnz.doctype.jnz_ration_request.jnz_ration_request.get_user_project_roles',
            args: {
                project: frm.doc.rreq_project,
                user: frappe.session.user
            },
            callback: function(r) {
                let user_roles_in_project = r.message || [];
                let is_system_manager = frappe.user_roles.includes("System Manager");

                // ۳. مپ کردن دقیق Stateهای ورک‌فلو به نقش‌ها
                const state_role_map = {
                    "Pending Support Approval": { role: "JNZ_ROLE_Support_Supervisor", prefix: "support_supervisor" },
                    "Pending Commercial Approval": { role: "JNZ_ROLE_Commercial_Manager", prefix: "commercial_manager" },
                    "Pending CEO Office Approval": { role: "JNZ_ROLE__CEO_Office", prefix: "ceo_office" },
                    "Pending Security Approval": { role: "JNZ_ROLE__Security_Department", prefix: "security" },
                    "Pending Finance Approval": { role: "JNZ_ROLE_Finance_Manager", prefix: "finance" },
                    "Pending CEO Approval": { role: "JNZ_ROLE_CEO", prefix: "ceo" }
                };

                let current_state_config = state_role_map[frm.doc.workflow_state];

                // ۴. باز کردن فیلد در صورت تطابق نقش
                if (current_state_config) {
                    if (user_roles_in_project.includes(current_state_config.role) || is_system_manager) {
                        frm.set_df_property(current_state_config.prefix + '_resident_count', 'read_only', 0);
                        frm.set_df_property(current_state_config.prefix + '_non_resident_count', 'read_only', 0);
                    }
                }
            }
        });
    }
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
        
        // تغییر تسک ۹ و ۱۰: قفل و باز کردن ستون‌های جدول بر اساس نقش کاربر در پروژه
        if (this.frm.doc.rreq_project) {
            frappe.call({
                method: 'jnz.jnz.doctype.jnz_ration_request.jnz_ration_request.get_user_project_roles',
                args: {
                    project: this.frm.doc.rreq_project,
                    user: frappe.session.user
                },
                callback: (r) => {
                    let user_roles = r.message || [];
                    let is_system_manager = frappe.user_roles.includes("System Manager");
                    
                    let is_ration_officer = user_roles.includes("JNZ_ROLE_Ration_Officer") || is_system_manager;
                    let is_delivery_officer = user_roles.includes("JNZ_ROLE_Delivery_Officer") || is_system_manager;

                    grid.update_docfield_property("rri_allocated_quantity", "read_only", is_ration_officer ? 0 : 1);
                    grid.update_docfield_property("rri_delivered_quantity", "read_only", is_delivery_officer ? 0 : 1);
                    grid.reset_grid();
                }
            });
        } else {
            grid.update_docfield_property("rri_allocated_quantity", "read_only", 1);
            grid.update_docfield_property("rri_delivered_quantity", "read_only", 1);
            grid.reset_grid();
        }
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

// تغییر تسک ۹ و ۱۰: هوک رندر گرید برای اطمینان از اعمال قفل ستون‌ها در طول فرم لایو
frappe.ui.form.on('JNZ Ration Request Item CT', {
    rreq_items_on_form_rendered(doc, cdt, cdn) {
        cur_frm.trigger('manage_grid_columns_permissions');
    }
});