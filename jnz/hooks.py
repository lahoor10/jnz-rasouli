from . import __version__ as app_version

app_name = "jnz"
app_title = "JNZ"
app_publisher = "Arian"
app_description = "Ration and Food Management System"
app_email = "info@arian.local"
app_license = "MIT"

# ---------------------------------------------------------------------------
# Module Def — must run after install AND after every migrate  (§3)
# Guarantees Module Def records keep app_name = "jnz" so DocTypes in the JNZ
# module are never treated as orphaned and deleted on bench migrate.
# ---------------------------------------------------------------------------
after_install = [
	"jnz.module_def_setup.ensure_module_defs",
	"jnz.module_def_setup.ensure_roles",
	"jnz.module_def_setup.ensure_number_cards",
	"jnz.module_def_setup.ensure_dashboard_charts",
	"jnz.module_def_setup.ensure_jnz_workspace",
]
after_migrate = [
	"jnz.module_def_setup.ensure_module_defs",
	"jnz.module_def_setup.ensure_roles",
	"jnz.module_def_setup.ensure_number_cards",
	"jnz.module_def_setup.ensure_dashboard_charts",
	"jnz.module_def_setup.ensure_jnz_workspace",
#	"jnz.scripts.create_workflow.run",
]

# ---------------------------------------------------------------------------
# Fixtures — Desktop Icon is a git-tracked fixture  (§16.2).
# The JNZ Workspace is upserted in ensure_jnz_workspace() (after_migrate)
# instead of via fixtures, which import Workspace records unreliably.
# ---------------------------------------------------------------------------
fixtures = [
	{"doctype": "Desktop Icon", "filters": [["label", "=", "JNZ"]]},
#	{"doctype": ""},
]

# ---------------------------------------------------------------------------
# Translations — Frappe auto-discovers the translations/ folder  (§9).
# File: jnz/translations/fa.csv
# ---------------------------------------------------------------------------

scheduler_events = {
    "daily": [
        "jnz.tasks.food_request_reminders.check_missing_food_requests"
    ]
}

permission_query_conditions = {
    "JNZ Project": "jnz.permissions.get_project_query_conditions",
    "JNZ Ration Request": "jnz.permissions.get_ration_request_query_conditions",
    "JNZ Food Request": "jnz.permissions.get_food_request_query_conditions",
}


doc_events = {
    "JNZ Ration Request": {
        "validate": "jnz.permissions.check_project_workflow_permission"
    },
    "JNZ Food Request": {
        "validate": "jnz.permissions.check_project_workflow_permission"
    }
}