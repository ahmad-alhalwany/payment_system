from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import requests
import jwt
import datetime
import os

# Secret key for generating local tokens - should match the one in backend/security.py
SECRET_KEY = "929b15e43fd8f1cf4df79d86eb93ca426ab58ae53386c7a91ac4adb45832773b"
ALGORITHM = "HS256"

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("تسجيل الدخول")
        self.setGeometry(200, 200, 400, 300)
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
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-size: 14px;
            }
        """)

        self.layout = QVBoxLayout()

        # Title
        title = QLabel("نظام تحويل الأموال الداخلي")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        self.layout.addWidget(title)

        self.username_label = QLabel("اسم المستخدم:")
        self.username_input = QLineEdit(self)
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        self.password_label = QLabel("كلمة المرور:")
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        self.login_button = QPushButton("تسجيل الدخول")
        self.login_button.clicked.connect(self.check_login)
        self.login_button.setStyleSheet("""
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
        self.layout.addWidget(self.login_button)

        # Add a "Create User" button for admins and branch managers
        self.create_user_button = QPushButton("إنشاء مستخدم جديد")
        self.create_user_button.clicked.connect(self.open_create_user_dialog)
        self.create_user_button.setVisible(False)  # Hidden by default
        self.layout.addWidget(self.create_user_button)

        self.setLayout(self.layout)

        self.user_role = None
        self.branch_id = None  # Store branch_id for branch managers
        self.user_id = None    # Store user_id
        self.token = None      # Store authentication token
        
        self.check_initialization()

    def check_initialization(self):
        try:
            api_url = os.environ["API_URL"]
            response = requests.get(f"{api_url}/check-initialization/")
            if response.status_code == 200 and not response.json().get("is_initialized"):
                dialog = SetupDialog(self)
                dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر التحقق من تهيئة النظام: {str(e)}")        

    def check_login(self):
        """Check login credentials via the backend."""
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال اسم المستخدم وكلمة المرور!")
            return

        # Attempt backend login
        self.backend_login(username, password)

    def create_local_token(self, username, role, branch_id, user_id=1):
        """Create a JWT token for local testing that matches the backend token format."""
        # Set expiration time to 24 hours from now
        expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        
        # Create token payload
        payload = {
            "username": username,
            "role": role,
            "branch_id": branch_id,
            "user_id": user_id,
            "exp": expiration
        }
        
        # Generate token
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token

    def backend_login(self, username, password):
        """Authenticate user using the backend API."""
        try:
            api_url = os.environ["API_URL"]
            response = requests.post(
                f"{api_url}/login/",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
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
            else:
                QMessageBox.warning(self, "خطأ في تسجيل الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة!")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الاتصال", f"تعذر الاتصال بالخادم: {str(e)}")

    def open_create_user_dialog(self):
        """Open a dialog to create a new user."""
        dialog = CreateUserDialog(self.user_role, self.branch_id, self.token, self)
        dialog.exec()

class CreateUserDialog(QDialog):
    """Dialog to create a new user."""
    def __init__(self, user_role, branch_id, token, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إنشاء مستخدم جديد")
        self.setGeometry(250, 250, 400, 350)
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
            self.role_input.addItems(["موظف"])  # Branch managers can only create employees
        layout.addWidget(self.role_label)
        layout.addWidget(self.role_input)

        if self.user_role == "director":
            self.branch_label = QLabel("الفرع:")
            self.branch_input = QComboBox(self)
            layout.addWidget(self.branch_label)
            layout.addWidget(self.branch_input)
            self.load_branches()

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
        """Load branches from the API."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            api_url = os.environ["API_URL"]
            response = requests.get(f"{api_url}/branches/", headers=headers)
            
            if response.status_code == 200:
                branches = response.json()
                self.branch_input.clear()
                
                for branch in branches:
                    self.branch_input.addItem(branch["name"], branch["id"])
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل الفروع! الخطأ: {response.status_code} - {response.text}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")

    def create_user(self):
        """Create a new user using the backend API."""
        username = self.username_input.text()
        password = self.password_input.text()
        role = "branch_manager" if self.role_input.currentText() == "مدير فرع" else "employee"

        if not username or not password:
            QMessageBox.warning(self, "خطأ", "يرجى ملء جميع الحقول!")
            return

        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Determine branch_id based on user role
            selected_branch_id = None
            if self.user_role == "director":
                selected_branch_id = self.branch_input.currentData()
            else:
                selected_branch_id = self.branch_id
            api_url = os.environ["API_URL"]
            response = requests.post(
                f"{api_url}/register/",
                json={
                    "username": username,
                    "password": password,
                    "role": role,
                    "branch_id": selected_branch_id
                },
                headers=headers
            )

            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم إنشاء المستخدم بنجاح!")
                self.accept()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في إنشاء المستخدم: الخطأ: {response.status_code} - {response.text}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")

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

        self.password_label = QLabel("كلمة المرور:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.confirm_label = QLabel("تأكيد كلمة المرور:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_label)
        layout.addWidget(self.confirm_input)

        self.submit_button = QPushButton("تهيئة النظام")
        self.submit_button.clicked.connect(self.submit_setup)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

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