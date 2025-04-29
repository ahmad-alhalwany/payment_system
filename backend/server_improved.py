from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import User, Branch, Base, BranchFund
from pydantic import BaseModel, validator, ValidationError
import uuid
from datetime import datetime, timedelta
from security import hash_password, verify_password, create_jwt_token, SECRET_KEY, ALGORITHM
import sqlite3
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import sqlalchemy.exc

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./transactions.db"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables if they don't exist
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Data models
class Transaction(BaseModel):
    sender: str
    sender_mobile: str
    sender_governorate: str
    sender_location: str
    sender_id: Optional[str] = None
    sender_address: Optional[str] = None
    
    receiver: str
    receiver_mobile: str
    receiver_governorate: str
    receiver_location: Optional[str] = None
    receiver_id: Optional[str] = None
    receiver_address: Optional[str] = None
    
    amount: float
    base_amount: float
    benefited_amount: float
    tax_rate: float
    tax_amount: float
    currency: str = "ليرة سورية"
    
    message: str
    employee_name: str
    branch_governorate: str
    destination_branch_id: int
    branch_id: Optional[int] = None

class TransactionReceived(BaseModel):
    transaction_id: str
    is_received: bool
    receiver: str
    receiver_mobile: str
    receiver_id: str
    receiver_address: str
    receiver_governorate: str

class TransactionStatus(BaseModel):
    transaction_id: str
    status: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    username: str
    new_password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    
class FundAllocation(BaseModel):
    amount: float
    type: str  # 'allocation' أو 'deduction'
    currency: str   # Added currency field with default value
    description: Optional[str] = None
    
class TransactionResponse(BaseModel):
    id: str
    sender: str
    receiver: str
    amount: float
    currency: str
    status: str
    date: str
    branch_id: int
    destination_branch_id: int
    employee_name: str
    sending_branch_name: str  # إضافة هذا الحقل
    destination_branch_name: str  # إضافة هذا الحقل
    branch_governorate: str  
    
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "employee"
    branch_id: Optional[int] = None  
    
class BranchUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    governorate: Optional[str] = None
    status: Optional[str] = None
    
class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None

    class Config:
        from_attributes = True 
        
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "employee"
    branch_id: Optional[int] = None
    
class BranchCreate(BaseModel):
    branch_id: str
    name: str
    location: str
    governorate: str     
        
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        role: str = payload.get("role")
        branch_id: int = payload.get("branch_id")
        user_id: int = payload.get("user_id")
        
        if username is None or role is None:
            raise credentials_exception
            
        return {"username": username, "role": role, "branch_id": branch_id, "user_id": user_id}
    except JWTError:
        raise credentials_exception        
        

def save_to_db(transaction, branch_id=None, employee_id=None):
    transaction_id = str(uuid.uuid4())
    transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()
    
    try:
        # Start transaction with immediate lock
        cursor.execute("BEGIN IMMEDIATE")
        
        # Check if this is a System Manager transfer (branch_id = 0)
        is_system_manager = branch_id == 0 or transaction.employee_name == "System Manager" or transaction.employee_name == "system_manager"
        
        if is_system_manager:
            # System Manager has unlimited funds - skip all allocation checks
            print("System Manager transaction detected - bypassing fund checks")
            # Just verify destination branch exists
            cursor.execute("""
                SELECT id, allocated_amount_syp, allocated_amount_usd FROM branches 
                WHERE id = ?
            """, (transaction.destination_branch_id,))
            destination_branch = cursor.fetchone()
            
            if not destination_branch:
                raise HTTPException(status_code=404, detail="Destination branch not found")
        else:
            # 1. Check sending branch allocation for regular transfers based on currency
            if transaction.currency == "SYP":
                cursor.execute("""
                    SELECT allocated_amount_syp FROM branches 
                    WHERE id = ?
                """, (branch_id,))
                branch = cursor.fetchone()
                
                if not branch:
                    raise HTTPException(status_code=404, detail="Sending branch not found")
                    
                allocated = branch[0]
                
                if allocated < transaction.amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient allocated funds in SYP. Available: {allocated} SYP"
                    )
            elif transaction.currency == "USD":
                cursor.execute("""
                    SELECT allocated_amount_usd FROM branches 
                    WHERE id = ?
                """, (branch_id,))
                branch = cursor.fetchone()
                
                if not branch:
                    raise HTTPException(status_code=404, detail="Sending branch not found")
                    
                allocated = branch[0]
                
                if allocated < transaction.amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient allocated funds in USD. Available: {allocated} USD"
                    )
            else:
                # Default to SYP for other currencies for backward compatibility
                cursor.execute("""
                    SELECT allocated_amount_syp FROM branches 
                    WHERE id = ?
                """, (branch_id,))
                branch = cursor.fetchone()
                
                if not branch:
                    raise HTTPException(status_code=404, detail="Sending branch not found")
                    
                allocated = branch[0]
                
                if allocated < transaction.amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient allocated funds. Available: {allocated} {transaction.currency}"
                    )
        
        # For non-system manager transactions, check if destination branch exists
        if not is_system_manager:
            cursor.execute("""
                SELECT id, allocated_amount_syp, allocated_amount_usd FROM branches 
                WHERE id = ?
            """, (transaction.destination_branch_id,))
            destination_branch = cursor.fetchone()
            
            if not destination_branch:
                raise HTTPException(status_code=404, detail="Destination branch not found")
        
        # 3. Deduct from sending branch allocation (skip for System Manager)
        if not is_system_manager:
            if transaction.currency == "SYP":
                new_allocated = allocated - transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_allocated, new_allocated, branch_id))
            elif transaction.currency == "USD":
                new_allocated = allocated - transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_usd = ? 
                    WHERE id = ?
                """, (new_allocated, branch_id))
            else:
                # Default to SYP for other currencies for backward compatibility
                new_allocated = allocated - transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_allocated, new_allocated, branch_id))
            
            # 4. Increase destination branch allocation for regular transfers
            if transaction.currency == "SYP":
                new_destination_allocated = destination_branch[1] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_destination_allocated, new_destination_allocated, transaction.destination_branch_id))
            elif transaction.currency == "USD":
                new_destination_allocated = destination_branch[2] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_usd = ? 
                    WHERE id = ?
                """, (new_destination_allocated, transaction.destination_branch_id))
            else:
                # Default to SYP for other currencies for backward compatibility
                new_destination_allocated = destination_branch[1] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_destination_allocated, new_destination_allocated, transaction.destination_branch_id))
        else:
            # For System Manager, just increase destination branch allocation
            # First get the destination branch details
            cursor.execute("""
                SELECT id, allocated_amount_syp, allocated_amount_usd FROM branches 
                WHERE id = ?
            """, (transaction.destination_branch_id,))
            destination_branch = cursor.fetchone()
            
            if not destination_branch:
                raise HTTPException(status_code=404, detail="Destination branch not found")
                
            # Increase destination branch allocation based on currency
            if transaction.currency == "SYP":
                new_destination_allocated = destination_branch[1] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_destination_allocated, new_destination_allocated, transaction.destination_branch_id))
            elif transaction.currency == "USD":
                new_destination_allocated = destination_branch[2] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_usd = ? 
                    WHERE id = ?
                """, (new_destination_allocated, transaction.destination_branch_id))
            else:
                # Default to SYP for other currencies for backward compatibility
                new_destination_allocated = destination_branch[1] + transaction.amount
                cursor.execute("""
                    UPDATE branches 
                    SET allocated_amount_syp = ?, allocated_amount = ? 
                    WHERE id = ?
                """, (new_destination_allocated, new_destination_allocated, transaction.destination_branch_id))
        
        # Insert transaction
        cursor.execute("""
            INSERT INTO transactions (
                id, sender, sender_mobile, sender_governorate, sender_location, 
                sender_id, sender_address, receiver, receiver_mobile, 
                receiver_governorate, receiver_location, receiver_id, receiver_address,
                amount, base_amount, benefited_amount, tax_rate, tax_amount, currency,
                message, branch_id, destination_branch_id, employee_id, employee_name, 
                branch_governorate, status, is_received, type, received_by, received_at,
                date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, transaction.sender, transaction.sender_mobile,
            transaction.sender_governorate, transaction.sender_location,
            transaction.sender_id or "", transaction.sender_address or "",
            transaction.receiver, transaction.receiver_mobile,
            transaction.receiver_governorate, transaction.receiver_location or "",
            transaction.receiver_id or "", transaction.receiver_address or "",
            transaction.amount, transaction.base_amount, transaction.benefited_amount,
            transaction.tax_rate, transaction.tax_amount, transaction.currency,
            transaction.message or "", branch_id, transaction.destination_branch_id,
            employee_id, transaction.employee_name,
            transaction.branch_governorate, "processing", False, "transfer",
            None, None, transaction_date
        ))
        
        # Record fund deduction for sending branch (skip for System Manager)
        if not is_system_manager:
            cursor.execute("""
                INSERT INTO branch_funds (
                    branch_id, amount, type, currency, description
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                branch_id,
                transaction.amount,
                "deduction",
                transaction.currency,
                f"Transaction {transaction_id} deduction"
            ))
        
        # Record fund allocation for receiving branch
        cursor.execute("""
            INSERT INTO branch_funds (
                branch_id, amount, type, currency, description
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            transaction.destination_branch_id,
            transaction.amount,
            "allocation",
            transaction.currency,
            f"Transaction {transaction_id} allocation from {is_system_manager and 'System Manager' or f'branch {branch_id}'}"
        ))
        
        # Create notification
        notification_message = f"Hello {transaction.receiver}, you have a new money transfer of {transaction.amount} {transaction.currency} waiting. Please visit your nearest branch to collect it."
        cursor.execute("""
            INSERT INTO notifications (transaction_id, recipient_phone, message, status)
            VALUES (?, ?, ?, ?)
        """, (transaction_id, transaction.receiver_mobile, notification_message, "pending"))
        
        conn.commit()
        return transaction_id
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"SQLite error in save_to_db: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error in save_to_db: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    finally:
        conn.close()
        
