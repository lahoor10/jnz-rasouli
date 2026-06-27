# -*- coding: utf-8 -*-
from enum import Enum

class RequestState(str, Enum):
    DRAFT = "Draft"
    PENDING_PROJ_TECH = "Pending Project Tech Approval"
    PENDING_SITE_SUPERVISOR = "Pending Site Supervisor Approval"
    PENDING_DEPT_MGR = "Pending Dept Manager Approval"
    PENDING_HQ_TECH = "Pending HQ Tech Approval"
    APPROVED = "Approved for Procurement"
    REJECTED = "Rejected"
