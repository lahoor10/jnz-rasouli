import frappe

ITEMS = [
    {
        "itm_name": "Sugar Cubes",
        "user_define_code": "SUGAR_CUBES",
        "itm_default_unit": "gram",
        "description": "Sugar cubes"
    },
    {
        "itm_name": "Tea",
        "user_define_code": "TEA",
        "itm_default_unit": "gram",
        "description": "Dry tea"
    },
    {
        "itm_name": "Tissue Paper",
        "user_define_code": "TISSUE_PAPER",
        "itm_default_unit": "package",
        "description": "Approximately one package per room per month"
    },
    {
        "itm_name": "Dishwashing Gloves",
        "user_define_code": "DISHWASHING_GLOVES",
        "itm_default_unit": "pair",
        "description": "One pair every two months"
    },
    {
        "itm_name": "Bleach",
        "user_define_code": "BLEACH",
        "itm_default_unit": "liter",
        "description": "Bleach liquid"
    },
    {
        "itm_name": "Toilet Cleaner",
        "user_define_code": "TOILET_CLEANER",
        "itm_default_unit": "liter",
        "description": "Toilet cleaning liquid"
    },
    {
        "itm_name": "Dishwashing Liquid",
        "user_define_code": "DISHWASHING_LIQUID",
        "itm_default_unit": "gram",
        "description": "Dishwashing liquid"
    },
    {
        "itm_name": "Hand Wash Liquid",
        "user_define_code": "HAND_WASH_LIQUID",
        "itm_default_unit": "gram",
        "description": "Hand wash liquid"
    },
    {
        "itm_name": "Meeting Biscuits",
        "user_define_code": "MEETING_BISCUITS",
        "itm_default_unit": "package",
        "description": "Meeting hospitality biscuits"
    },
    {
        "itm_name": "Meeting Chocolate",
        "user_define_code": "MEETING_CHOCOLATE",
        "itm_default_unit": "package",
        "description": "Meeting hospitality chocolate"
    },
    {
        "itm_name": "Steel Scourer",
        "user_define_code": "STEEL_SCOURER",
        "itm_default_unit": "piece",
        "description": "Steel scourer"
    },
    {
        "itm_name": "Sponge Scourer",
        "user_define_code": "SPONGE_SCOURER",
        "itm_default_unit": "package",
        "description": "Sponge scourer"
    },
    {
        "itm_name": "Garbage Bag",
        "user_define_code": "GARBAGE_BAG",
        "itm_default_unit": "piece",
        "description": "Garbage bag"
    },
    {
        "itm_name": "Freezer Bag Roll",
        "user_define_code": "FREEZER_BAG_ROLL",
        "itm_default_unit": "package",
        "description": "Freezer bag roll"
    },
    {
        "itm_name": "Glass Cleaner",
        "user_define_code": "GLASS_CLEANER",
        "itm_default_unit": "piece",
        "description": "Glass cleaner"
    },
    {
        "itm_name": "Salt",
        "user_define_code": "SALT",
        "itm_default_unit": "package",
        "description": "Salt"
    },
    {
        "itm_name": "Disposable Table Cover Roll",
        "user_define_code": "DISPOSABLE_TABLE_COVER_ROLL",
        "itm_default_unit": "piece",
        "description": "Disposable table cover roll"
    },
    {
        "itm_name": "Matches",
        "user_define_code": "MATCHES",
        "itm_default_unit": "package",
        "description": "Matches"
    },
    {
        "itm_name": "Hand Washing Powder",
        "user_define_code": "HAND_WASHING_POWDER",
        "itm_default_unit": "piece",
        "description": "Hand washing powder"
    },
    {
        "itm_name": "Paper Cup",
        "user_define_code": "PAPER_CUP",
        "itm_default_unit": "piece",
        "description": "Paper cup"
    },
    {
        "itm_name": "Glass Cup",
        "user_define_code": "GLASS_CUP",
        "itm_default_unit": "piece",
        "description": "Glass cup"
    },
    {
        "itm_name": "Disposable Spoon",
        "user_define_code": "DISPOSABLE_SPOON",
        "itm_default_unit": "piece",
        "description": "Disposable spoon"
    },
]

for item in ITEMS:
    if frappe.db.exists("JNZ Item", {"itm_name": item["itm_name"]}):
        print(f"Skipped: {item['itm_name']}")
        continue

    doc = frappe.get_doc({
        "doctype": "JNZ Item",
        "active": 1,
        **item
    })

    doc.insert(ignore_permissions=True)
    print(f"Created: {item['itm_name']}")

frappe.db.commit()
print("Done")