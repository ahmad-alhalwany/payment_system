import os
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
from ui.money_transfer_improved import MoneyTransferApp
from ui.dashboard_improved import DirectorDashboard
from ui.branch_manager_dashboard import BranchManagerDashboard
from ui.user_search import UserSearchDialog
from login_fixed import LoginWindow
from dotenv import load_dotenv
from config import setup_environment

def main():
    # Set up environment variables
    setup_environment()

    app = QApplication(sys.argv)
    load_dotenv()
    # Set application-wide font for Arabic support
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # Apply stylesheet for modern look
    app.setStyleSheet("""
        QWidget {
            font-family: Arial;
        }
        QMessageBox {
            background-color: #f5f5f5;
        }
        QMessageBox QPushButton {
            background-color: #2c3e50;
            color: white;
            border-radius: 5px;
            padding: 6px 12px;
            font-weight: bold;
        }
        QMessageBox QPushButton:hover {
            background-color: #34495e;
        }
        QPushButton {
            background-color: #2980b9;
            color: white;
            border-radius: 8px;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border: none;
        }
        QPushButton:hover {
            background-color: #3498db;
        }
        QPushButton:pressed {
            background-color: #1c6ea4;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
            border-radius: 8px;
            background-color: rgba(255, 255, 255, 0.7);
        }
        QTabBar::tab {
            background-color: #ddd;
            padding: 10px 15px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background-color: #2c3e50;
            color: white;
        }
        QTableWidget {
            border: none;
            background-color: white;
            gridline-color: #ddd;
        }
        QHeaderView::section {
            background-color: #2c3e50;
            color: white;
            padding: 8px;
            border: 1px solid #1a2530;
            font-weight: bold;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
    """)

    login_window = LoginWindow()
    
    if login_window.exec() == 1:  # Check if login was successful
        user_role = login_window.user_role 
        branch_id = login_window.branch_id
        user_id = login_window.user_id
        token = login_window.token
        username = login_window.username if hasattr(login_window, 'username') else "User"

        if user_role == "director":
            # Pass the updated parameters to DirectorDashboard
            window = DirectorDashboard(token=token)
            window.setWindowTitle("لوحة تحكم المدير - نظام التحويلات المالية")
        elif user_role == "branch_manager":
            print(f"Creating BranchManagerDashboard with branch_id={branch_id}, token={token}")
            window = BranchManagerDashboard(
                branch_id=branch_id,
                token=token,
                user_id=user_id,  # Use the extracted user_id
                username=username,
                full_name=username,  # Or actual name if available
            )
            window.setWindowTitle(f"لوحة تحكم مدير الفرع - نظام التحويلات المالية")
        elif user_role == "employee":
            # Use our updated MoneyTransferApp with all the new features
            window = MoneyTransferApp(
                user_token=token,
                branch_id=branch_id,
                user_id=user_id,
                user_role=user_role,
                username=username
            )
            window.setWindowTitle(f"واجهة موظف التحويلات - نظام التحويلات المالية")
        else:
            QMessageBox.warning(None, "خطأ", "دور المستخدم غير معروف!")
            sys.exit()

        window.show()
        sys.exit(app.exec())
    else:
        sys.exit()  # Exit if login was not successful

if __name__ == "__main__":
    main()