@app.delete("/branches/{branch_id}/allocations/")
def reset_allocations(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    currency: Optional[str] = None
):
    if current_user["role"] != "director":
        raise HTTPException(status_code=403, detail="Director access required")
    
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # If currency is specified, reset only that currency
    if currency == "SYP":
        # Record the reset in fund history
        if branch.allocated_amount_syp > 0:
            fund_record = BranchFund(
                branch_id=branch_id,
                amount=-branch.allocated_amount_syp,
                type="deduction",
                currency="SYP",
                description="حذف الرصيد بالليرة السورية بالكامل بواسطة المدير"
            )
            db.add(fund_record)
        
        branch.allocated_amount_syp = 0.0
        # Update legacy field for backward compatibility
        branch.allocated_amount = 0.0
        db.commit()
        
        return {"status": "success", "message": "SYP allocations reset"}
    
    elif currency == "USD":
        # Record the reset in fund history
        if branch.allocated_amount_usd > 0:
            fund_record = BranchFund(
                branch_id=branch_id,
                amount=-branch.allocated_amount_usd,
                type="deduction",
                currency="USD",
                description="حذف الرصيد بالدولار الأمريكي بالكامل بواسطة المدير"
            )
            db.add(fund_record)
        
        branch.allocated_amount_usd = 0.0
        db.commit()
        
        return {"status": "success", "message": "USD allocations reset"}
    
    # If no currency specified, reset both
    else:
        # Record the reset in fund history for SYP
        if branch.allocated_amount_syp > 0:
            fund_record_syp = BranchFund(
                branch_id=branch_id,
                amount=-branch.allocated_amount_syp,
                type="deduction",
                currency="SYP",
                description="حذف الرصيد بالليرة السورية بالكامل بواسطة المدير"
            )
            db.add(fund_record_syp)
        
        # Record the reset in fund history for USD
        if branch.allocated_amount_usd > 0:
            fund_record_usd = BranchFund(
                branch_id=branch_id,
                amount=-branch.allocated_amount_usd,
                type="deduction",
                currency="USD",
                description="حذف الرصيد بالدولار الأمريكي بالكامل بواسطة المدير"
            )
            db.add(fund_record_usd)
        
        branch.allocated_amount_syp = 0.0
        branch.allocated_amount_usd = 0.0
        # Update legacy field for backward compatibility
        branch.allocated_amount = 0.0
        db.commit()
        
        return {"status": "success", "message": "All allocations reset"}
    
@app.put("/branches/{branch_id}")
def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "director":
        raise HTTPException(status_code=403, detail="Director access required")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    update_data = branch_data.dict(exclude_unset=True)
    
    # Update branch fields
    for field, value in update_data.items():
        setattr(branch, field, value)

    try:
        db.commit()
        db.refresh(branch)
        return {
            "status": "success",
            "branch": {
                "id": branch.id,
                "branch_id": branch.branch_id,
                "name": branch.name,
                "location": branch.location,
                "governorate": branch.governorate,
                "status": branch.status
            }
        }
    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Branch ID or name already exists")
    
