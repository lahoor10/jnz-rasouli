import os
import json

def execute():
    BASE_DIR = "/home/fara-kasb/frappe-jnz/apps/jnz/jnz"
    
    # 1. Create Directories
    directories = [
        f"{BASE_DIR}/services/civil_services",
        f"{BASE_DIR}/doctype/jnz_civil_service_request",
        f"{BASE_DIR}/workflow/jnz_civil_service_request_workflow"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Domain Package\n")

    # Clear old broken fixture file if it exists to stop old error
    old_fixture = f"{BASE_DIR}/fixtures/workflow.json"
    if os.path.exists(old_fixture):
        os.remove(old_fixture)

    # 2. States Enum
    states_content = """# -*- coding: utf-8 -*-
from enum import Enum

class RequestState(str, Enum):
    DRAFT = "Draft"
    PENDING_PROJ_TECH = "Pending Project Tech Approval"
    PENDING_SITE_SUPERVISOR = "Pending Site Supervisor Approval"
    PENDING_DEPT_MGR = "Pending Dept Manager Approval"
    PENDING_HQ_TECH = "Pending HQ Tech Approval"
    APPROVED = "Approved for Procurement"
    REJECTED = "Rejected"
"""
    with open(f"{BASE_DIR}/services/civil_services/states.py", "w") as f: f.write(states_content)

    # 3. Service Layer
    service_content = """# -*- coding: utf-8 -*-
import frappe
from jnz.services.civil_services.states import RequestState

class RequestValidationService:
    @staticmethod
    def validate_anti_tamper(doc):
        if not doc.is_new():
            old_doc = doc.get_doc_before_save()
            if old_doc and old_doc.workflow_state != doc.workflow_state:
                if not frappe.flags.in_workflow_transition:
                    frappe.throw("Direct modification of workflow_state is forbidden.")

    @staticmethod
    def execute_pessimistic_lock(doc):
        if doc.is_new(): return
        frappe.db.sql("SELECT name FROM `tabJNZ Civil Service Request` WHERE name=%s FOR UPDATE", doc.name)
        current_state = frappe.db.get_value("JNZ Civil Service Request", doc.name, "workflow_state")
        if current_state != doc.workflow_state:
            frappe.throw("Concurrency conflict detected. Refresh document.")

    @staticmethod
    def handle_approved_event(doc):
        if doc.workflow_state == RequestState.APPROVED:
            frappe.logger("jnz").info(f"Request {doc.name} APPROVED. Triggering Inquiry DocType...")
"""
    with open(f"{BASE_DIR}/services/civil_services/request_validation_service.py", "w") as f: f.write(service_content)

    # 4. Controller Layer
    controller_content = """# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document
from jnz.services.civil_services.request_validation_service import RequestValidationService

class JNZCivilServiceRequest(Document):
    def before_save(self):
        RequestValidationService.validate_anti_tamper(self)
        
    def before_workflow_action(self, action):
        RequestValidationService.execute_pessimistic_lock(self)

    def on_update(self):
        RequestValidationService.handle_approved_event(self)
"""
    with open(f"{BASE_DIR}/doctype/jnz_civil_service_request/jnz_civil_service_request.py", "w") as f: f.write(controller_content)

    # 5. DocType Schema
    doctype_schema = {
        "name": "JNZ Civil Service Request",
        "doctype": "DocType",
        "module": "Jnz",
        "autoname": "naming_series:",
        "naming_rule": "By \"Naming Series\"",
        "issubmittable": 0,
        "editable_grid": 1,
        "track_changes": 1,
        "fields": [
            {"fieldname": "naming_series", "fieldtype": "Select", "label": "Naming Series", "options": "JNZ-CSR-.YYYY.-"},
            {"fieldname": "title", "fieldtype": "Data", "label": "Service Request Title", "reqd": 1},
            {"fieldname": "project", "fieldtype": "Link", "label": "Target Project", "options": "Project", "reqd": 1},
            {"fieldname": "description", "fieldtype": "Text Editor", "label": "Scope of Civil Services", "reqd": 1},
            {"fieldname": "workflow_state", "fieldtype": "Link", "label": "Workflow Status", "options": "Workflow State", "read_only": 1},
            {"fieldname": "amended_from", "fieldtype": "Link", "label": "Amended From", "options": "JNZ Civil Service Request", "read_only": 1}
        ],
        "permissions": [
            {"role": "JNZ_ROLE_Executive_Expert", "read": 1, "write": 1, "create": 1},
            {"role": "JNZ_ROLE_Project_Technical_Office", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Site_Supervisor", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_Department_Manager", "read": 1, "write": 1},
            {"role": "JNZ_ROLE_HQ_Technical_Office", "read": 1, "write": 1}
        ]
    }
    with open(f"{BASE_DIR}/doctype/jnz_civil_service_request/jnz_civil_service_request.json", "w") as f: json.dump(doctype_schema, f, indent=4)

    # 6. UI Layer
    js_content = """frappe.ui.form.on('JNZ Civil Service Request', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.workflow_state !== "Draft") {
            frm.disable_form();
        }
    }
});"""
    with open(f"{BASE_DIR}/doctype/jnz_civil_service_request/jnz_civil_service_request.js", "w") as f: f.write(js_content)

    # 7. Native Module Workflow Document JSON Layout
    workflow_doc = {
        "name": "JNZ Civil Service Request Workflow",
        "doctype": "Workflow",
        "workflow_name": "JNZ Civil Service Request Workflow",
        "document_type": "JNZ Civil Service Request",
        "is_active": 1,
        "override_status": 1,
        "workflow_state_field": "workflow_state",
        "states": [
            {"state": "Draft", "doc_status": "0", "allow_edit": "JNZ_ROLE_Executive_Expert"},
            {"state": "Pending Project Tech Approval", "doc_status": "0", "allow_edit": "JNZ_ROLE_Project_Technical_Office"},
            {"state": "Pending Site Supervisor Approval", "doc_status": "0", "allow_edit": "JNZ_ROLE_Site_Supervisor"},
            {"state": "Pending Dept Manager Approval", "doc_status": "0", "allow_edit": "JNZ_ROLE_Department_Manager"},
            {"state": "Pending HQ Tech Approval", "doc_status": "0", "allow_edit": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Approved for Procurement", "doc_status": "0", "allow_edit": "System Manager"},
            {"state": "Rejected", "doc_status": "0", "allow_edit": "JNZ_ROLE_Executive_Expert"}
        ],
        "transitions": [
            {"state": "Draft", "action": "Submit", "next_state": "Pending Project Tech Approval", "allowed": "JNZ_ROLE_Executive_Expert"},
            {"state": "Pending Project Tech Approval", "action": "Approve", "next_state": "Pending Site Supervisor Approval", "allowed": "JNZ_ROLE_Project_Technical_Office"},
            {"state": "Pending Project Tech Approval", "action": "Reject", "next_state": "Rejected", "allowed": "JNZ_ROLE_Project_Technical_Office"},
            {"state": "Pending Site Supervisor Approval", "action": "Approve", "next_state": "Pending Dept Manager Approval", "allowed": "JNZ_ROLE_Site_Supervisor"},
            {"state": "Pending Site Supervisor Approval", "action": "Reject", "next_state": "Rejected", "allowed": "JNZ_ROLE_Site_Supervisor"},
            {"state": "Pending Dept Manager Approval", "action": "Approve", "next_state": "Pending HQ Tech Approval", "allowed": "JNZ_ROLE_Department_Manager"},
            {"state": "Pending Dept Manager Approval", "action": "Reject", "next_state": "Rejected", "allowed": "JNZ_ROLE_Department_Manager"},
            {"state": "Pending HQ Tech Approval", "action": "Approve", "next_state": "Approved for Procurement", "allowed": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Pending HQ Tech Approval", "action": "Reject", "next_state": "Rejected", "allowed": "JNZ_ROLE_HQ_Technical_Office"},
            {"state": "Rejected", "action": "Resubmit", "next_state": "Pending Project Tech Approval", "allowed": "JNZ_ROLE_Executive_Expert"}
        ]
    }
    with open(f"{BASE_DIR}/workflow/jnz_civil_service_request_workflow/jnz_civil_service_request_workflow.json", "w") as f: 
        json.dump(workflow_doc, f, indent=4)

    print("🏁 Fixed code tracking configurations generated successfully.")