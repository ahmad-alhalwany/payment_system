import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import requests

class UserManagement(QDialog):
    def __init__(self, branch_id, token=None):
        super().__init__()
        self.branch_id = branch_id  # Store the branch_id
        self.token = token  # Store the token
        self.setWindowTitle("إدارة الموظفين")
        self.setGeometry(200, 200, 900, 650)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
                font-size: 14px;
            }
            QTableWidget {
                border: 1px solid #e6e6e6;
                border-radius: 8px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        self.layout = QVBoxLayout()
        self.all_employees = []  # Store all employees for filtering

        # Header section with card-like design
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        
        self.title = QLabel(f"إدارة الموظفين للفرع: {self.branch_id}")
        self.title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        header_layout.addWidget(self.title)
        
        # Subtitle
        subtitle = QLabel("قائمة الموظفين وإدارة الصلاحيات")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; margin-bottom: 10px; font-size: 16px;")
        header_layout.addWidget(subtitle)
        
        self.layout.addWidget(header_widget)
        self.layout.addSpacing(15)
        
        # Search and filter section
        search_filter_container = QWidget()
        search_filter_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                padding: 10px;
            }
        """)
        search_filter_layout = QVBoxLayout(search_filter_container)
        
        search_filter_title = QLabel("بحث وتصفية")
        search_filter_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        search_filter_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        search_filter_layout.addWidget(search_filter_title)
        
        # Search and filter controls
        controls_layout = QHBoxLayout()
        
        # Search by name
        search_layout = QVBoxLayout()
        search_label = QLabel("بحث باسم الموظف:")
        search_label.setStyleSheet("font-weight: bold;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("أدخل اسم الموظف للبحث")
        self.search_input.textChanged.connect(self.filter_employees)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        controls_layout.addLayout(search_layout)
        
        # Filter by role
        role_filter_layout = QVBoxLayout()
        role_filter_label = QLabel("تصفية حسب الوظيفة:")
        role_filter_label.setStyleSheet("font-weight: bold;")
        self.role_filter = QComboBox()
        self.role_filter.addItems(["الكل", "مدير فرع", "موظف تحويلات"])
        self.role_filter.currentTextChanged.connect(self.filter_employees)
        role_filter_layout.addWidget(role_filter_label)
        role_filter_layout.addWidget(self.role_filter)
        controls_layout.addLayout(role_filter_layout)
        
        search_filter_layout.addLayout(controls_layout)
        self.layout.addWidget(search_filter_container)
        self.layout.addSpacing(15)
        
        # Employees table with card-like design
        table_container = QWidget()
        table_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                padding: 10px;
            }
        """)
        table_layout = QVBoxLayout(table_container)
        
        table_title = QLabel("قائمة الموظفين")
        table_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        table_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        table_layout.addWidget(table_title)
        
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(5)
        self.employees_table.setHorizontalHeaderLabels(["معرف", "اسم الموظف", "الوظيفة", "الفرع", "الإجراءات"])
        self.employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.employees_table.setAlternatingRowColors(True)
        self.employees_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.employees_table.setStyleSheet("""
            QTableWidget {
                border: none;
                border-radius: 8px;
                background-color: white;
            }
        """)
        table_layout.addWidget(self.employees_table)
        
        self.layout.addWidget(table_container)
        
        # Buttons section with card-like design
        buttons_container = QWidget()
        buttons_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                padding: 15px;
            }
        """)
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(15)
        
        # Add employee button
        self.add_employee_button = QPushButton("➕ إضافة موظف جديد")
        self.add_employee_button.clicked.connect(self.add_employee)
        self.add_employee_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                min-height: 45px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        buttons_layout.addWidget(self.add_employee_button)
        
        # Edit employee button
        self.edit_employee_button = QPushButton("✏️ تعديل الموظف المحدد")
        self.edit_employee_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                min-height: 45px;
            }
            QPushButton:hover {
                background-color: #f1c40f;
            }
        """)
        buttons_layout.addWidget(self.edit_employee_button)
        
        # Delete employee button
        self.delete_employee_button = QPushButton("❌ حذف الموظف المحدد")
        self.delete_employee_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                min-height: 45px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        buttons_layout.addWidget(self.delete_employee_button)
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 تحديث القائمة")
        self.refresh_button.clicked.connect(self.load_employees)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                min-height: 45px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        buttons_layout.addWidget(self.refresh_button)
        
        self.layout.addSpacing(15)
        self.layout.addWidget(buttons_container)
        
        self.setLayout(self.layout)
        
        # Load employees data
        self.load_employees()

    def load_employees(self):
        """Load employees data for this branch."""
        try:
            api_url = os.environ["API_URL"]
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{api_url}/branches/{self.branch_id}/employees/", headers=headers)
            
            if response.status_code == 200:
                self.all_employees = response.json()
                # Apply any existing filters
                self.filter_employees()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل الموظفين! الخطأ: {response.status_code}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")
            
    def filter_employees(self):
        """Filter employees based on search text and role filter."""
        # Get filter criteria
        search_text = self.search_input.text().lower()
        role_filter = self.role_filter.currentText()
        
        # Apply filters
        filtered_employees = []
        for employee in self.all_employees:
            # Filter by name
            employee_name = employee.get("username", "").lower()
            if search_text and search_text not in employee_name:
                continue
                
            # Filter by role
            employee_role = "مدير فرع" if employee.get("role") == "branch_manager" else "موظف تحويلات"
            if role_filter != "الكل" and role_filter != employee_role:
                continue
                
            # Employee passed all filters
            filtered_employees.append(employee)
        
        # Update table with filtered employees
        self.update_employees_table(filtered_employees)
        
    def update_employees_table(self, employees):
        """Update the employees table with the given list of employees."""
        self.employees_table.setRowCount(len(employees))
        
        for row, employee in enumerate(employees):
            # ID
            id_item = QTableWidgetItem(str(employee.get("id", "")))
            self.employees_table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(employee.get("username", ""))
            self.employees_table.setItem(row, 1, name_item)
            
            # Role
            role_text = "مدير فرع" if employee.get("role") == "branch_manager" else "موظف تحويلات"
            role_item = QTableWidgetItem(role_text)
            self.employees_table.setItem(row, 2, role_item)
            
            # Branch
            branch_item = QTableWidgetItem(str(employee.get("branch_id", "")))
            self.employees_table.setItem(row, 3, branch_item)
            
            # Actions - placeholder for now
            actions_item = QTableWidgetItem("...")
            self.employees_table.setItem(row, 4, actions_item)

    def add_employee(self):
        """Add a new employee."""
        self.add_employee_window = AddEmployeeDialog(is_admin=True, branch_id=self.branch_id, token=self.token)
        if self.add_employee_window.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "نجاح", "تمت إضافة الموظف بنجاح!")
            self.load_employees()  # Refresh the employee list

