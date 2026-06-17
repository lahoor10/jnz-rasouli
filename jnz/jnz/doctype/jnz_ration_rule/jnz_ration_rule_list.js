// JNZ Ration Rule — List View  (§12)
frappe.listview_settings["JNZ Ration Rule"] = {
    add_fields: ["active", "rrul_calc_type", "rrul_period"],
    filters: [["active", "=", 1]],
    get_indicator(doc) {
        if (!doc.active) return [__("Inactive"), "grey", "active,=,0"];
        if (doc.rrul_period && doc.rrul_period !== "per_request") {
            return [__("Periodic"), "blue", "rrul_period,!=,"];
        }
        return [__("Per Request"), "green", "active,=,1"];
    },
};
