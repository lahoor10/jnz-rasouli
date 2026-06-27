# -*- coding: utf-8 -*-
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
