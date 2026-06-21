// JNZ Food Request — List View  (§12)
frappe.listview_settings["JNZ Food Request"] = {
    add_fields: ["docstatus", "freq_start_date", "freq_end_date"],
    get_indicator(doc) {
        if (doc.docstatus === 2) return [__("Rejected"), "red",    "docstatus,=,2"];
        if (doc.docstatus === 1) return [__("Approved"), "green",  "docstatus,=,1"];
        return [__("Draft"), "orange", "docstatus,=,0"];
    },
};