@app.get("/customers/")
def get_customers(
    name: Optional[str] = None,
    mobile: Optional[str] = None,
    id_number: Optional[str] = None,
    governorate: Optional[str] = None,
    user_type: Optional[str] = None,  # 'sender' or 'receiver'
    db: Session = Depends(get_db)
):
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    base_query = """
        SELECT 
            sender as sender_name,
            sender_mobile,
            sender_governorate,
            sender_location,
            sender_id,
            receiver as receiver_name,
            receiver_mobile,
            receiver_governorate,
            receiver_location,
            receiver_id,
            ? as user_type
        FROM transactions
        WHERE 1=1
    """
    params = [user_type]

    conditions = []
    if name:
        conditions.append("(sender LIKE ? OR receiver LIKE ?)")
        params.extend([f"%{name}%", f"%{name}%"])
    if mobile:
        conditions.append("(sender_mobile LIKE ? OR receiver_mobile LIKE ?)")
        params.extend([f"%{mobile}%", f"%{mobile}%"])
    if id_number:
        conditions.append("(sender_id LIKE ? OR receiver_id LIKE ?)")
        params.extend([f"%{id_number}%", f"%{id_number}%"])
    if governorate:
        conditions.append("(sender_governorate LIKE ? OR receiver_governorate LIKE ?)")
        params.extend([f"%{governorate}%", f"%{governorate}%"])
    if user_type:
        if user_type == "sender":
            conditions.append("sender IS NOT NULL")
        elif user_type == "receiver":
            conditions.append("receiver IS NOT NULL")

    final_query = base_query
    if conditions:
        final_query += " AND " + " AND ".join(conditions)
    final_query += " GROUP BY sender_name, sender_mobile, sender_governorate, sender_location, sender_id, receiver_name, receiver_mobile, receiver_governorate, receiver_location, receiver_id"

    cursor.execute(final_query, params)
    customers = cursor.fetchall()
    conn.close()

    customer_list = []
    for cust in customers:
        customer_list.append({
            "sender_name": cust[0] or "",
            "sender_mobile": cust[1] or "",
            "sender_governorate": cust[2] or "",
            "sender_location": cust[3] or "",
            "sender_id": cust[4] or "",
            "receiver_name": cust[5] or "",
            "receiver_mobile": cust[6] or "",
            "receiver_governorate": cust[7] or "",
            "receiver_location": cust[8] or "",
            "receiver_id": cust[9] or "",
            "user_type": cust[10] or ""
        })
    return {"customers": customer_list}

@app.get("/check-initialization/")
def check_initialization(db: Session = Depends(get_db)):
    admin_exists = db.query(User).filter(User.role == "director").first()
    return {"is_initialized": admin_exists is not None}

@app.post("/initialize-system/")
def initialize_system(user: UserCreate, db: Session = Depends(get_db)):
    # Check if any admin exists
    if db.query(User).filter(User.role == "director").first():
        raise HTTPException(status_code=400, detail="النظام مهيأ مسبقاً")

    # Create admin user
    hashed_password = hash_password(user.password)
    db_user = User(
        username=user.username,
        password=hashed_password,
        role="director",
        branch_id=1,  # Link to default branch
        created_at=datetime.now()
    )
    db.add(db_user)

    # Create default branch if not exists
    if not db.query(Branch).filter(Branch.id == 1).first():
        db_branch = Branch(
            branch_id="MAIN",
            name="الفرع الرئيسي",
            location="المقر المركزي",
            governorate="المركزية",
            created_at=datetime.now()
        )
        db.add(db_branch)

    db.commit()
    return {"status": "success", "message": "تم إنشاء مدير النظام بنجاح"} 

@app.post("/branches/{branch_id}/allocate-funds/")
def allocate_funds(
    branch_id: int, 
    allocation: FundAllocation,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "director":
        raise HTTPException(status_code=403, detail="Director access required")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Validate currency input
    currency = allocation.currency.upper()  # Normalize to uppercase
    if currency not in ["SYP", "USD"]:
        raise HTTPException(status_code=400, 
                          detail="العملة غير مدعومة. الرجاء استخدام SYP أو USD")

    # Handle SYP operations
    if currency == "SYP":
        if allocation.type == 'deduction':
            if branch.allocated_amount_syp < allocation.amount:
                raise HTTPException(
                    status_code=400,
                    detail="رصيد الفرع بالليرة السورية غير كافي للخصم"
                )
            branch.allocated_amount_syp -= allocation.amount
        else:
            branch.allocated_amount_syp += allocation.amount
        
        # Update legacy field explicitly
        branch.allocated_amount = branch.allocated_amount_syp

    # Handle USD operations
    elif currency == "USD":
        if allocation.type == 'deduction':
            if branch.allocated_amount_usd < allocation.amount:
                raise HTTPException(
                    status_code=400,
                    detail="رصيد الفرع بالدولار الأمريكي غير كافي للخصم"
                )
            branch.allocated_amount_usd -= allocation.amount
        else:
            branch.allocated_amount_usd += allocation.amount

    # Create audit record with precise values
    fund_record = BranchFund(
        branch_id=branch_id,
        amount=allocation.amount * (1 if allocation.type == 'allocation' else -1),
        type=allocation.type,
        currency=currency,
        description=(
            allocation.description or 
            f"{'إيداع' if allocation.type == 'allocation' else 'خصم'} "
            f"بواسطة {current_user['username']} ({currency})"
        )
    )
    
    try:
        db.add(fund_record)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"فشل في حفظ العملية: {str(e)}"
        )

    return {
        "status": "success",
        "new_allocated_syp": branch.allocated_amount_syp,
        "new_allocated_usd": branch.allocated_amount_usd,
        "currency": currency
    }

