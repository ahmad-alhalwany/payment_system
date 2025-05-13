from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QProgressBar, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor
import requests
import jwt
import datetime
import os
import time
import json
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Secret key for generating local tokens - should match the one in backend/security.py
SECRET_KEY = "929b15e43fd8f1cf4df79d86eb93ca426ab58ae53386c7a91ac4adb45832773b"
ALGORITHM = "HS256"

class RequestManager:
    """Manages API requests with caching and concurrent execution"""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.session = requests.Session()
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes

    def _get_cache_key(self, url: str, params: Dict = None) -> str:
        """Generate cache key from URL and parameters"""
        if params:
            return f"{url}?{json.dumps(params, sort_keys=True)}"
        return url

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key in self.cache:
            cache_time, _ = self.cache[cache_key]
            return time.time() - cache_time < self.cache_timeout
        return False

    def get(self, url: str, params: Dict = None, headers: Dict = None, use_cache: bool = True) -> Dict:
        """Make GET request with caching"""
        cache_key = self._get_cache_key(url, params)
        
        if use_cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key][1]

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if use_cache:
                self.cache[cache_key] = (time.time(), data)
            
            return data
        except Exception as e:
            raise

    def post(self, url: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Make POST request"""
        try:
            response = self.session.post(url, json=data, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise

    def concurrent_get(self, urls: list, params_list: list = None, headers: Dict = None) -> list:
        """Execute multiple GET requests concurrently"""
        if params_list is None:
            params_list = [None] * len(urls)

        futures = []
        for url, params in zip(urls, params_list):
            futures.append(
                self.executor.submit(self.get, url, params, headers)
            )

        results = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                results.append(None)

        return results

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()

    def __del__(self):
        """Cleanup resources"""
        self.executor.shutdown(wait=False)
        self.session.close()

class LoginWorker(QThread):
    """Worker thread for handling login operations with improved error handling and progress tracking"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password
        self.max_retries = 3
        self.retry_delay = 1
        self.request_manager = RequestManager()

    def run(self):
        try:
            self.status.emit("جاري التحقق من البيانات...")
            self.progress.emit(10)
            
            api_url = os.environ["API_URL"]
            self.status.emit("جاري الاتصال بالخادم...")
            self.progress.emit(30)
            
            for attempt in range(self.max_retries):
                try:
                    self.status.emit(f"محاولة الاتصال {attempt + 1} من {self.max_retries}...")
                    response_data = self.request_manager.post(
                        f"{api_url}/login/",
                        data={"username": self.username, "password": self.password}
                    )
                    self.progress.emit(70)
                    
                    self.status.emit("تم تسجيل الدخول بنجاح!")
                    self.progress.emit(100)
                    self.finished.emit(response_data)
                    return
                except requests.exceptions.RequestException as e:
                    if attempt == self.max_retries - 1:
                        self.error.emit(f"تعذر الاتصال بالخادم: {str(e)}")
                        return
                    self.status.emit(f"فشل الاتصال، جاري إعادة المحاولة...")
                    time.sleep(self.retry_delay)
        except Exception as e:
            self.error.emit(f"حدث خطأ غير متوقع: {str(e)}")

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("تسجيل الدخول")
        self.setGeometry(200, 200, 450, 500)
        self.setWindowIcon(QIcon("payment-system.ico"))
        self.setup_ui()
        self.setup_styles()
        
        # Initialize other properties
        self.user_role = None
        self.branch_id = None
        self.user_id = None
        self.token = None
        self.username = None
        self.check_initialization()  # تحقق من التهيئة عند بدء التشغيل

    def check_initialization(self):
        try:
            api_url = os.environ["API_URL"]
            response = requests.get(f"{api_url}/check-initialization/", timeout=5)
            if response.status_code == 200 and not response.json().get("is_initialized"):
                dialog = SetupDialog(self)
                dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر التحقق من تهيئة النظام: {str(e)}")

    def setup_ui(self):
        """Set up the UI components with improved loading indicators"""
        self.layout = QVBoxLayout()
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # Create a frame for the content
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)

        # Logo or title
        title = QLabel("نظام تحويل الأموال الداخلي")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 30px;")
        content_layout.addWidget(title)

        # Username field
        self.username_label = QLabel("اسم المستخدم:")
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("أدخل اسم المستخدم")
        content_layout.addWidget(self.username_label)
        content_layout.addWidget(self.username_input)

        # Password field with toggle button
        self.password_label = QLabel("كلمة المرور:")
        content_layout.addWidget(self.password_label)
        
        password_layout = QHBoxLayout()
        password_layout.setSpacing(5)
        
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("أدخل كلمة المرور")
        password_layout.addWidget(self.password_input)
        
        self.toggle_password_button = QPushButton("👁️", self)
        self.toggle_password_button.setFixedWidth(40)
        self.toggle_password_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_button)
        
        content_layout.addLayout(password_layout)

        # Status label for detailed progress
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        content_layout.addWidget(self.status_label)

        # Progress bar with improved styling
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
                background-color: white;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 5px;
            }
        """)
        content_layout.addWidget(self.progress_bar)

        # Login button
        self.login_button = QPushButton("تسجيل الدخول")
        self.login_button.clicked.connect(self.check_login)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                padding: 12px;
                font-weight: bold;
                font-size: 16px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        content_layout.addWidget(self.login_button)

        # Create user button
        self.create_user_button = QPushButton("إنشاء مستخدم جديد")
        self.create_user_button.clicked.connect(self.open_create_user_dialog)
        self.create_user_button.setVisible(False)
        self.create_user_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        content_layout.addWidget(self.create_user_button)

        # Add content frame to main layout
        self.layout.addWidget(content_frame)
        self.setLayout(self.layout)

    def setup_styles(self):
        """Set up the window styles"""
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: Arial;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                margin-bottom: 5px;
            }
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 14px;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)

    def check_login(self):
        """Check login credentials with improved error handling and UI feedback"""
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال اسم المستخدم وكلمة المرور!")
            return

        # Disable inputs during login
        self.set_inputs_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري التحقق من البيانات...")

        # Start login worker
        self.worker = LoginWorker(username, password)
        self.worker.finished.connect(self.handle_login_success)
        self.worker.error.connect(self.handle_login_error)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.start()

    def set_inputs_enabled(self, enabled):
        """Enable or disable all input widgets"""
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.login_button.setEnabled(enabled)
        self.toggle_password_button.setEnabled(enabled)

    def update_progress(self, value):
        """Update progress bar value"""
        self.progress_bar.setValue(value)

    def update_status(self, status):
        """Update status label with current operation status"""
        self.status_label.setText(status)

    def handle_login_success(self, data):
        """Handle successful login with improved feedback"""
        self.user_role = data.get("role")
        self.branch_id = data.get("branch_id")
        self.user_id = data.get("user_id")
        self.token = data.get("token")
        self.username = data.get("username")

        # Show "Create User" button for admin and branch manager
        if self.user_role in ["director", "branch_manager"]:
            self.create_user_button.setVisible(True)

        QMessageBox.information(self, "نجاح", f"تم تسجيل الدخول بنجاح كـ {self.user_role}!")
        self.accept()

    def handle_login_error(self, error_message):
        """Handle login error with improved feedback"""
        self.set_inputs_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.warning(self, "خطأ في تسجيل الدخول", error_message)

    def toggle_password_visibility(self):
        """Toggle password visibility between hidden and visible."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText("👁️‍🗨️")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText("👁️")

    def open_create_user_dialog(self):
        """Open a dialog to create a new user."""
        dialog = CreateUserDialog(self.user_role, self.branch_id, self.token, self)
        dialog.exec()

class CreateUserWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, username, password, role, branch_id, token, api_url):
        super().__init__()
        self.username = username
        self.password = password
        self.role = role
        self.branch_id = branch_id
        self.token = token
        self.api_url = api_url

    def run(self):
        try:
            self.status.emit("جاري إرسال البيانات...")
            self.progress.emit(30)
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.post(
                f"{self.api_url}/register/",
                json={
                    "username": self.username,
                    "password": self.password,
                    "role": self.role,
                    "branch_id": self.branch_id
                },
                headers=headers
            )
            self.progress.emit(80)
            if response.status_code == 200:
                self.status.emit("تم إنشاء المستخدم بنجاح!")
                self.progress.emit(100)
                self.finished.emit()
            else:
                self.error.emit(f"فشل في إنشاء المستخدم: الخطأ: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(f"تعذر الاتصال بالخادم: {str(e)}")

class CreateUserDialog(QDialog):
    """Dialog to create a new user."""
    def __init__(self, user_role, branch_id, token, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إنشاء مستخدم جديد")
        self.setGeometry(250, 250, 400, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-size: 14px;
            }
        """)

        self.user_role = user_role
        self.branch_id = branch_id
        self.token = token
        self.cache_manager = CacheManager()

        layout = QVBoxLayout()

        # Title
        title = QLabel("إنشاء مستخدم جديد")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)

        self.username_label = QLabel("اسم المستخدم:")
        self.username_input = QLineEdit(self)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        self.password_label = QLabel("كلمة المرور:")
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.role_label = QLabel("الوظيفة:")
        self.role_input = QComboBox(self)
        if self.user_role == "director":
            self.role_input.addItems(["مدير فرع", "موظف"])
        else:
            self.role_input.addItems(["موظف"])
        layout.addWidget(self.role_label)
        layout.addWidget(self.role_input)

        if self.user_role == "director":
            self.branch_label = QLabel("الفرع:")
            self.branch_input = QComboBox(self)
            layout.addWidget(self.branch_label)
            layout.addWidget(self.branch_input)
            self.load_branches()

        # Status label and progress bar
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
                background-color: white;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.create_button = QPushButton("إنشاء مستخدم")
        self.create_button.clicked.connect(self.create_user)
        self.create_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        layout.addWidget(self.create_button)

        self.setLayout(layout)

    def load_branches(self):
        """Load branches from the API with caching."""
        try:
            # Try to get cached data first
            cached_branches = self.cache_manager.get_cached_data('branches')
            if cached_branches:
                self.branch_input.clear()
                for branch in cached_branches:
                    self.branch_input.addItem(branch["name"], branch["id"])
                return

            # If no cached data, fetch from API
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            api_url = os.environ["API_URL"]
            response = requests.get(f"{api_url}/branches/", headers=headers)
            
            if response.status_code == 200:
                branches = response.json()
                # Cache the branches data
                self.cache_manager.set_cached_data('branches', branches)
                
                self.branch_input.clear()
                for branch in branches:
                    self.branch_input.addItem(branch["name"], branch["id"])
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل الفروع! الخطأ: {response.status_code} - {response.text}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")

    def set_inputs_enabled(self, enabled):
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.role_input.setEnabled(enabled)
        if hasattr(self, 'branch_input'):
            self.branch_input.setEnabled(enabled)
        self.create_button.setEnabled(enabled)

    def create_user(self):
        """Create a new user using the backend API asynchronously."""
        username = self.username_input.text()
        password = self.password_input.text()
        role = "branch_manager" if self.role_input.currentText() == "مدير فرع" else "employee"

        if not username or not password:
            QMessageBox.warning(self, "خطأ", "يرجى ملء جميع الحقول!")
            return

        self.set_inputs_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري إرسال البيانات...")

        # Determine branch_id based on user role
        selected_branch_id = None
        if self.user_role == "director":
            selected_branch_id = self.branch_input.currentData()
        else:
            selected_branch_id = self.branch_id
        api_url = os.environ["API_URL"]

        self.worker = CreateUserWorker(username, password, role, selected_branch_id, self.token, api_url)
        self.worker.finished.connect(self.handle_create_success)
        self.worker.error.connect(self.handle_create_error)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.start()

    def handle_create_success(self):
        self.set_inputs_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.information(self, "نجاح", "تم إنشاء المستخدم بنجاح!")
        self.accept()

    def handle_create_error(self, error_message):
        self.set_inputs_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.warning(self, "خطأ", error_message)

class SetupDialog(QDialog):
    """Dialog for initial system setup."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تهيئة النظام")
        self.setGeometry(200, 200, 400, 300)
        self.setStyleSheet("""
            QWidget { background-color: #f5f5f5; font-family: Arial; }
            QLabel { color: #333; font-size: 14px; }
            QPushButton { 
                background-color: #27ae60; color: white; border-radius: 5px; 
                padding: 10px; font-weight: bold; margin-top: 20px;
            }
            QLineEdit { border: 1px solid #ccc; border-radius: 5px; padding: 8px; }
        """)

        layout = QVBoxLayout()

        title = QLabel("تهيئة النظام - إنشاء مدير النظام الأول")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.username_label = QLabel("اسم المستخدم:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        # Password field with toggle button
        self.password_label = QLabel("كلمة المرور:")
        layout.addWidget(self.password_label)
        
        password_layout = QHBoxLayout()
        password_layout.setSpacing(5)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_input)
        
        self.toggle_password_button = QPushButton("👁️", self)
        self.toggle_password_button.setFixedWidth(40)
        self.toggle_password_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_button)
        
        layout.addLayout(password_layout)

        # Confirm password field with toggle button
        self.confirm_label = QLabel("تأكيد كلمة المرور:")
        layout.addWidget(self.confirm_label)
        
        confirm_layout = QHBoxLayout()
        confirm_layout.setSpacing(5)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_layout.addWidget(self.confirm_input)
        
        self.toggle_confirm_button = QPushButton("👁️", self)
        self.toggle_confirm_button.setFixedWidth(40)
        self.toggle_confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.toggle_confirm_button.clicked.connect(self.toggle_confirm_visibility)
        confirm_layout.addWidget(self.toggle_confirm_button)
        
        layout.addLayout(confirm_layout)

        self.submit_button = QPushButton("تهيئة النظام")
        self.submit_button.clicked.connect(self.submit_setup)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def toggle_password_visibility(self):
        """Toggle password visibility between hidden and visible."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText("👁️‍🗨️")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText("👁️")

    def toggle_confirm_visibility(self):
        """Toggle confirm password visibility between hidden and visible."""
        if self.confirm_input.echoMode() == QLineEdit.EchoMode.Password:
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_confirm_button.setText("👁️‍🗨️")
        else:
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_confirm_button.setText("👁️")

    def submit_setup(self):
        username = self.username_input.text()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not username or not password or not confirm:
            QMessageBox.warning(self, "خطأ", "يرجى ملء جميع الحقول!")
            return

        if password != confirm:
            QMessageBox.warning(self, "خطأ", "كلمات المرور غير متطابقة!")
            return

        try:
            api_url = os.environ["API_URL"]
            response = requests.post(
                f"{api_url}/initialize-system/",
                json={"username": username, "password": password, "role": "director"}
            )
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تهيئة النظام بنجاح! يمكنك الآن تسجيل الدخول.")
                self.accept()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل التهيئة: {response.json().get('detail', '')}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")