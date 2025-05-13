from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os

# Get database URL from environment variable with fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost/postgres"
)

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)
# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_database():
    with engine.connect() as cursor:
        # Create tables with all current columns
        cursor.execute(text("""
            CREATE TABLE branches (
                id serial PRIMARY KEY,
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
        """))
        
        cursor.execute(text("""
            CREATE TABLE branch_funds (
                id serial PRIMARY KEY,
                branch_id INTEGER,
                amount REAL,
                type TEXT CHECK(type IN ('allocation', 'deduction', 'refund')),
                currency TEXT DEFAULT 'SYP',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
            )
        """))
        
        cursor.execute(text("""
            CREATE TABLE users (
                id serial PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('director', 'branch_manager', 'employee')),
                branch_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
            )
        """))
        
        cursor.execute(text("""
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
        """))
        
        cursor.execute(text("""
            CREATE TABLE notifications (
                id serial PRIMARY KEY,
                transaction_id TEXT,
                recipient_phone TEXT,
                message TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
            )
        """))
        
        # Add indexes for better performance
        cursor.execute(text("CREATE INDEX idx_transactions_id ON transactions(id);"))
        cursor.execute(text("CREATE INDEX idx_transactions_sender ON transactions(sender);"))
        cursor.execute(text("CREATE INDEX idx_transactions_receiver ON transactions(receiver);"))
        cursor.execute(text("CREATE INDEX idx_transactions_status ON transactions(status);"))
        cursor.execute(text("CREATE INDEX idx_transaction_date ON transactions(date);"))
        cursor.execute(text("CREATE INDEX idx_transaction_branch ON transactions(branch_id);"))
        cursor.execute(text("CREATE INDEX idx_transaction_currency ON transactions(currency);"))
        cursor.execute(text("CREATE INDEX idx_transaction_dates ON transactions(date, branch_id, currency, status);"))
        cursor.execute(text("CREATE INDEX idx_transaction_destination ON transactions(destination_branch_id);"))
        cursor.execute(text("CREATE INDEX idx_transaction_employee ON transactions(employee_id);"))
        cursor.execute(text("CREATE INDEX idx_transaction_received ON transactions(received_by);"))
        cursor.execute(text("CREATE INDEX idx_transaction_composite ON transactions(branch_id, status, date);"))
        
        cursor.commit()
        print("New database created with current schema")


if __name__ == "__main__":
    reset_database()