import os
import sqlite3

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
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE transactions (
            type TEXT,  -- Add this line
            id TEXT PRIMARY KEY,
            sender TEXT,
            sender_mobile TEXT,
            sender_governorate TEXT,
            sender_location TEXT,
            receiver TEXT,
            receiver_mobile TEXT,
            receiver_id TEXT,
            receiver_address TEXT,
            receiver_governorate TEXT,
            receiver_location TEXT,
            amount REAL,
            currency TEXT,
            message TEXT,
            branch_id INTEGER,  -- Sending branch
            destination_branch_id INTEGER,
            employee_id INTEGER,
            employee_name TEXT,
            branch_governorate TEXT,
            status TEXT DEFAULT 'processing',
            is_received BOOLEAN DEFAULT FALSE,
            received_by INTEGER,
            received_at TIMESTAMP,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL,
            FOREIGN KEY(destination_branch_id) REFERENCES branches(id),
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

if __name__ == "__main__":
    reset_database()