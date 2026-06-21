from frappe import _

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


# jnz/jnz/permissions.py

from frappe import _
import frappe

# ... (توابع قبلی مثل has_full_access و فیلترهای لیست سر جای خودشان بمانند) ...

def check_project_workflow_permission(doc, method=None):
    """
    جلوگیری از تغییر وضعیت ورک‌فلو اگر کاربر در آن پروژه نقش مربوطه را نداشته باشد
    """
    user = frappe.session.user
    
    # ۱. استثنا برای ادمین و مدیرعامل
    if has_full_access(user):
        return

    # ۲. اگر سند جدید است (Draft) اجازه ساخت می‌دهیم
    if doc.is_new():
        return

    # ۳. دریافت وضعیت قبلی از دیتابیس
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return

    old_state = old_doc.workflow_state
    new_state = doc.workflow_state

    # اگر وضعیت ورک‌فلو تغییری نکرده، یعنی کاربر فقط دارد فیلدها را ویرایش می‌کند، پس کاری نداریم
    if old_state == new_state:
        return

    # ۴. پیدا کردن نام پروژه مرتبط با این سند
    project_name = doc.get("rreq_project") or doc.get("freq_project")
    if not project_name:
        return

    # ۵. پیدا کردن نام ورک‌فلوی فعال برای این داک‌تایپ
    workflow_name = frappe.db.get_value("Workflow", {"document_type": doc.doctype, "is_active": 1}, "name")
    if not workflow_name:
        return
    
    active_workflow = frappe.get_doc("Workflow", workflow_name)

    # ۶. پیدا کردن نقش‌های مجاز برای این تغییر وضعیت
    allowed_roles = []
    action_name = ""
    for t in active_workflow.transitions:
        # اگر در جدول ترانزیشن‌ها، استیت قبلی و بعدی مچ شد، نقش مجاز را برمی‌داریم
        if t.state == old_state and t.next_state == new_state:
            allowed_roles.append(t.allowed)
            action_name = t.action

    # اگر نقشی پیدا نشد (حالت نامعتبر)، خود فرپه ارور می‌دهد
    if not allowed_roles:
        return

    # اگر در تنظیمات ورک‌فلوت نوشتی All (مثل مرحله Draft به Pending)، اجازه عبور می‌دهیم
    if "All" in allowed_roles:
        return

    # ۷. بررسی اینکه آیا کاربر در این پروژه خاص، یکی از نقش‌های مجاز را دارد؟
    user_roles_in_project = frappe.db.sql_list("""
        SELECT role 
        FROM `tabJNZ Project Members CT` 
        WHERE parent = %s AND member = %s
    """, (project_name, user))

    # اگر نقش کاربر با نقش‌های مجاز در این تغییر وضعیت همخوانی نداشت، سیستم را قفل می‌کنیم
    has_valid_role = any(role in allowed_roles for role in user_roles_in_project)
    
    if not has_valid_role:
        action_display = action_name or f"{old_state} -> {new_state}"
        frappe.throw(
            _("You do not have the required role to perform the action {0} in project {1}!").format(
                frappe.bold(_(action_display)), frappe.bold(project_name)
            )
        )
        



@frappe.whitelist()
def get_unauthorized_workflow_actions(doctype, project_name, current_state):
    """
    این تابع توسط جاوااسکریپت صدا زده می‌شود تا لیست اکشن‌هایی 
    که کاربر حق دیدن آن‌ها را ندارد برگرداند.
    """
    user = frappe.session.user
    
    # اگر کاربر دسترسی کامل دارد، هیچ دکمه‌ای مخفی نمی‌شود (لیست خالی برمی‌گردد)
    if has_full_access(user):
        return []
        
    if not project_name or not current_state:
        return []
        
    workflow_name = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "name")
    if not workflow_name:
        return []
        
    active_workflow = frappe.get_doc("Workflow", workflow_name)
    
    # نقش‌های این کاربر در این پروژه خاص را می‌گیریم
    user_roles_in_project = frappe.db.sql_list("""
        SELECT role FROM `tabJNZ Project Members CT` 
        WHERE parent = %s AND member = %s
    """, (project_name, user))
    
    unauthorized_actions = []
    
    # حلقه می‌زنیم روی ترانزیشن‌ها تا ببینیم کدام دکمه‌ها برای این استیت تعریف شده‌اند
    for t in active_workflow.transitions:
        if t.state == current_state:
            # اگر دکمه برای همه (All) باز باشد، مخفی نمی‌شود
            if t.allowed == "All":
                continue
            # اگر نقش مورد نیاز برای این دکمه در نقش‌های پروژه‌ای کاربر نبود، آن را به لیست مخفی‌ها اضافه می‌کنیم
            if t.allowed not in user_roles_in_project:
                unauthorized_actions.append(t.action)
                
    return unauthorized_actions