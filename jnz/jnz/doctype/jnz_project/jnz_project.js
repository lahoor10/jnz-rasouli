// Copyright (c) 2026, Arian and contributors
// For license information, please see license.txt

// frappe.ui.form.on("JNZ Project", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('JNZ Project', {
    refresh: function(frm) {
        // اعمال فیلتر روی فیلد نقش در جدول فرزند
        frm.set_query('role', 'members', function() {
            return {
                filters: [
                    ['Role', 'name', 'like', 'JNZ_%'],
                    ['Role', 'disabled', '=', 0]
                ]
            };
        });
    }
});
