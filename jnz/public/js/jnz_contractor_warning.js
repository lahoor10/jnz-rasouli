frappe.ui.form.on("JNZ Contractor Warning", {

    refresh(frm) {
        update_secretariat_fields(frm);
    },

    workflow_state(frm) {
        update_secretariat_fields(frm);
    }

});


function update_secretariat_fields(frm) {

    const is_secretariat =
        frappe.user.has_role("JNZ_ROLE_Secretariat");
    const is_admin = frappe.user.has_role("System Manager");
    // پیش فرض
    frm.set_df_property(
        "postal_tracking_number",
        "read_only",
        1
    );

    frm.set_df_property(
        "automation_letter_number",
        "read_only",
        1
    );

    // دبیرخانه + ارسال رسمی
    if (
        (is_secretariat || is_admin) &&
        frm.doc.workflow_state === "Pending Official Dispatch"
    ) {

        frm.set_df_property(
            "postal_tracking_number",
            "read_only",
            0
        );

    }

    // دبیرخانه + ارسال داخلی
    if (
        is_secretariat &&
        frm.doc.workflow_state === "Pending Internal Dispatch"
    ) {

        frm.set_df_property(
            "automation_letter_number",
            "read_only",
            0
        );

    }

}