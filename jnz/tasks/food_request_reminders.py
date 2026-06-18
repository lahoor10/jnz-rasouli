import frappe
from frappe.utils import add_days, getdate

def check_missing_food_requests():
    """متد اصلی که هر شب پروژه‌ها را برای بررسی عدم ثبت درخواست اسکن می‌کند"""
    # ۱. دریافت تمام کاربران با نقش‌های سرپرست کارگاه و مدیر پروژه
    recipients = get_recipients_by_roles(["JNZ_ROLE_Site_Supervisor", "JNZ_ROLE__Project_Manager"])
    if not recipients:
        return

    # ۲. اصلاح فیلتر بر اساس فیلد واقعی دیتابیس شما (active=1)
    active_projects = frappe.get_all("JNZ Project", filters={"active": 1}, fields=["name"])

    # ۳. بررسی وضعیت برای ۱ روز بعد
    check_and_send_alerts(active_projects, days_left=1, recipients=recipients)

def check_and_send_alerts(active_projects, days_left, recipients):
    """بررسی تک‌تک پروژه‌ها؛ اگر درخواست سابمیت شده ندارند، ایمیل می‌زند"""
    target_date = add_days(getdate(), days_left)
    
    for project in active_projects:
        # چک می‌کنیم آیا برای این پروژه و این تاریخ، درخواستِ سابمیت شده وجود دارد؟
        has_submitted_request = frappe.db.exists("JNZ Food Request", {
            "freq_project": project.name,
            "freq_end_date": target_date,
            "docstatus": 1  # 1 یعنی حتماً سابمیت و نهایی شده است
        })
        
        # اگر هیچ درخواستِ سابمیت‌شده‌ای وجود نداشت
        if not has_submitted_request:
            # پیدا کردن لینک سند در صورتی که به صورت پیش‌نویس وجود داشته باشد
            draft_doc = frappe.db.get_value("JNZ Food Request", 
                {"freq_project": project.name, "freq_end_date": target_date, "docstatus": 0}, 
                "name"
            )
            
            send_reminder_email(project.name, draft_doc, days_left, recipients)

def get_recipients_by_roles(roles):
    """استخراج ایمیل کاربران بر اساس نقش‌ها"""
    user_emails = frappe.get_all("Has Role", filters={"role": ["in", roles]}, fields=["parent"])
    return list(set([user.parent for user in user_emails if user.parent]))

def send_reminder_email(project_name, doc_name, days_left, recipients):
    """ارسال ایمیل هوشمند فارسی"""
    site_url = frappe.utils.get_url()
    
    subject = f"هشدار {days_left} روز مانده: عدم ثبت نهایی آمار غذای پروژه {project_name}"
    
    button_url = f"{site_url}/app/jnz-food-request/{doc_name}" if doc_name else f"{site_url}/app/jnz-food-request"
    status_text = "هنوز هیچ درخواستی برای این تاریخ ایجاد نشده است" if not doc_name else "درخواستی ایجاد شده اما هنوز پیش‌نویس است و ثبت نهایی (Submit) نشده است"

    message = f"""
    <div dir="rtl" style="font-family: Tahoma, Arial, sans-serif; text-align: right; line-height: 1.8;">
        <p>کاربر گرامی،</p>
        <p>تنها <b>{days_left} روز</b> تا پایان دوره زمانی درخواست غذا برای پروژه <b>{project_name}</b> باقی مانده است.</p>
        <p style="color: #d35400; font-weight: bold;">وضعیت: {status_text}.</p>
        <p>لطفاً در اسرع وقت اقدام به ورود آمار و <b>ثبت نهایی (Submit)</b> درخواست نمایید تا فرآیند تدارکات دچار اختلال نشود.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p><a href="{button_url}" style="background-color: #c0392b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">ورود به سامانه و اقدام</a></p>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True
    )