class AddEmployeeDialog(QDialog):
    def __init__(self, is_admin=False, branch_id=None, token=None, current_user_id=None):
        super().__init__()
        self.api_url = os.environ["API_URL"] 
        self.current_user_id = current_user_id
        self.setWindowTitle("إضافة موظف جديد")
        self.setGeometry(250, 250, 450, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 14px;
                margin-top: 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                font-size: 14px;
                margin-bottom: 5px;
            }
        """)

        self.is_admin = is_admin
        self.branch_id = branch_id
        self.token = token  # Store the token

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title with card-like design
        title_container = QWidget()
        title_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                padding: 10px;
            }
        """)
        title_layout = QVBoxLayout(title_container)
        
        title = QLabel("إضافة موظف جديد")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 5px 0;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("أدخل معلومات الموظف الجديد")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        title_layout.addWidget(subtitle)
        
        layout.addWidget(title_container)
        layout.addSpacing(15)

        # Form with card-like design
        form_container = QWidget()
        form_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                padding: 15px;
            }
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(12)

        # Employee name
        name_label = QLabel("👤 اسم الموظف:")
        name_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("أدخل اسم الموظف")
        form_layout.addWidget(self.name_input)
        form_layout.addSpacing(5)

        # Password
        password_label = QLabel("🔑 كلمة المرور:")
        password_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("أدخل كلمة المرور")
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(5)

        # Role
        role_label = QLabel("💼 الوظيفة:")
        role_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(role_label)
        
        self.role_input = QComboBox()
        if self.is_admin:
            self.role_input.addItems(["مدير فرع", "موظف تحويلات"])
        else:
            self.role_input.addItems(["موظف تحويلات"])
            self.role_input.setEnabled(False)
        form_layout.addWidget(self.role_input)
        form_layout.addSpacing(5)

        # Branch
        branch_label = QLabel("🏢 الفرع:")
        branch_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(branch_label)
        
        self.branch_input = QComboBox()
        form_layout.addWidget(self.branch_input)
        
        layout.addWidget(form_container)
        layout.addSpacing(15)

        # Save button
        self.save_button = QPushButton("✅ حفظ")
        self.save_button.clicked.connect(self.save_employee)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 15px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        layout.addWidget(self.save_button)

        self.name_input.textChanged.connect(self.validate_inputs)
        self.password_input.textChanged.connect(self.validate_inputs)

        self.setLayout(layout)
        
        # Initially disable save button
        self.save_button.setEnabled(False)
        
        # Load branches
        self.load_branches()

    def load_branches(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            if self.is_admin:
                response = requests.get(f"{self.api_url}/branches/", headers=headers)
                if response.status_code == 200:
                    # Extract branches list from the response
                    branches = response.json().get("branches", [])  # Fixed here
                    for branch in branches:
                        self.branch_input.addItem(branch.get("name"), branch.get("id"))
            else:
                # Load only current branch for branch managers
                response = requests.get(f"{self.api_url}/branches/{self.branch_id}", headers=headers)
                if response.status_code == 200:
                    branch = response.json()
                    self.branch_input.addItem(branch.get("name"), branch.get("id"))
                    self.branch_input.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load branches: {str(e)}")

    def validate_inputs(self):
        """Enable the save button only when all fields are filled."""
        name = self.name_input.text()
        password = self.password_input.text()

        if name and password:
            self.save_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)

    def save_employee(self):
        """Send employee data to the API for registration."""
        data = {
            "username": self.name_input.text(),
            "password": self.password_input.text(),
            "role": "branch_manager" if self.role_input.currentText() == "مدير فرع" else "employee",
            "branch_id": self.branch_input.currentData()
        }

        try:
            # Ensure token is properly formatted with Bearer prefix
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            # print(f"Using token: {self.token}")
            # print(f"Sending data: {data}")
            
            # Use /users/ endpoint instead of /register/ as it has the same functionality but with better error handling
            response = requests.post(
                f"{self.api_url}/users/", 
                json=data, 
                headers=headers,
                timeout=5  # إضافة مهلة للاتصال
            )
            if response.status_code == 200:  # عادةً 201 للإنشاء الناجح
                QMessageBox.information(self, "نجاح", "تمت إضافة الموظف بنجاح!")
                self.accept()
            else:
                error_details = response.json().get("detail", "خطأ غير معروف")
                QMessageBox.warning(
                    self, 
                    "خطأ", 
                    f"فشل في الإضافة: {response.status_code}\nالتفاصيل: {error_details}"
                )
        except requests.exceptions.RequestException as e:
            QMessageBox.warning(
                self, 
                "خطأ اتصال", 
                f"تعذر الاتصال بالخادم: {str(e)}"
            )
            
            
