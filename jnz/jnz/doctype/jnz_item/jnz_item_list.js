// JNZ Item — List View  (§12)
frappe.listview_settings["JNZ Item"] = {
    add_fields: ["active", "itm_default_unit"],
    filters: [["active", "=", 1]],
    get_indicator(doc) {
        if (doc.active) return [__("Active"), "green", "active,=,1"];
        return [__("Inactive"), "grey", "active,=,0"];
    },
};
