import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./transactions.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_database():
    # Delete existing database if it exists
    if os.path.exists("transactions.db"):
        os.remove("transactions.db")
        print("Old database removed")
    
    # Create new database with current schema
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()
    
    # Create tables with all current columns
    cursor.execute("""
        CREATE TABLE branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id TEXT UNIQUE,
            name TEXT UNIQUE,
            location TEXT,
            governorate TEXT,
            allocated_amount_syp REAL DEFAULT 0.0,
            allocated_amount_usd REAL DEFAULT 0.0,
            allocated_amount REAL DEFAULT 0.0,  -- Kept for backward compatibility
            tax_rate REAL DEFAULT 0.0,  -- Added tax rate field
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE branch_funds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER,
            amount REAL,
            type TEXT CHECK(type IN ('allocation', 'deduction', 'refund')),
            currency TEXT DEFAULT 'SYP',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT CHECK(role IN ('director', 'branch_manager', 'employee')),
            branch_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            sender TEXT,
            sender_mobile TEXT,
            sender_governorate TEXT,
            sender_location TEXT,
            sender_id TEXT,
            sender_address TEXT,
            
            receiver TEXT,
            receiver_mobile TEXT,
            receiver_governorate TEXT,
            receiver_location TEXT,
            receiver_id TEXT,
            receiver_address TEXT,
            
            amount REAL,
            base_amount REAL DEFAULT 0.0,
            benefited_amount REAL DEFAULT 0.0,
            tax_rate REAL DEFAULT 0.0,
            tax_amount REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'SYP',
            
            message TEXT,
            branch_id INTEGER,
            destination_branch_id INTEGER,
            employee_id INTEGER,
            employee_name TEXT,
            branch_governorate TEXT,
            
            status TEXT DEFAULT 'pending',
            is_received BOOLEAN DEFAULT FALSE,
            received_by INTEGER,
            received_at TIMESTAMP,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL,
            FOREIGN KEY (destination_branch_id) REFERENCES branches(id),
            FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (received_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            recipient_phone TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    print("New database created with current schema")

# ---
# Recommended SQL commands to add indexes for better search performance:
# Run these in your SQLite database (once) if you have a lot of data or want faster search:
#
# CREATE INDEX idx_transactions_id ON transactions(id);
# CREATE INDEX idx_transactions_sender ON transactions(sender);
# CREATE INDEX idx_transactions_receiver ON transactions(receiver);
# CREATE INDEX idx_transactions_status ON transactions(status);
# CREATE INDEX idx_transactions_date ON transactions(date);
# ---

if __name__ == "__main__":
    reset_database()