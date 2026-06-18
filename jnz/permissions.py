# jnz/jnz/permissions.py

import frappe

def has_full_access(user):
    """
    بررسی می‌کند که آیا کاربر ادمین یا مدیرعامل است تا تمام دیتاها را ببیند
    """
    if user == "Administrator":
        return True
    
    # لیست نقش‌های این کاربر را می‌گیریم
    user_roles = frappe.get_roles(user)
    if "JNZ_ROLE_CEO" in user_roles:
        return True
        
    return False

def get_allowed_projects(user):
    """
    برمی‌گرداند کاربر در چه پروژه‌هایی عضو است.
    """
    return frappe.db.sql_list("""
        SELECT parent
        FROM `tabJNZ Project Members CT`
        WHERE member = %s
    """, user)

def get_project_query_conditions(user):
    """
    فیلتر لیست پروژه‌ها
    """
    if has_full_access(user):
        return "" # استثنا برای ادمین و مدیرعامل
    
    allowed_projects = get_allowed_projects(user)
    if not allowed_projects:
        return "1=0"
    
    formatted_projects = "'" + "', '".join(allowed_projects) + "'"
    return f"`tabJNZ Project`.name IN ({formatted_projects})"

def get_ration_request_query_conditions(user):
    """
    فیلتر لیست درخواست‌های جیره
    """
    if has_full_access(user):
        return ""
    
    allowed_projects = get_allowed_projects(user)
    if not allowed_projects:
        return "1=0"
    
    formatted_projects = "'" + "', '".join(allowed_projects) + "'"
    return f"`tabJNZ Ration Request`.rreq_project IN ({formatted_projects})"

def get_food_request_query_conditions(user):
    """
    فیلتر لیست درخواست‌های غذا
    """
    if has_full_access(user):
        return ""
    
    allowed_projects = get_allowed_projects(user)
    if not allowed_projects:
        return "1=0"
    
    formatted_projects = "'" + "', '".join(allowed_projects) + "'"
    return f"`tabJNZ Food Request`.freq_project IN ({formatted_projects})"