class EditEmployeeDialog(QDialog):
    def __init__(self, employee_data, token=None, is_admin=False, current_branch_id=None, current_user_id=None):
        super().__init__()
        self.token = token
        self.api_url = os.environ["API_URL"]
        self.is_admin = is_admin
        self.current_branch_id = current_branch_id
        self.current_user_id = current_user_id
        self.employee_data = employee_data

        # Security check: Prevent self-editing
        if str(employee_data.get("id")) == str(self.current_user_id):
            QMessageBox.warning(self, "تحذير", "لا يمكنك تعديل حسابك الخاص!")
            self.reject()
            return

        # Security check: Validate employee data
        if not employee_data or not isinstance(employee_data, dict):
            QMessageBox.critical(self, "خطأ", "بيانات الموظف غير صالحة!")
            self.reject()
            return

        # Initialize UI
        self.setup_ui()
        self.load_branches()

    def setup_ui(self):
        self.setWindowTitle("تعديل بيانات الموظف")
        self.setGeometry(250, 250, 450, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 14px;
                margin-top: 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                font-size: 14px;
                margin-bottom: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Title Section
        title_container = QWidget()
        title_container.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #e6e6e6; padding: 10px;")
        title_layout = QVBoxLayout(title_container)
        
        title = QLabel("تعديل بيانات الموظف")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)
        
        layout.addWidget(title_container)
        layout.addSpacing(15)

        # Form Section
        form_container = QWidget()
        form_container.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #e6e6e6; padding: 15px;")
        form_layout = QVBoxLayout(form_container)

        # Username Field
        name_label = QLabel("👤 اسم الموظف:")
        name_label.setStyleSheet("font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setText(self.employee_data.get("username", ""))
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)

        # Role Field
        role_label = QLabel("💼 الوظيفة:")
        role_label.setStyleSheet("font-weight: bold;")
        self.role_input = QComboBox()
        
        # Role restrictions for non-admins
        if self.is_admin:
            self.role_input.addItems(["مدير فرع", "موظف تحويلات"])
        else:
            self.role_input.addItem("موظف تحويلات")
            self.role_input.setEnabled(False)
        
        current_role = "مدير فرع" if self.employee_data.get("role") == "branch_manager" else "موظف تحويلات"
        self.role_input.setCurrentText(current_role)
        form_layout.addWidget(role_label)
        form_layout.addWidget(self.role_input)
        
        # Add branch input widget
        self.branch_input = QComboBox()

        # Branch Field
        branch_label = QLabel("🏢 الفرع:")
        branch_label.setStyleSheet("font-weight: bold;")
        self.branch_input = QComboBox()
        form_layout.addWidget(branch_label)
        form_layout.addWidget(self.branch_input)

        layout.addWidget(form_container)
        layout.addSpacing(15)

        # Save Button
        self.save_button = QPushButton("💾 حفظ التعديلات")
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 15px;
                min-height: 50px;
            }
            QPushButton:hover { background-color: #f1c40f; }
        """)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def load_branches(self):
        """Load branches with restrictions for non-admins"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            branches = []
            error_message = ""

            if self.is_admin:
                # Load all branches for admins
                try:
                    response = requests.get(
                        f"{self.api_url}/branches/",
                        headers=headers,
                        timeout=10  # Added timeout
                    )
                    response.raise_for_status()
                    
                    # Validate response format
                    if isinstance(response.json().get("branches", []), list):
                        branches = response.json()["branches"]
                    else:
                        raise ValueError("Invalid branches format in response")
                        
                except requests.exceptions.RequestException as e:
                    error_message = f"فشل الاتصال بالخادم: {str(e)}"
                except ValueError as e:
                    error_message = f"تنسيق بيانات الفروع غير صالح: {str(e)}"
                    
            else:
                # Load only current branch for branch managers
                try:
                    if not self.current_branch_id:
                        raise ValueError("معرف الفرع الحالي غير صالح")

                    response = requests.get(
                        f"{self.api_url}/branches/{self.current_branch_id}",
                        headers=headers,
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    # Validate single branch response
                    branch_data = response.json()
                    if isinstance(branch_data, dict) and "id" in branch_data:
                        branches = [branch_data]
                    else:
                        raise ValueError("تنسيق بيانات الفرع غير صالح")
                        
                except requests.exceptions.RequestException as e:
                    status_code = response.status_code if response else "N/A"
                    error_message = f"فشل تحميل الفرع (الكود: {status_code}): {str(e)}"
                except ValueError as e:
                    error_message = str(e)

            # Handle errors
            if error_message:
                raise Exception(error_message)

            # Clear and populate branches
            self.branch_input.clear()
            for branch in branches:
                branch_name = branch.get("name", "فرع غير معروف")
                branch_id = branch.get("id")
                
                # Validate branch ID exists
                if branch_id is None:
                    continue
                    
                self.branch_input.addItem(branch_name, branch_id)

            # Set current branch selection
            current_branch_id = self.employee_data.get("branch_id")
            if current_branch_id:
                index = self.branch_input.findData(current_branch_id)
                if index >= 0:
                    self.branch_input.setCurrentIndex(index)
                else:
                    self.branch_input.setCurrentIndex(0)  # Fallback to first item

            # Disable branch selection for non-admins
            if not self.is_admin:
                self.branch_input.setEnabled(False)
                if self.branch_input.count() == 0:
                    raise Exception("لا يوجد فروع متاحة للعرض")

        except Exception as e:
            QMessageBox.warning(
                self,
                "خطأ في تحميل الفروع",
                f"""تعذر تحميل بيانات الفروع:
                
                التفاصيل: {str(e)}
                الرجاء التحقق من:
                1. اتصالك بالإنترنت
                2. صلاحيات المستخدم
                3. صحة بيانات الفرع"""
            )
            self.reject()  # Close dialog on critical error

    def save_changes(self):
        """Save changes with security validations"""
        # Validate role changes
        new_role = "branch_manager" if self.role_input.currentText() == "مدير فرع" else "employee"
        if not self.is_admin and new_role == "branch_manager":
            QMessageBox.warning(self, "خطأ", "غير مصرح لك بتغيير الدور إلى مدير فرع!")
            return

        # Validate branch changes
        new_branch = self.branch_input.currentData()
        if not self.is_admin and new_branch != self.current_branch_id:
            QMessageBox.warning(self, "خطأ", "غير مصرح لك بنقل الموظف إلى فرع آخر!")
            return

        # Prepare data
        data = {
            "username": self.name_input.text(),
            "role": new_role,
            "branch_id": new_branch
        }

        # Send request
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.put(
                f"{self.api_url}/users/{self.employee_data.get('id')}/",
                json=data,
                headers=headers
            )

            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث بيانات الموظف بنجاح!")
                self.accept()
            else:
                error_msg = f"فشل التحديث: {response.status_code}"
                try:
                    error_details = response.json().get("detail", "")
                    error_msg += f"\nالتفاصيل: {error_details}"
                except:
                    pass
                QMessageBox.warning(self, "خطأ", error_msg)

        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")
