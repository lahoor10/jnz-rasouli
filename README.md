# JNZ DocTypes — Rebuild (Standards-Compliant)

Generated against **frappe-dev-standards.md**. Every deviation from the first
output is documented below.

---

## What Changed vs First Output

| Rule (§) | Old behaviour | Fixed behaviour |
|---|---|---|
| §2.2 Autoname | `By fieldname` with manual IDs | `Expression` with prefixes (`PROJ-.#####`, `RRUL-.#####`, etc.) |
| §9 Source language | Farsi in labels, options, descriptions | **English only** in source; all Farsi in `translations/fa.csv` |
| §4.1 Master properties | Missing `show_title_field_in_link` | Added on every master |
| §4.2 Master fields | No `active`, `description`, `user_define_code` | Added to all masters |
| §5 Child Table properties | Missing `grid_page_length`, `index_web_pages_for_search`, `rows_threshold_for_grid_search` | Added — omitting any one causes Frappe 16 to delete the CT on migrate |
| §5.6 Display-only CT | `items` CT had no `cannot_add_rows/delete_rows` | Set on both `JNZ Ration Request Item CT` and `JNZ Food Request Day CT` |
| §7.1 Class naming | N/A | `JNZRationRequest`, `JNZFoodRequest` — acronym `JNZ` uppercase throughout |
| §7.2 API constants | Inline strings | `DOCTYPE_*`, `CALC_*`, `PERIOD_*` constants at top of each file |
| §7.3 Validation | Would throw inside loops | Collect-then-throw pattern |
| §8 JS | No JS | Class-based `FormController` + `FieldHandler` / `DateHandler` per form |
| §8.4 async set_value | N/A | `Object.assign(frm.doc, …)` + `frm.dirty()` + `frm.refresh_fields()` |
| §11 Section break labels | "Items" section had label duplicating table label | `"label": ""` on all such section breaks |
| §12 List views | None | `listview_settings.js` with colour indicators for all DocTypes |
| §3 Module Def | None | `module_def_setup.py` with `after_install` + `after_migrate` hooks |

---

## File Structure

```
jnz_doctypes/
│
├── doctypes/                          ← JSON fixtures (import in order below)
│   ├── JNZ_Condition.json
│   ├── JNZ_Item.json
│   ├── JNZ_Project.json
│   ├── JNZ_Project_Settings.json
│   ├── JNZ_Ration_Rule_Condition_CT.json   ← CT before parent
│   ├── JNZ_Ration_Rule.json
│   ├── JNZ_Ration_Request_Item_CT.json     ← CT before parent
│   ├── JNZ_Ration_Request.json
│   ├── JNZ_Food_Request_Day_CT.json        ← CT before parent
│   └── JNZ_Food_Request.json
│
├── controllers/
│   ├── jnz_ration_request.py          → class JNZRationRequest(Document)
│   └── jnz_food_request.py            → class JNZFoodRequest(Document)
│
├── js/
│   ├── jnz_ration_request.js          → JNZRationRequestController + JNZRationRequestFieldHandler
│   ├── jnz_food_request.js            → JNZFoodRequestController + JNZFoodRequestDateHandler
│   └── listview_settings.js           → colour indicators for all DocTypes
│
├── translations/
│   └── fa.csv                         → ALL Farsi translations (English source → فارسی)
│
└── module_def_setup.py                → ensures Module Def records survive bench migrate
```

---

## DocType Autoname Prefixes

| DocType | Prefix | Example |
|---|---|---|
| JNZ Project | `PROJ-.#####` | `PROJ-00001` |
| JNZ Project Settings | `PROJSET-.#####` | `PROJSET-00001` |
| JNZ Item | `ITM-.#####` | `ITM-00001` |
| JNZ Condition | `COND-.#####` | `COND-00001` |
| JNZ Ration Rule | `RRUL-.#####` | `RRUL-00001` |
| JNZ Ration Rule Condition CT | `RRC-.#####` | `RRC-00001` |
| JNZ Ration Request | `RREQ-.#####` | `RREQ-00001` |
| JNZ Ration Request Item CT | `RRI-.#####` | `RRI-00001` |
| JNZ Food Request | `FREQ-.#####` | `FREQ-00001` |
| JNZ Food Request Day CT | `FRD-.#####` | `FRD-00001` |

---

## File Placement in Your App

```
jnz/
└── jnz/
    ├── module_def_setup.py
    ├── hooks.py  ← add after_install / after_migrate entries
    ├── public/js/
    │   └── listview_settings.js   (register in hooks.py → app_include_js)
    └── doctype/
        ├── jnz_project/
        │   └── jnz_project.json
        ├── jnz_item/
        │   └── jnz_item.json
        ├── jnz_condition/
        │   └── jnz_condition.json
        ├── jnz_ration_rule/
        │   └── jnz_ration_rule.json
        ├── jnz_ration_rule_condition_ct/
        │   └── jnz_ration_rule_condition_ct.json
        ├── jnz_ration_request/
        │   ├── jnz_ration_request.json
        │   ├── jnz_ration_request.py
        │   └── jnz_ration_request.js
        ├── jnz_ration_request_item_ct/
        │   └── jnz_ration_request_item_ct.json
        ├── jnz_food_request/
        │   ├── jnz_food_request.json
        │   ├── jnz_food_request.py
        │   └── jnz_food_request.js
        └── jnz_food_request_day_ct/
            └── jnz_food_request_day_ct.json
```

### hooks.py additions

```python
after_install = "jnz.module_def_setup.ensure_module_defs"
after_migrate  = "jnz.module_def_setup.ensure_module_defs"

app_include_js = ["jnz/public/js/listview_settings.js"]
```

---

## Migration Order

```bash
bash patch.sh   # if applicable
bench --site <site> execute jnz.module_def_setup.ensure_module_defs
bench --site <site> migrate
bench build --app jnz
bench restart
```

---

## Roles Required in Frappe Role Master

```
JNZ_ROLE_Site_Supervisor
JNZ_ROLE__Project_Manager
JNZ_ROLE__Security_Department
JNZ_ROLE__HR
JNZ_ROLE__CEO_Office
JNZ_ROLE_CEO
```

---

## Ration Calculation Logic

| calc_type | Formula |
|---|---|
| `per_person` | `amount × workers_count` |
| `per_room` | `amount × project.rooms_count` |
| `per_project` | `amount` (flat) |
| `per_meeting` | `amount` only when `has_meeting = 1` |

**Condition gates** (`_conditions_met`):
- Condition type `meeting` → requires `has_meeting = 1`
- Condition type `lunch` → requires `has_lunch = 1`
- Multiple conditions → ALL must pass (AND logic)
- Condition types for management approval / special request / event → not auto-blocked

**Period eligibility** (`_period_eligible`):
- Queries previous submitted/draft Ration Requests for the same project + item
- `per_month` → threshold = last request date + 1 month
- `per_two_month` → threshold = last request date + 2 months
- No previous request → always eligible
- If ineligible → item **excluded entirely** (not shown as 0)

## Food Request Day Auto-Generation

1. If `end_date` is empty and `Project Settings.auto_generate_end_date = 1`:
   `end_date = start_date + (request_period_days − 1)`
2. One child row per calendar day in `[start_date, end_date]`
3. `day_date` is `read_only` — user only edits breakfast/lunch/dinner counts
4. Re-saving **preserves** existing counts for previously entered dates