@app.get("/branches/{branch_id}/funds-history")
def get_funds_history(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Authorization
    if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    history = db.query(BranchFund).filter(
        BranchFund.branch_id == branch_id
    ).order_by(BranchFund.created_at.desc()).all()

    return [{
        "date": record.created_at.strftime("%Y-%m-%d") if record.created_at else "غير معروف",
        "type": record.type,
        "amount": record.amount,
        "currency": record.currency,  # إضافة حقل العملة
        "description": record.description
    } for record in history]
    
@app.post("/send-money/")
async def send_money(transaction: Transaction, current_user: dict = Depends(get_current_user)):
    branch_id = current_user.get("branch_id")
    employee_id = current_user.get("user_id")
    
    transaction_id = save_to_db(transaction, branch_id, employee_id)
    # Remove the receipt generation
    return {"status": "success", "message": "Transaction saved!", "transaction_id": transaction_id}

@app.post("/transactions/", status_code=201)
async def create_transaction(transaction: Transaction, current_user: dict = Depends(get_current_user)):
    try:
        # Validate amounts
        if transaction.amount <= 0:
            raise HTTPException(status_code=400, detail="المبلغ يجب أن يكون أكبر من صفر")
        
        if transaction.base_amount < 0 or transaction.benefited_amount < 0:
            raise HTTPException(status_code=400, detail="المبالغ لا يمكن أن تكون سالبة")
        
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Get branch information
        branch_id = transaction.branch_id or current_user.get("branch_id")
        employee_id = current_user.get("user_id")
        
        # Create transaction record
        transaction_data = {
            "id": transaction_id,
            "sender": transaction.sender,
            "sender_mobile": transaction.sender_mobile,
            "sender_governorate": transaction.sender_governorate,
            "sender_location": transaction.sender_location,
            "sender_id": transaction.sender_id or "",
            "sender_address": transaction.sender_address or "",
            
            "receiver": transaction.receiver,
            "receiver_mobile": transaction.receiver_mobile,
            "receiver_governorate": transaction.receiver_governorate,
            "receiver_location": transaction.receiver_location or "",
            "receiver_id": transaction.receiver_id or "",
            "receiver_address": transaction.receiver_address or "",
            
            "amount": transaction.amount,
            "base_amount": transaction.base_amount,
            "benefited_amount": transaction.benefited_amount,
            "tax_rate": transaction.tax_rate,
            "tax_amount": transaction.tax_amount,
            "currency": transaction.currency,
            
            "message": transaction.message or "",
            "employee_name": transaction.employee_name,
            "branch_governorate": transaction.branch_governorate,
            "branch_id": branch_id,
            "destination_branch_id": transaction.destination_branch_id,
            "employee_id": employee_id,
            "status": "processing",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_received": False
        }
        
        # Save to database using the save_to_db function
        try:
            transaction_id = save_to_db(transaction, branch_id, employee_id)
            return {
                "status": "success",
                "message": "تم إنشاء التحويل بنجاح",
                "transaction_id": transaction_id
            }
        except Exception as e:
            print(f"Error saving transaction: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in create_transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class TransactionReceived(BaseModel):
    transaction_id: str
    receiver: str
    receiver_mobile: str
    receiver_id: str
    receiver_address: str
    receiver_governorate: str

@app.post("/mark-transaction-received/")
def mark_transaction_received(received_data: TransactionReceived, current_user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        
        # Verify transaction exists and belongs to current branch
        cursor.execute("""
            SELECT id FROM transactions 
            WHERE id = ? AND branch_id = ?
        """, (received_data.transaction_id, current_user["branch_id"]))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, 
                             detail="Transaction not found or not authorized for this branch")
        
        # Update transaction
        update_query = """
            UPDATE transactions 
            SET is_received = TRUE,
                received_by = ?,
                received_at = ?,
                receiver = ?,
                receiver_mobile = ?,
                receiver_id = ?,
                receiver_address = ?,
                receiver_governorate = ?,
                status = 'completed'
            WHERE id = ?
        """
        
        cursor.execute(update_query, (
            current_user["user_id"],
            datetime.now().isoformat(),
            received_data.receiver,
            received_data.receiver_mobile,
            received_data.receiver_id,
            received_data.receiver_address,
            received_data.receiver_governorate,
            received_data.transaction_id
        ))
        
        # Update notification
        cursor.execute("""
            UPDATE notifications 
            SET status = 'sent' 
            WHERE transaction_id = ?
        """, (received_data.transaction_id,))
        
        conn.commit()
        return {"status": "success", "message": "Transaction marked as received"}
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        # Log the full error for debugging
        print(f"Database error details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="حدث خطأ في قاعدة البيانات. الرجاء التحقق من سجلات الخادم للحصول على التفاصيل."
        )
    finally:
        if conn:
            conn.close()

@app.post("/login/")
async def login(user: LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first() 
    if db_user and verify_password(user.password, db_user.password):
        # Create token with expiration time (24 hours)
        access_token_expires = timedelta(hours=24)
        expires = datetime.utcnow() + access_token_expires
        
        # Include user role and branch_id in the token
        token_data = {
            "username": db_user.username,
            "role": db_user.role,
            "branch_id": db_user.branch_id,
            "user_id": db_user.id,
            "exp": expires
        }
        
        access_token = create_jwt_token(token_data)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": db_user.role, 
            "username": db_user.username,
            "branch_id": db_user.branch_id,
            "user_id": db_user.id,
            "token": access_token  # Adding token directly for frontend compatibility
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/register/")
def register_user(user: UserCreate, token: str = Depends(oauth2_scheme)):
    try:
        # Try to decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        role = payload.get("role")
        branch_id = payload.get("branch_id")
        user_id = payload.get("user_id")
        
        # Check if user has permission to create users
        if role not in ["director", "branch_manager"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
        # Branch managers can only create employees for their own branch
        if role == "branch_manager" and (user.role != "employee" or user.branch_id != branch_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch managers can only create employees for their own branch")
        
        db = SessionLocal()
        try:
            # Check if username already exists
            existing_user = db.query(User).filter(User.username == user.username).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already registered")
            
            # Check if branch exists if branch_id is provided
            if user.branch_id:
                branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
                if not branch:
                    raise HTTPException(status_code=404, detail="Branch not found")
            
            # Create new user
            hashed_password = hash_password(user.password)
            db_user = User(
                username=user.username,
                password=hashed_password,
                role=user.role,
                branch_id=user.branch_id,
                created_at=datetime.now()
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            return {"id": db_user.id, "username": db_user.username, "role": db_user.role, "branch_id": db_user.branch_id}
        finally:
            db.close()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Check if user has permission to create users
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Branch managers can only create employees for their own branch
    if current_user["role"] == "branch_manager" and (user.role != "employee" or user.branch_id != current_user["branch_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch managers can only create employees")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if branch exists if branch_id is provided
    if user.branch_id:
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
    
    # Create new user
    hashed_password = hash_password(user.password)
    db_user = User(
        username=user.username,
        password=hashed_password,
        role=user.role,
        branch_id=user.branch_id,
        created_at=datetime.now()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"id": db_user.id, "username": db_user.username, "role": db_user.role, "branch_id": db_user.branch_id}

@app.post("/branches/")
def create_branch(branch: BranchCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Only directors can create branches
    if current_user["role"] != "director":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    try:
        # Check if branch_id already exists
        existing_branch = db.query(Branch).filter(Branch.branch_id == branch.branch_id).first()
        if existing_branch:
            raise HTTPException(status_code=400, detail="Branch ID already registered")
        
        # Create new branch
        db_branch = Branch(
            branch_id=branch.branch_id,
            name=branch.name,
            location=branch.location,
            governorate=branch.governorate,
            created_at=datetime.now()
        )
        
        db.add(db_branch)
        db.commit()
        db.refresh(db_branch)
        
        return {"id": db_branch.id, "branch_id": db_branch.branch_id, "name": db_branch.name, "location": db_branch.location, "governorate": db_branch.governorate}
    
    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        # Handle specific integrity errors with user-friendly messages
        if "UNIQUE constraint failed: branches.name" in str(e):
            raise HTTPException(status_code=400, detail="A branch with this name already exists. Please use a different name.")
        elif "UNIQUE constraint failed: branches.branch_id" in str(e):
            raise HTTPException(status_code=400, detail="A branch with this ID already exists. Please use a different branch ID.")
        else:
            # For other integrity errors
            raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")

@app.get("/branches/")
def get_branches(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        # Attempt to get authenticated user
        user_role = current_user["role"]
        user_branch_id = current_user.get("branch_id")
    except:
        # Public access with limited information
        branches = db.query(Branch).all()
        return {
            "branches": [{
                "id": branch.id,
                "branch_id": branch.branch_id,
                "name": branch.name,
                "location": branch.location,
                "governorate": branch.governorate,
                "created_at": branch.created_at.strftime("%Y-%m-%d %H:%M:%S") if branch.created_at else None
            } for branch in branches]
        }
    
    # Authorized access
    branches = db.query(Branch).all()
    
    branch_list = []
    for branch in branches:
        branch_data = {
            "id": branch.id,
            "branch_id": branch.branch_id,
            "name": branch.name,
            "location": branch.location,
            "governorate": branch.governorate,
            "created_at": branch.created_at.strftime("%Y-%m-%d %H:%M:%S") if branch.created_at else None,
            "allocated_amount_syp": branch.allocated_amount_syp,
            "allocated_amount_usd": branch.allocated_amount_usd,
            "allocated_amount": branch.allocated_amount
        }
        
        # Add financial info based on role
        if user_role == "director":
            branch_data.update({
                "allocated_amount": branch.allocated_amount,
                "current_balance": branch.allocated_amount  # You might want to calculate this differently
            })
        elif user_role == "branch_manager" and branch.id == user_branch_id:
            branch_data.update({
                "allocated_amount": branch.allocated_amount,
                "current_balance": branch.allocated_amount
            })
        
        branch_list.append(branch_data)
    
    return {"branches": branch_list}

@app.get("/branches/{branch_id}")
def get_branch(branch_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Special handling for System Manager branch (ID 0)
    if branch_id == 0:
        # Return a virtual branch with very high (but not infinite) funds for the System Manager
        return {
            "id": 0,
            "branch_id": "MAIN",
            "name": "Main Branch",
            "location": "System",
            "governorate": "System Manager",
            "allocated_amount": 9999999999.0,  # Very high amount instead of infinity
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_sent": 0.0,
            "total_received": 0.0,
            "total_allocated": 9999999999.0,  # Very high amount instead of infinity
            "available_balance": 9999999999.0,  # Very high amount instead of infinity
            "financial_stats": {
                "available_balance": 9999999999.0,  # Very high amount instead of infinity
                "total_allocated": 9999999999.0,  # Very high amount instead of infinity
                "total_sent": 0.0,
                "total_received": 0.0
            }
        }
    
    # Authorization check
    if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this branch")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Initialize default values
    total_sent = 0.0
    total_received = 0.0
    total_allocated = 0.0

    try:
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()

        # Get total sent transactions amount (fixed COALESCE syntax)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0)
            FROM transactions 
            WHERE branch_id = ? AND status = 'completed'
        """, (branch_id,))
        total_sent = cursor.fetchone()[0] or 0.0

        # Get total received transactions amount (fixed COALESCE syntax)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0)
            FROM transactions 
            WHERE destination_branch_id = ? AND status = 'completed'
        """, (branch_id,))
        total_received = cursor.fetchone()[0] or 0.0

        # Get allocation history (added COALESCE)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0)
            FROM branch_funds 
            WHERE branch_id = ? AND type = 'allocation'
        """, (branch_id,))
        total_allocated = cursor.fetchone()[0] or 0.0

    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

    return {
        "id": branch.id,
        "branch_id": branch.branch_id,
        "name": branch.name,
        "location": branch.location,
        "governorate": branch.governorate,
        "allocated_amount": branch.allocated_amount,
        "allocated_amount_syp": branch.allocated_amount_syp,
        "allocated_amount_usd": branch.allocated_amount_usd,
        "financial_stats": {
            "total_allocated": total_allocated,
            "available_balance": branch.allocated_amount,
            "available_balance_syp": branch.allocated_amount_syp,
            "available_balance_usd": branch.allocated_amount_usd,
            "total_sent": total_sent,
            "total_received": total_received
        },
        "created_at": branch.created_at.strftime("%Y-%m-%d %H:%M:%S") if branch.created_at else None
    }
@app.get("/users/")
def get_users(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Only directors and branch managers can view users
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    query = db.query(User)
    
    # Branch managers can only see users in their branch
    if current_user["role"] == "branch_manager":
        query = query.filter(User.branch_id == current_user["branch_id"])
    
    users = query.all()
    
    # Get branch names for each user
    user_list = []
    for user in users:
        branch_name = None
        if user.branch_id:
            branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
            if branch:
                branch_name = branch.name
        
        user_list.append({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "branch_id": user.branch_id,
            "branch_name": branch_name,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
        })
    
    return {"users": user_list}

@app.get("/employees/")
def get_employees(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), branch_id: Optional[int] = None):
    # Only directors and branch managers can view employees
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    query = db.query(User)
    
    # Filter by role to only include employees
    query = query.filter(User.role == "employee")
    
    # Filter by branch_id if provided
    if branch_id:
        # Branch managers can only view employees in their own branch
        if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view employees in your branch")
        query = query.filter(User.branch_id == branch_id)
    # If no branch_id provided but user is branch manager, only show their branch
    elif current_user["role"] == "branch_manager":
        query = query.filter(User.branch_id == current_user["branch_id"])
    
    employees = query.all()
    
    # Get branch names for each employee
    employee_list = []
    for employee in employees:
        branch_name = None
        if employee.branch_id:
            branch = db.query(Branch).filter(Branch.id == employee.branch_id).first()
            if branch:
                branch_name = branch.name
        
        employee_list.append({
            "id": employee.id,
            "username": employee.username,
            "role": employee.role,
            "branch_id": employee.branch_id,
            "branch_name": branch_name,
            "created_at": employee.created_at.strftime("%Y-%m-%d %H:%M:%S") if employee.created_at else None
        })
    
    return employee_list

@app.get("/branches/{branch_id}/employees/")
def get_branch_employees(branch_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Check if user has permission to view branch employees
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Branch managers can only view employees in their own branch
    if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view employees in your branch")
    
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Get employees for the branch
    employees = db.query(User).filter(User.branch_id == branch_id).all()
    
    employee_list = []
    for employee in employees:
        employee_list.append({
            "id": employee.id,
            "username": employee.username,
            "role": employee.role,
            "branch_id": employee.branch_id,
            "created_at": employee.created_at.strftime("%Y-%m-%d %H:%M:%S") if employee.created_at else None
        })
    
    return employee_list

@app.get("/transactions/")
def get_transactions(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user),
    branch_id: Optional[int] = None,
    filter_type: Optional[str] = None,
    destination_branch_id: Optional[int] = None,
    limit: Optional[int] = None,
    id: Optional[str] = None,
    sender: Optional[str] = None,
    receiver: Optional[str] = None,
    status: Optional[str] = None,
    date: Optional[str] = None
):
    conn = sqlite3.connect("transactions.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT t.*, 
               b1.name as sending_branch_name,
               b2.name as destination_branch_name
        FROM transactions t
        LEFT JOIN branches b1 ON t.branch_id = b1.id
        LEFT JOIN branches b2 ON t.destination_branch_id = b2.id
    """
    params = []
    where_clauses = []
    
    # Base security filtering
    if current_user["role"] == "employee":
        where_clauses.append("(t.employee_id = ? OR t.destination_branch_id = ?)")
        params.extend([current_user["user_id"], current_user["branch_id"]])
    elif current_user["role"] == "branch_manager":
        # Show both incoming and outgoing transactions for the branch
        where_clauses.append("(t.branch_id = ? OR t.destination_branch_id = ?)")
        params.extend([current_user["branch_id"], current_user["branch_id"]])

    # Additional filters
    if branch_id:
        where_clauses.append("t.branch_id = ?")
        params.append(branch_id)
        
    if destination_branch_id:
        where_clauses.append("t.destination_branch_id = ?")
        params.append(destination_branch_id)

    # New: Specific search filters
    if id:
        where_clauses.append("t.id LIKE ?")
        params.append(f"%{id}%")
    if sender:
        where_clauses.append("t.sender LIKE ?")
        params.append(f"%{sender}%")
    if receiver:
        where_clauses.append("t.receiver LIKE ?")
        params.append(f"%{receiver}%")
    if status:
        where_clauses.append("t.status = ?")
        params.append(status)
    if date:
        where_clauses.append("t.date LIKE ?")
        params.append(f"%{date}%")

    # Governorate filtering
    if filter_type:
        cursor.execute("SELECT governorate FROM branches WHERE id = ?", 
                      (current_user["branch_id"],))
        branch_gov = cursor.fetchone()["governorate"]
        
        if filter_type == "incoming":
            where_clauses.append("t.receiver_governorate = ?")
            params.append(branch_gov)
        elif filter_type == "outgoing":
            where_clauses.append("t.sender_governorate = ?")
            params.append(branch_gov)
        elif filter_type == "branch_related":
            where_clauses.append("(t.sender_governorate = ? OR t.receiver_governorate = ?)")
            params.extend([branch_gov, branch_gov])

    # Build query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY t.date DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    try:
        cursor.execute(query, params)
        transactions = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

    return {"transactions": transactions}

@app.get("/reports/transactions/")
def get_transactions_report(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    date_from: str = None,
    date_to: str = None,
    branch_id: int = None,
    page: int = 1,
    per_page: int = 10
):
    # Authorization check
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Branch managers can only access their branch's data
    if current_user["role"] == "branch_manager":
        branch_id = current_user["branch_id"]

    offset = (page - 1) * per_page

    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    # Base query
    query = """
        SELECT * FROM transactions 
        WHERE 1=1
    """
    params = []

    # Add branch filter
    if branch_id:
        query += " AND branch_id = ?"
        params.append(branch_id)

    # Add date filters
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    # Count total records
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    cursor.execute(query, params)
    transactions = cursor.fetchall()
    
    conn.close()

    return {
        "items": transactions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Authorization check
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Find the user
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent branch managers from modifying other branches
    if current_user["role"] == "branch_manager":
        if db_user.branch_id != current_user["branch_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify users from other branches"
            )
        
        # Prevent branch managers from creating other managers
        if user_data.role == "branch_manager":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create other branch managers"
            )

    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if key == "password" and value:
                setattr(db_user, key, hash_password(value))
            else:
                setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "role": db_user.role,
        "branch_id": db_user.branch_id
    }

@app.post("/update-transaction-status/")
def update_transaction_status(
    status_update: TransactionStatus, 
    current_user: dict = Depends(get_current_user)
):
    conn = None
    try:
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")  # Start transaction

        # Get transaction details including amount and branch
        cursor.execute("""
            SELECT branch_id, amount, status, destination_branch_id
            FROM transactions 
            WHERE id = ?
        """, (status_update.transaction_id,))
        transaction = cursor.fetchone()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        branch_id, amount, old_status, dest_branch_id = transaction
        new_status = status_update.status

        # Authorization check
        if current_user["role"] == "branch_manager":
            if branch_id != current_user["branch_id"] and dest_branch_id != current_user["branch_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to modify this transaction"
                )

        # Handle fund allocation changes
        if old_status == "processing" and new_status in ["cancelled", "rejected"]:
            # Refund the amount to the originating branch
            cursor.execute("""
                UPDATE branches
                SET allocated_amount = allocated_amount + ?
                WHERE id = ?
            """, (amount, branch_id))
            
            # Record fund refund
            cursor.execute("""
                INSERT INTO branch_funds (
                    branch_id, amount, type, description
                ) VALUES (?, ?, ?, ?)
            """, (
                branch_id,
                amount,
                "refund",
                f"Refund for {new_status} transaction {status_update.transaction_id}"
            ))

        elif new_status == "completed" and old_status != "completed":
            # Deduct from destination branch's allocation if needed
            # (Add this logic if completing transactions affects allocations)
            pass

        # Update transaction status
        cursor.execute("""
            UPDATE transactions 
            SET status = ?
            WHERE id = ?
        """, (new_status, status_update.transaction_id))

        # Update notification status
        notification_status = {
            "completed": "sent",
            "cancelled": "failed",
            "rejected": "failed",
            "processing": "pending",
            "pending": "pending"
        }.get(new_status, "pending")
        
        cursor.execute("""
            UPDATE notifications 
            SET status = ?
            WHERE transaction_id = ?
        """, (notification_status, status_update.transaction_id))

        conn.commit()
        return {"status": "success", "message": "Status updated with fund adjustment"}

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.post("/reset-password/")
def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Only directors and branch managers can reset passwords
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Find the user
    user = db.query(User).filter(User.username == reset_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Branch managers can only reset passwords for employees in their branch
    if current_user["role"] == "branch_manager" and (user.role != "employee" or user.branch_id != current_user["branch_id"]):
        raise HTTPException(status_code=403, detail="You can only reset passwords for employees in your branch")
    
    # Update password
    user.password = hash_password(reset_data.new_password)
    db.commit()
    
    return {"status": "success", "message": "Password reset successfully"}

@app.post("/change-password/")
def change_password(password_data: ChangePassword, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Find the user
    user = db.query(User).filter(User.username == current_user["username"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify old password
    if not verify_password(password_data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # Update password
    user.password = hash_password(password_data.new_password)
    db.commit()
    
    return {"status": "success", "message": "Password changed successfully"}

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Only directors and branch managers can delete users
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Directors can't be deleted
    if user.role == "director":
        raise HTTPException(status_code=403, detail="Directors cannot be deleted")
    
    # Branch managers can only delete employees in their branch
    if current_user["role"] == "branch_manager" and (user.role != "employee" or user.branch_id != current_user["branch_id"]):
        raise HTTPException(status_code=403, detail="You can only delete employees in your branch")
    
    # Delete the user
    db.delete(user)
    db.commit()
    
    return {"status": "success", "message": "User deleted successfully"}

@app.delete("/branches/{branch_id}/")
def delete_branch(branch_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Only directors can delete branches
    if current_user["role"] != "director":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Find the branch
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if there are users assigned to this branch
    users = db.query(User).filter(User.branch_id == branch_id).all()
    if users:
        raise HTTPException(status_code=400, detail="Cannot delete branch with assigned users")
    
    # Delete the branch
    db.delete(branch)
    db.commit()
    
    return {"status": "success", "message": "Branch deleted successfully"}

@app.get("/branches/stats/")
def get_branch_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Get all branches
    branches = db.query(Branch).all()
    
    # Get transaction stats for each branch
    branch_stats = []
    for branch in branches:
        # Get transaction count and total amount for the branch
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        
        # Transactions originating from this branch
        cursor.execute("""
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE branch_id = ?
        """, (branch.id,))
        outgoing = cursor.fetchone()
        
        # Transactions destined for this branch
        cursor.execute("""
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE destination_branch_id = ?
        """, (branch.id,))
        incoming = cursor.fetchone()
        
        conn.close()
        
        branch_stats.append({
            "id": branch.id,
            "name": branch.name,
            "transactions_count": (outgoing[0] or 0) + (incoming[0] or 0),
            "total_amount": (outgoing[1] or 0) + (incoming[1] or 0)
        })
    
    return {
        "total": len(branches),
        "active": len(branches),  # Assuming all branches are active
        "branches": branch_stats
    }

@app.get("/users/stats/")
def get_user_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Get total number of users
    total_users = db.query(User).count()
    
    # Get number of employees
    employees = db.query(User).filter(User.role == "employee").count()
    
    return {
        "total": total_users,
        "directors": db.query(User).filter(User.role == "director").count(),
        "branch_managers": db.query(User).filter(User.role == "branch_manager").count(),
        "employees": employees
    }

@app.get("/branches/{branch_id}/employees/stats/")
def get_branch_employees_stats(branch_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Check if user has permission to view branch employee stats
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Branch managers can only view stats for their own branch
    if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view stats for your branch")
    
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Get total number of employees in the branch
    total_employees = db.query(User).filter(User.branch_id == branch_id).count()
    
    return {
        "total": total_employees,
        "active": total_employees  # For now, all employees are considered active
    }

@app.get("/branches/{branch_id}/transactions/stats/")
def get_branch_transactions_stats(branch_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Check if user has permission to view branch transaction stats
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Branch managers can only view stats for their own branch
    if current_user["role"] == "branch_manager" and current_user["branch_id"] != branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view stats for your branch")
    
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()
    
    # Get total number of transactions for the branch
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE branch_id = ?", (branch_id,))
    total_transactions = cursor.fetchone()[0]
    
    # Get total amount of transactions for the branch
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE branch_id = ?", (branch_id,))
    total_amount = cursor.fetchone()[0] or 0
    
    # Get number of completed transactions
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE branch_id = ? AND status = 'completed'", (branch_id,))
    completed_transactions = cursor.fetchone()[0]
    
    # Get number of pending transactions
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE branch_id = ? AND status = 'processing'", (branch_id,))
    pending_transactions = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total": total_transactions,
        "total_amount": total_amount,
        "completed": completed_transactions,
        "pending": pending_transactions
    }

@app.get("/transactions/stats/")
def get_transactions_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()
    
    # Base query
    query = "SELECT COUNT(*), SUM(amount) FROM transactions"
    params = []
    
    # Branch managers can only see transactions from their branch
    if current_user["role"] == "branch_manager":
        query += " WHERE branch_id = ?"
        params.append(current_user["branch_id"])
    
    cursor.execute(query, params)
    result = cursor.fetchone()
    total_transactions = result[0] or 0
    total_amount = result[1] or 0
    
    # Get number of completed transactions
    completed_query = "SELECT COUNT(*) FROM transactions"
    completed_params = []
    
    if current_user["role"] == "branch_manager":
        completed_query += " WHERE branch_id = ? AND status = 'completed'"
        completed_params.append(current_user["branch_id"])
    else:
        completed_query += " WHERE status = 'completed'"
    
    cursor.execute(completed_query, completed_params)
    result = cursor.fetchone()
    completed_transactions = result[0] or 0
    
    # Get number of pending transactions
    pending_query = "SELECT COUNT(*) FROM transactions"
    pending_params = []
    
    if current_user["role"] == "branch_manager":
        pending_query += " WHERE branch_id = ? AND status = 'processing'"
        pending_params.append(current_user["branch_id"])
    else:
        pending_query += " WHERE status = 'processing'"
    
    cursor.execute(pending_query, pending_params)
    result = cursor.fetchone()
    pending_transactions = result[0] or 0
    
    conn.close()
    
    return {
        "total": total_transactions,
        "total_amount": total_amount,
        "completed": completed_transactions,
        "pending": pending_transactions
    }

@app.get("/transactions/{transaction_id}/")
def get_transaction(transaction_id: str, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("transactions.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get transaction
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    transaction = cursor.fetchone()
    
    if not transaction:
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Branch managers can only view transactions from their branch
    if current_user["role"] == "branch_manager" and transaction["branch_id"] != current_user["branch_id"]:
        conn.close()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view transactions from your branch")
    
    transaction_dict = dict(transaction)
    
    conn.close()
    
    return transaction_dict


@app.get("/users/")
def get_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    branch_id: Optional[int] = None  # إضافة بارامتر branch_id
):
    # التحقق من الصلاحيات
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    query = db.query(User)
    
    # إذا كان المستخدم مدير فرع، قصر النتائج على فرعه
    if current_user["role"] == "branch_manager":
        query = query.filter(User.branch_id == current_user["branch_id"])
    
    # تطبيق تصفية branch_id إذا تم تقديمه
    if branch_id:
        # المديرين الفرعيين لا يمكنهم طلب فروع أخرى
        if current_user["role"] == "branch_manager" and branch_id != current_user["branch_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your branch's employees")
        query = query.filter(User.branch_id == branch_id)
    
    # جلب المستخدمين مع أسماء الفروع
    users = query.all()
    user_list = []
    for user in users:
        branch_name = None
        if user.branch_id:
            branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
            branch_name = branch.name if branch else None
        
        user_list.append({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "branch_id": user.branch_id,
            "branch_name": branch_name,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
        })
    
    return {"users": user_list}

@app.get("/notifications/")
def get_notifications(current_user: dict = Depends(get_current_user)):
    """Get notifications for the current user's branch"""
    conn = sqlite3.connect("transactions.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Branch managers can only see notifications from their branch
    if current_user["role"] == "branch_manager":
        cursor.execute("""
            SELECT n.* FROM notifications n
            JOIN transactions t ON n.transaction_id = t.id
            WHERE t.branch_id = ?
            ORDER BY n.created_at DESC
        """, (current_user["branch_id"],))
    else:
        # Directors can see all notifications
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC")
    
    notifications = cursor.fetchall()
    
    notification_list = []
    for notification in notifications:
        notification_dict = dict(notification)
        notification_list.append(notification_dict)
    
    conn.close()
    
    return {"notifications": notification_list}

@app.get("/reports/{report_type}/")
def get_report(
    report_type: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    branch_id: Optional[int] = None
):
    # Only directors and branch managers can view reports
    if current_user["role"] not in ["director", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Branch managers can only view reports for their branch
    if current_user["role"] == "branch_manager":
        if branch_id and branch_id != current_user["branch_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view reports for your branch")
        branch_id = current_user["branch_id"]
    
    # Generate report based on type
    if report_type == "transactions":
        return generate_transactions_report(db, branch_id, date_from, date_to)
    elif report_type == "branches":
        return generate_branches_report(db)
    elif report_type == "employees":
        return generate_employees_report(db, branch_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")

def generate_transactions_report(db: Session, branch_id=None, date_from=None, date_to=None):
    conn = sqlite3.connect("transactions.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Base query
    query = "SELECT * FROM transactions"
    params = []
    
    # Apply filters
    where_clauses = []
    
    # Filter by branch_id
    if branch_id:
        where_clauses.append("branch_id = ?")
        params.append(branch_id)
    
    # Filter by date range
    if date_from:
        where_clauses.append("date >= ?")
        params.append(date_from)
    
    if date_to:
        where_clauses.append("date <= ?")
        params.append(date_to)
    
    # Combine where clauses
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    # Order by date (newest first)
    query += " ORDER BY date DESC"
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    
    transaction_list = []
    for transaction in transactions:
        transaction_dict = dict(transaction)
        transaction_list.append(transaction_dict)
    
    conn.close()
    
    return {"items": transaction_list}

def generate_branches_report(db: Session):
    branches = db.query(Branch).all()
    
    branch_list = []
    for branch in branches:
        branch_list.append({
            "id": branch.id,
            "branch_id": branch.branch_id,
            "name": branch.name,
            "location": branch.location,
            "governorate": branch.governorate,
            "created_at": branch.created_at.strftime("%Y-%m-%d %H:%M:%S") if branch.created_at else None,
            "status": "active"  # All branches are considered active for now
        })
    
    return {"items": branch_list}

def generate_employees_report(db: Session, branch_id):
    query = db.query(User).filter(User.role == "employee")
    
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    employees = query.all()
    
    employee_list = []
    for employee in employees:
        branch_name = None
        if employee.branch_id:
            branch = db.query(Branch).filter(Branch.id == employee.branch_id).first()
            if branch:
                branch_name = branch.name
        
        employee_list.append({
            "id": employee.id,
            "username": employee.username,
            "role": employee.role,
            "branch_id": employee.branch_id,
            "branch_name": branch_name,
            "created_at": employee.created_at.strftime("%Y-%m-%d %H:%M:%S") if employee.created_at else None
        })
    
    return {"items": employee_list}

# Tax-related endpoints
class TaxRateUpdate(BaseModel):
    tax_rate: float

    @validator('tax_rate')
    def validate_tax_rate(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Tax rate must be between 0 and 100')
        return v

@app.put("/api/branches/{branch_id}/tax_rate/")
def update_branch_tax_rate(
    branch_id: int,
    tax_data: TaxRateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "director":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only directors can update tax rates"
        )
    
    if tax_data.tax_rate < 0 or tax_data.tax_rate > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax rate must be between 0 and 100"
        )
    
    try:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
        
        branch.tax_rate = tax_data.tax_rate
        db.commit()
        
        return {
            "id": branch.id,
            "name": branch.name,
            "tax_rate": branch.tax_rate,
            "message": "Tax rate updated successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/branches/{branch_id}/tax_rate/")
def get_branch_tax_rate(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tax rate for a specific branch"""
    # Find the branch
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    
    return {
        "id": branch.id,
        "name": branch.name,
        "tax_rate": branch.tax_rate
    }

@app.get("/api/transactions/tax_summary/")
def tax_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    date_from: str = None,
    date_to: str = None,
    branch_id: int = None,
    currency: str = None,
    status: str = None
):
    """Get tax summary data for transactions."""
    try:
        # Build base query
        query = """
            SELECT 
                t.branch_id,
                b.name as branch_name,
                COUNT(*) as transaction_count,
                SUM(t.amount) as total_amount,
                SUM(t.benefited_amount) as benefited_amount,
                AVG(t.tax_rate) as avg_tax_rate,
                SUM(t.tax_amount) as tax_amount,
                t.currency
            FROM transactions t
            LEFT JOIN branches b ON t.branch_id = b.id
            WHERE 1=1
        """
        params = []

        # Add date filters
        if date_from:
            query += " AND t.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND t.date <= ?"
            params.append(date_to)
            
        # Add branch filter
        if branch_id:
            query += " AND t.branch_id = ?"
            params.append(branch_id)
            
        # Add currency filter
        if currency:
            query += " AND t.currency = ?"
            params.append(currency)
            
        # Add status filter
        if status:
            query += " AND t.status = ?"
            params.append(status)
        else:
            # By default, exclude cancelled transactions
            query += " AND t.status != 'cancelled'"
            
        # Group by branch
        query += " GROUP BY t.branch_id, b.name, t.currency"

        # Execute query
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        cursor.execute(query, params)
        branch_results = cursor.fetchall()
        
        # Get transaction details
        details_query = """
            SELECT 
                t.id,
                t.date,
                t.amount,
                t.benefited_amount,
                t.tax_rate,
                t.tax_amount,
                t.currency,
                sb.name as source_branch,
                db.name as destination_branch,
                t.status
            FROM transactions t
            LEFT JOIN branches sb ON t.branch_id = sb.id
            LEFT JOIN branches db ON t.destination_branch_id = db.id
            WHERE 1=1
        """
        
        # Add the same filters
        if date_from:
            details_query += " AND t.date >= ?"
        if date_to:
            details_query += " AND t.date <= ?"
        if branch_id:
            details_query += " AND t.branch_id = ?"
        if currency:
            details_query += " AND t.currency = ?"
        if status:
            details_query += " AND t.status = ?"
        else:
            details_query += " AND t.status != 'cancelled'"
            
        cursor.execute(details_query, params)
        transaction_details = cursor.fetchall()
        
        # Calculate totals
        total_amount = sum(float(row[3] or 0) for row in branch_results)
        total_benefited = sum(float(row[4] or 0) for row in branch_results)
        total_tax = sum(float(row[6] or 0) for row in branch_results)
        total_transactions = sum(int(row[2] or 0) for row in branch_results)
        
        # Format branch summary
        branch_summary = []
        for row in branch_results:
            branch_summary.append({
                "branch_id": row[0],
                "branch_name": row[1],
                "transaction_count": row[2],
                "total_amount": float(row[3] or 0),
                "benefited_amount": float(row[4] or 0),
                "tax_rate": float(row[5] or 0),
                "tax_amount": float(row[6] or 0),
                "currency": row[7]
            })

        # Format transaction details
        transactions = []
        for row in transaction_details:
            transactions.append({
                "id": row[0],
                "date": row[1],
                "amount": float(row[2] or 0),
                "benefited_amount": float(row[3] or 0),
                "tax_rate": float(row[4] or 0),
                "tax_amount": float(row[5] or 0),
                "currency": row[6],
                "source_branch": row[7],
                "destination_branch": row[8],
                "status": row[9]
            })

        return {
            "total_amount": total_amount,
            "total_benefited_amount": total_benefited,
            "total_tax_amount": total_tax,
            "total_transactions": total_transactions,
            "branch_summary": branch_summary,
            "transactions": transactions
        }
        
    except Exception as e:
        logger.error(f"Error in tax_summary_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tax summary: {str(e)}"
        )
    finally:
        if 'conn' in locals():
            conn.close()
