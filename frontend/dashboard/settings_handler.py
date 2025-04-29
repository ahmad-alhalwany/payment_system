import os
import json
import requests
import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QFileDialog, QMessageBox
)
from ui.custom_widgets import ModernGroupBox, ModernButton

class SettingsHandlerMixin:
    """Mixin class handling system settings and maintenance functionality"""
    def setup_settings_tab(self):
        """Set up the settings tab."""
        layout = QVBoxLayout()
        
        # System settings
        settings_group = ModernGroupBox("إعدادات النظام", "#3498db")
        settings_layout = QFormLayout()
        
        self.system_name_input = QLineEdit("نظام التحويلات المالية الداخلي")
        settings_layout.addRow("اسم النظام:", self.system_name_input)
        
        self.company_name_input = QLineEdit("شركة التحويلات المالية")
        settings_layout.addRow("اسم الشركة:", self.company_name_input)
        
        self.admin_email_input = QLineEdit("admin@example.com")
        settings_layout.addRow("البريد الإلكتروني للمسؤول:", self.admin_email_input)
        
        self.currency_input = QComboBox()
        self.currency_input.addItems(["ليرة سورية", "دولار أمريكي", "يورو"])
        settings_layout.addRow("العملة الافتراضية:", self.currency_input)
        
        self.language_input = QComboBox()
        self.language_input.addItems(["العربية", "English"])
        settings_layout.addRow("اللغة:", self.language_input)
        
        self.theme_input = QComboBox()
        self.theme_input.addItems(["فاتح", "داكن", "أزرق"])
        settings_layout.addRow("السمة:", self.theme_input)
        
        save_settings_button = ModernButton("حفظ الإعدادات", color="#2ecc71")
        save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addRow("", save_settings_button)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # User settings
        user_settings_group = ModernGroupBox("إعدادات المستخدم", "#e74c3c")
        user_settings_layout = QFormLayout()
        
        self.username_input = QLineEdit("admin")
        self.username_input.setReadOnly(True)
        self.username_input.setStyleSheet("background-color: #f0f0f0;")
        user_settings_layout.addRow("اسم المستخدم:", self.username_input)
        
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        user_settings_layout.addRow("كلمة المرور الحالية:", self.old_password_input)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        user_settings_layout.addRow("كلمة المرور الجديدة:", self.new_password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        user_settings_layout.addRow("تأكيد كلمة المرور:", self.confirm_password_input)
        
        change_password_button = ModernButton("تغيير كلمة المرور", color="#f39c12")
        change_password_button.clicked.connect(self.change_password)
        user_settings_layout.addRow("", change_password_button)
        
        user_settings_group.setLayout(user_settings_layout)
        layout.addWidget(user_settings_group)
        
        # Backup and restore
        backup_group = ModernGroupBox("النسخ الاحتياطي واستعادة البيانات", "#9b59b6")
        backup_layout = QVBoxLayout()
        
        backup_button = ModernButton("إنشاء نسخة احتياطية", color="#3498db")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)
        
        restore_button = ModernButton("استعادة من نسخة احتياطية", color="#e74c3c")
        restore_button.clicked.connect(self.restore_backup)
        backup_layout.addWidget(restore_button)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        self.settings_tab.setLayout(layout)
    def save_settings(self):
        """Save system settings."""
        try:
            # Get settings values
            system_name = self.system_name_input.text()
            company_name = self.company_name_input.text()
            admin_email = self.admin_email_input.text()
            currency = self.currency_input.currentText()
            language = self.language_input.currentText()
            theme = self.theme_input.currentText()
            
            # Validate inputs
            if not system_name or not company_name or not admin_email:
                QMessageBox.warning(self, "تنبيه", "الرجاء ملء جميع الحقول المطلوبة")
                return
                
            # Create settings data
            settings_data = {
                "system_name": system_name,
                "company_name": company_name,
                "admin_email": admin_email,
                "default_currency": currency,
                "language": language,
                "theme": theme
            }
            
            # Save settings to file
            settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "settings.json")
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
                
            QMessageBox.information(self, "نجاح", "تم حفظ الإعدادات بنجاح")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر حفظ الإعدادات: {str(e)}")
    
    def change_password(self):
        """Change the user's password."""
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not old_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "تنبيه", "الرجاء ملء جميع حقول كلمة المرور")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "تنبيه", "كلمة المرور الجديدة وتأكيدها غير متطابقين")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            data = {
                "old_password": old_password,
                "new_password": new_password
            }
            response = requests.post(f"{self.api_url}/change-password/", json=data, headers=headers)
            
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تغيير كلمة المرور بنجاح")
                self.old_password_input.clear()
                self.new_password_input.clear()
                self.confirm_password_input.clear()
            else:
                error_msg = f"فشل تغيير كلمة المرور: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                QMessageBox.warning(self, "خطأ", error_msg)
        except Exception as e:
            print(f"Error changing password: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تغيير كلمة المرور: {str(e)}")
    
    def create_backup(self):
        """Create a backup of the database."""
        try:
            # Get backup directory from user
            backup_dir = QFileDialog.getExistingDirectory(
                self, "اختر مجلد النسخ الاحتياطي", ""
            )
            
            if not backup_dir:
                return  # User canceled
                
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"system_backup_{timestamp}.zip")
            
            # Request backup from server
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/backup/", headers=headers, stream=True)
            
            if response.status_code == 200:
                # Save backup file
                with open(backup_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة الاحتياطية بنجاح في:\n{backup_file}")
            else:
                error_msg = f"فشل إنشاء النسخة الاحتياطية: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                QMessageBox.warning(self, "خطأ", error_msg)
                
        except Exception as e:
            print(f"Error creating backup: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر إنشاء النسخة الاحتياطية: {str(e)}")
    
    def restore_backup(self):
        """Restore from a backup."""
        try:
            # Get backup file from user
            backup_file, _ = QFileDialog.getOpenFileName(
                self, "اختر ملف النسخة الاحتياطية", "", "ملفات ZIP (*.zip)"
            )
            
            if not backup_file:
                return  # User canceled
                
            # Confirm restore
            confirm = QMessageBox.warning(
                self,
                "تأكيد الاستعادة",
                "سيؤدي استعادة النسخة الاحتياطية إلى استبدال جميع البيانات الحالية. هل أنت متأكد من المتابعة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm != QMessageBox.StandardButton.Yes:
                return
                
            # Upload backup file to server
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            with open(backup_file, 'rb') as f:
                files = {'backup_file': (os.path.basename(backup_file), f, 'application/zip')}
                response = requests.post(f"{self.api_url}/restore/", headers=headers, files=files)
            
            if response.status_code == 200:
                QMessageBox.information(
                    self, 
                    "نجاح", 
                    "تم استعادة النسخة الاحتياطية بنجاح. سيتم إعادة تشغيل النظام."
                )
                # In a real application, you would restart the application here
            else:
                error_msg = f"فشل استعادة النسخة الاحتياطية: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                QMessageBox.warning(self, "خطأ", error_msg)
                
        except Exception as e:
            print(f"Error restoring backup: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر استعادة النسخة الاحتياطية: {str(e)}")
    