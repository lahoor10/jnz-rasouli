// JNZ Ration Request — List View  (§12)
frappe.listview_settings["JNZ Ration Request"] = {
    add_fields: ["docstatus", "rreq_has_meeting", "rreq_has_lunch"],
    get_indicator(doc) {
        if (doc.docstatus === 2) return [__("Rejected"), "red",    "docstatus,=,2"];
        if (doc.docstatus === 1) return [__("Approved"), "green",  "docstatus,=,1"];
        return [__("Draft"), "orange", "docstatus,=,0"];
    },
};

