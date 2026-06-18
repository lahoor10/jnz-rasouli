# Copyright (c) 2026, Arian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class JNZProject(Document):
    
    def validate(self):
        """
        اجرای ولیدیشن‌ها قبل از ذخیره پروژه
        """
        self.validate_members()

    def on_update(self):
        """
        تخصیص و مدیریت نقش‌ها بعد از ذخیره پروژه
        """
        self.sync_roles()

    def on_trash(self):
        """
        پس گرفتن نقش‌ها هنگام حذف کامل پروژه
        """
        for row in self.get("members", []):
            self.remove_role_if_not_needed(row.member, row.role)

    # ==========================================
    # Logic & Validation Methods
    # ==========================================

    def validate_members(self):
        """
        بررسی اعتبارسنجی‌های مربوط به جدول اعضا
        """
        seen_pairs = set()
        
        for row in self.get("members", []):
            # 1. جلوگیری از ردیف‌های تکراری
            key = (row.member, row.role)
            if key in seen_pairs:
                frappe.throw(_("Row {0}: Member {1} with Role {2} is duplicated.").format(
                    row.idx, frappe.bold(row.member), frappe.bold(row.role)
                ))
            seen_pairs.add(key)

            # 2. جلوگیری از تخصیص نقش‌های سیستمی (فقط نقش‌های JNZ_ مجاز هستند)
            if not row.role.startswith("JNZ_"):
                frappe.throw(_("Row {0}: Role {1} is a system role. Only custom project roles (starting with JNZ_) can be assigned.").format(
                    row.idx, frappe.bold(row.role)
                ))

            # 3. بررسی نوع کاربر و فعال بودن اکانت
            user_info = frappe.db.get_value("User", row.member, ["user_type", "enabled"], as_dict=True)
            
            if not user_info:
                frappe.throw(_("Row {0}: User {1} not found.").format(row.idx, frappe.bold(row.member)))

            # if user_info.user_type != "System User":
            #     frappe.throw(_("Row {0}: User {1} is a {2}, not a System User. Cannot assign roles.").format(
            #         row.idx, frappe.bold(row.member), user_info.user_type
            #     ))

            if not user_info.enabled:
                frappe.throw(_("Row {0}: User {1} is disabled.").format(row.idx, frappe.bold(row.member)))

    def sync_roles(self):
        """
        همگام‌سازی نقش‌ها (اضافه کردن نقش‌های جدید و حذف نقش‌های قدیمی)
        """
        roles_to_add = set()
        roles_to_check_for_removal = set()

        old_doc = self.get_doc_before_save()
        old_pairs = set((row.member, row.role) for row in old_doc.get("members", [])) if old_doc else set()
        current_pairs = set((row.member, row.role) for row in self.get("members", []))

        # 4. مدیریت وضعیت پروژه (اگر پروژه غیرفعال شده است، باید نقش‌ها پس گرفته شود)
        if not self.active:
            # تمام افراد فعلی و قدیمی باید چک شوند تا در صورت نیاز نقششان حذف شود
            roles_to_check_for_removal.update(current_pairs)
            roles_to_check_for_removal.update(old_pairs)
        else:
            # پروژه فعال است. باید تفاوت‌ها را محاسبه کنیم
            added_pairs = current_pairs - old_pairs
            removed_pairs = old_pairs - current_pairs

            # برای اضافه کردن، هم اعضای جدید و هم اعضای فعلی را در نظر می‌گیریم
            # (تا اگر مدیر نقشی را دستی از پروفایل کاربر حذف کرده بود، دوباره اصلاح شود)
            roles_to_add.update(current_pairs)
            
            # نقش‌های حذف شده باید بررسی شوند
            roles_to_check_for_removal.update(removed_pairs)

        # اجرای عملیات افزودن نقش
        for member, role in roles_to_add:
            self.add_role_to_user(member, role)

        # اجرای عملیات حذف نقش با رعایت شرایط پروژه‌های دیگر
        for member, role in roles_to_check_for_removal:
            self.remove_role_if_not_needed(member, role)

    def add_role_to_user(self, user_name, role_name):
        """
        اضافه کردن نقش به پروفایل کاربری در صورتی که آن را نداشته باشد.
        """
        if not frappe.db.exists("Has Role", {"parent": user_name, "role": role_name}):
            user = frappe.get_doc("User", user_name)
            user.append("roles", {"role": role_name})
            user.flags.ignore_permissions = True  # نیازی به سطح دسترسی ادمین برای ذخیره نیست
            user.save()

    def remove_role_if_not_needed(self, user_name, role_name):
        """
        حذف نقش از کاربر، به شرطی که در هیچ پروژه فعال دیگری این نقش را نداشته باشد.
        """
        # کوئری برای بررسی اینکه آیا کاربر این نقش را در پروژه فعال دیگری دارد یا خیر
        # نکته: نام جدول دیتابیس بر اساس Options چایلد تیبل شما تعیین می‌شود (JNZ Project Members CT)
        active_projects_with_role = frappe.db.sql("""
            SELECT parent
            FROM `tabJNZ Project Members CT`
            WHERE member = %s
              AND role = %s
              AND parent != %s
              AND parent IN (SELECT name FROM `tabJNZ Project` WHERE active = 1)
            LIMIT 1
        """, (user_name, role_name, self.name))

        if not active_projects_with_role:
            # کاربر در هیچ پروژه فعال دیگری این نقش را ندارد، پس نقش از پروفایل او حذف می‌شود
            if frappe.db.exists("Has Role", {"parent": user_name, "role": role_name}):
                user = frappe.get_doc("User", user_name)
                
                # فیلتر کردن ردیف‌ها و حذف نقش مورد نظر
                user.roles = [r for r in user.roles if r.role != role_name]
                user.flags.ignore_permissions = True
                user.save()
