import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog,
    QLineEdit, QFormLayout, QComboBox, QGroupBox,
)
from PyQt6.QtCore import Qt
import os

class ModernGroupBox(QGroupBox):
    """Custom styled group box."""
    
    def __init__(self, title, color="#3498db"):
        super().__init__(title)
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {color};
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {color};
            }}
        """)

class ModernButton(QPushButton):
    """Custom styled button."""
    
    def __init__(self, text, color="#3498db"):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """)
    
    def lighten_color(self, color):
        """Lighten a hex color."""
        # Simple implementation - not perfect but works for our needs
        if color.startswith('#'):
            color = color[1:]
        r = min(255, int(color[0:2], 16) + 20)
        g = min(255, int(color[2:4], 16) + 20)
        b = min(255, int(color[4:6], 16) + 20)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def darken_color(self, color):
        """Darken a hex color."""
        if color.startswith('#'):
            color = color[1:]
        r = max(0, int(color[0:2], 16) - 20)
        g = max(0, int(color[2:4], 16) - 20)
        b = max(0, int(color[4:6], 16) - 20)
        return f"#{r:02x}{g:02x}{b:02x}"

class AddBranchDialog(QDialog):
    """Dialog for adding a new branch."""
    
    def __init__(self, token=None, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = os.environ["API_URL"]
        
        self.setWindowTitle("إضافة فرع جديد")
        self.setGeometry(300, 300, 400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Form group
        form_group = ModernGroupBox("معلومات الفرع", "#3498db")
        form_layout = QFormLayout()
        
        # Branch ID
        branch_id_label = QLabel("رمز الفرع:")
        self.branch_id_input = QLineEdit()
        self.branch_id_input.setPlaceholderText("أدخل رمز الفرع")
        form_layout.addRow(branch_id_label, self.branch_id_input)
        
        # Branch name
        branch_name_label = QLabel("اسم الفرع:")
        self.branch_name_input = QLineEdit()
        self.branch_name_input.setPlaceholderText("أدخل اسم الفرع")
        form_layout.addRow(branch_name_label, self.branch_name_input)
        
        # Branch location
        branch_location_label = QLabel("موقع الفرع:")
        self.branch_location_input = QLineEdit()
        self.branch_location_input.setPlaceholderText("أدخل موقع الفرع")
        form_layout.addRow(branch_location_label, self.branch_location_input)
        
        # Branch governorate (dropdown)
        branch_governorate_label = QLabel("محافظة الفرع:")
        self.branch_governorate_combo = QComboBox()
        # Add all Syrian governorates
        self.branch_governorate_combo.addItems([
            "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", "الرقة", "دير الزور", 
            "الحسكة", "إدلب", "درعا", "السويداء", "القنيطرة", "ريف دمشق"
        ])
        form_layout.addRow(branch_governorate_label, self.branch_governorate_combo)
        
        # Branch manager field removed as requested
        
        # Branch status
        branch_status_label = QLabel("حالة الفرع:")
        self.branch_status_combo = QComboBox()
        self.branch_status_combo.addItems(["نشط", "غير نشط"])
        form_layout.addRow(branch_status_label, self.branch_status_combo)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_button = ModernButton("إلغاء", color="#e74c3c")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = ModernButton("حفظ", color="#2ecc71")
        save_button.clicked.connect(self.save_branch)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def save_branch(self):
        """Save the new branch."""
        # Validate inputs
        if not self.branch_id_input.text():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال رمز الفرع")
            return
        
        if not self.branch_name_input.text():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم الفرع")
            return
        
        if not self.branch_location_input.text():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال موقع الفرع")
            return
        
        # Prepare data
        data = {
            "branch_id": self.branch_id_input.text(),
            "name": self.branch_name_input.text(),
            "location": self.branch_location_input.text(),
            "governorate": self.branch_governorate_combo.currentText(),
            "status": "active" if self.branch_status_combo.currentText() == "نشط" else "inactive"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.post(f"{self.api_url}/branches/", json=data, headers=headers)
            
            if response.status_code == 201 or response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم إضافة الفرع بنجاح")
                self.accept()
            else:
                error_msg = f"فشل إضافة الفرع: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                QMessageBox.warning(self, "خطأ", error_msg)
        except Exception as e:
            print(f"Error adding branch: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")

class EditBranchDialog(QDialog):
    """Dialog for editing a branch."""
    
    def __init__(self, branch_data, token=None, parent=None):
        super().__init__(parent)
        self.branch_data = branch_data
        self.token = token
        self.api_url = os.environ["API_URL"]
        
        self.setWindowTitle("تعديل الفرع")
        self.setGeometry(300, 300, 400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Form group
        form_group = ModernGroupBox("معلومات الفرع", "#3498db")
        form_layout = QFormLayout()
        
        # Branch ID (read-only)
        branch_id_label = QLabel("رمز الفرع:")
        self.branch_id_input = QLineEdit()
        self.branch_id_input.setText(branch_data.get("branch_id", ""))
        self.branch_id_input.setReadOnly(True)
        self.branch_id_input.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow(branch_id_label, self.branch_id_input)
        
        # Branch name
        branch_name_label = QLabel("اسم الفرع:")
        self.branch_name_input = QLineEdit()
        self.branch_name_input.setText(branch_data.get("name", ""))
        form_layout.addRow(branch_name_label, self.branch_name_input)
        
        # Branch location
        branch_location_label = QLabel("موقع الفرع:")
        self.branch_location_input = QLineEdit()
        self.branch_location_input.setText(branch_data.get("location", ""))
        form_layout.addRow(branch_location_label, self.branch_location_input)
        
        # Branch governorate (dropdown)
        branch_governorate_label = QLabel("محافظة الفرع:")
        self.branch_governorate_combo = QComboBox()
        # Add all Syrian governorates
        governorates = [
            "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", "الرقة", "دير الزور", 
            "الحسكة", "إدلب", "درعا", "السويداء", "القنيطرة", "ريف دمشق"
        ]
        self.branch_governorate_combo.addItems(governorates)
        
        # Set current governorate if it exists
        current_governorate = branch_data.get("governorate", "")
        if current_governorate in governorates:
            self.branch_governorate_combo.setCurrentText(current_governorate)
        form_layout.addRow(branch_governorate_label, self.branch_governorate_combo)
        
        # Branch status
        branch_status_label = QLabel("حالة الفرع:")
        self.branch_status_combo = QComboBox()
        self.branch_status_combo.addItems(["نشط", "غير نشط"])
        # Set current status if it exists
        current_status = branch_data.get("status", "")
        if current_status == "active":
            self.branch_status_combo.setCurrentText("نشط")
        elif current_status == "inactive":
            self.branch_status_combo.setCurrentText("غير نشط")
        form_layout.addRow(branch_status_label, self.branch_status_combo)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_button = ModernButton("إلغاء", color="#e74c3c")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = ModernButton("حفظ", color="#2ecc71")
        save_button.clicked.connect(self.save_branch)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def save_branch(self):
        """Save the branch changes."""
        # Validate inputs
        if not self.branch_name_input.text():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم الفرع")
            return
        
        if not self.branch_location_input.text():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال موقع الفرع")
            return
        
        # Prepare data
        data = {
            "branch_id": self.branch_id_input.text(),
            "name": self.branch_name_input.text(),
            "location": self.branch_location_input.text(),
            "governorate": self.branch_governorate_combo.currentText(),
            "status": "active" if self.branch_status_combo.currentText() == "نشط" else "inactive"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.put(f"{self.api_url}/branches/{self.branch_id_input.text()}", json=data, headers=headers)
            
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث الفرع بنجاح")
                self.accept()
            else:
                error_msg = f"فشل تحديث الفرع: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                QMessageBox.warning(self, "خطأ", error_msg)
        except Exception as e:
            print(f"Error updating branch: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")

# Add a BranchManagement class for compatibility
class BranchManagement(QWidget):
    """Branch management widget."""
    
    def __init__(self, token=None, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = os.environ["API_URL"]
        
        self.setWindowTitle("إدارة الفروع")
        self.setGeometry(100, 100, 800, 600)
        
        # Create a simple layout that shows this is a placeholder
        layout = QVBoxLayout()
        label = QLabel("هذا الصف يستخدم فقط للتوافق. استخدم AddBranchDialog و EditBranchDialog بدلاً من ذلك.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        self.setLayout(layout)
