import os
import json
import requests
import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QProgressBar, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from ui.custom_widgets import ModernGroupBox, ModernButton

class PasswordWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, api_url, token, old_password, new_password):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.old_password = old_password
        self.new_password = new_password
    
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            data = {
                "old_password": self.old_password,
                "new_password": self.new_password
            }
            response = requests.post(f"{self.api_url}/change-password/", json=data, headers=headers)
            
            if response.status_code == 200:
                self.finished.emit(True, "تم تغيير كلمة المرور بنجاح")
            else:
                error_msg = f"فشل تغيير كلمة المرور: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                self.finished.emit(False, error_msg)
        except Exception as e:
            self.finished.emit(False, str(e))

class BackupWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    
    def __init__(self, api_url, token, backup_file):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.backup_file = backup_file
    
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/backup/", headers=headers, stream=True)
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                written = 0
                
                with open(self.backup_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        f.write(chunk)
                        written += len(chunk)
                        if total_size:
                            progress = int((written / total_size) * 100)
                            self.progress.emit(progress)
                
                self.finished.emit(True, self.backup_file)
            else:
                error_msg = f"فشل إنشاء النسخة الاحتياطية: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                self.finished.emit(False, error_msg)
        except Exception as e:
            self.finished.emit(False, str(e))

class RestoreWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    
    def __init__(self, api_url, token, backup_file):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.backup_file = backup_file
    
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            with open(self.backup_file, 'rb') as f:
                files = {'backup_file': (os.path.basename(self.backup_file), f, 'application/zip')}
                response = requests.post(
                    f"{self.api_url}/restore/",
                    headers=headers,
                    files=files
                )
            
            if response.status_code == 200:
                self.finished.emit(True, "تم استعادة النسخة الاحتياطية بنجاح")
            else:
                error_msg = f"فشل استعادة النسخة الاحتياطية: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                self.finished.emit(False, error_msg)
        except Exception as e:
            self.finished.emit(False, str(e))

class SettingsHandlerMixin:
    """Mixin class handling system settings and maintenance functionality"""
    def setup_settings_tab(self):
        """Set up the settings tab."""
        layout = QVBoxLayout()
        
        # System settings
        settings_group = ModernGroupBox("إعدادات النظام", "#3498db")
        settings_layout = QFormLayout()
        
        # Add cache for settings
        self._settings_cache = {}
        self._last_settings_load = 0
        self._settings_cache_timeout = 300  # 5 minutes
        
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
        
        # Add progress bars
        self.backup_progress = QProgressBar()
        self.backup_progress.setVisible(False)
        self.backup_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        backup_layout.addWidget(self.backup_progress)
        
        self.restore_progress = QProgressBar()
        self.restore_progress.setVisible(False)
        self.restore_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        backup_layout.addWidget(self.restore_progress)
        
        # Add status labels
        self.backup_status = QLabel("")
        self.backup_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        backup_layout.addWidget(self.backup_status)
        
        self.restore_status = QLabel("")
        self.restore_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        backup_layout.addWidget(self.restore_status)
        
        backup_button = ModernButton("إنشاء نسخة احتياطية", color="#3498db")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)
        
        restore_button = ModernButton("استعادة من نسخة احتياطية", color="#e74c3c")
        restore_button.clicked.connect(self.restore_backup)
        backup_layout.addWidget(restore_button)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        self.settings_tab.setLayout(layout)
        
        # Load initial settings
        self.load_settings()

    def load_settings(self):
        """Load settings from file with caching."""
        try:
            current_time = datetime.datetime.now().timestamp()
            
            # Check if cache is valid
            if (self._settings_cache and 
                current_time - self._last_settings_load < self._settings_cache_timeout):
                self._apply_settings(self._settings_cache)
                return
            
            settings_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "settings.json"
            )
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self._settings_cache = settings
                    self._last_settings_load = current_time
                    self._apply_settings(settings)
                    
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _apply_settings(self, settings):
        """Apply settings to UI elements."""
        self.system_name_input.setText(settings.get("system_name", ""))
        self.company_name_input.setText(settings.get("company_name", ""))
        self.admin_email_input.setText(settings.get("admin_email", ""))
        
        currency = settings.get("default_currency", "ليرة سورية")
        index = self.currency_input.findText(currency)
        if index >= 0:
            self.currency_input.setCurrentIndex(index)
        
        language = settings.get("language", "العربية")
        index = self.language_input.findText(language)
        if index >= 0:
            self.language_input.setCurrentIndex(index)
        
        theme = settings.get("theme", "فاتح")
        index = self.theme_input.findText(theme)
        if index >= 0:
            self.theme_input.setCurrentIndex(index)

    def save_settings(self):
        """Save system settings with optimized file handling."""
        try:
            # Get settings values
            settings_data = {
                "system_name": self.system_name_input.text(),
                "company_name": self.company_name_input.text(),
                "admin_email": self.admin_email_input.text(),
                "default_currency": self.currency_input.currentText(),
                "language": self.language_input.currentText(),
                "theme": self.theme_input.currentText()
            }
            
            # Validate inputs
            if not all([settings_data["system_name"], 
                       settings_data["company_name"], 
                       settings_data["admin_email"]]):
                QMessageBox.warning(self, "تنبيه", "الرجاء ملء جميع الحقول المطلوبة")
                return
            
            # Update cache
            self._settings_cache = settings_data
            self._last_settings_load = datetime.datetime.now().timestamp()
            
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

    def update_backup_progress(self, value):
        """Update backup progress bar."""
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(value)
        self.backup_status.setText(f"جاري النسخ الاحتياطي... {value}%")
        if value >= 100:
            self.backup_progress.setVisible(False)
            self.backup_status.setText("")

    def update_restore_progress(self, value):
        """Update restore progress bar."""
        self.restore_progress.setVisible(True)
        self.restore_progress.setValue(value)
        self.restore_status.setText(f"جاري الاستعادة... {value}%")
        if value >= 100:
            self.restore_progress.setVisible(False)
            self.restore_status.setText("")

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
        
        self.password_worker = PasswordWorker(self.api_url, self.token, old_password, new_password)
        self.password_worker.finished.connect(self.on_password_change_complete)
        self.password_worker.start()
    
    def on_password_change_complete(self, success, message):
        if success:
            QMessageBox.information(self, "نجاح", message)
            self.old_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
        else:
            QMessageBox.warning(self, "خطأ", f"تعذر تغيير كلمة المرور: {message}")
    
    def create_backup(self):
        """Create a backup of the database."""
        try:
            backup_dir = QFileDialog.getExistingDirectory(
                self, "اختر مجلد النسخ الاحتياطي", ""
            )
            
            if not backup_dir:
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"system_backup_{timestamp}.sqlite")
            
            self.backup_worker = BackupWorker(self.api_url, self.token, backup_file)
            self.backup_worker.finished.connect(self.on_backup_complete)
            self.backup_worker.progress.connect(self.update_backup_progress)
            self.backup_worker.start()
            
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر إنشاء النسخة الاحتياطية: {str(e)}")
    
    def on_backup_complete(self, success, message):
        if success:
            QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة الاحتياطية بنجاح في:\n{message}")
        else:
            QMessageBox.warning(self, "خطأ", message)
    
    def restore_backup(self):
        """Restore from a backup."""
        try:
            backup_file, _ = QFileDialog.getOpenFileName(
                self, "اختر ملف النسخة الاحتياطية", "", "ملفات ZIP (*.zip)"
            )
            
            if not backup_file:
                return
            
            confirm = QMessageBox.warning(
                self,
                "تأكيد الاستعادة",
                "سيؤدي استعادة النسخة الاحتياطية إلى استبدال جميع البيانات الحالية. هل أنت متأكد من المتابعة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm != QMessageBox.StandardButton.Yes:
                return
            
            self.restore_worker = RestoreWorker(self.api_url, self.token, backup_file)
            self.restore_worker.finished.connect(self.on_restore_complete)
            self.restore_worker.progress.connect(self.update_restore_progress)
            self.restore_worker.start()
            
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر استعادة النسخة الاحتياطية: {str(e)}")
    
    def on_restore_complete(self, success, message):
        if success:
            QMessageBox.information(self, "نجاح", message + "\nسيتم إعادة تشغيل النظام.")
        else:
            QMessageBox.warning(self, "خطأ", message)
    