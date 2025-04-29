from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="employee")
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship to Branch
    branch = relationship("Branch", back_populates="users")

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    governorate = Column(String)
    allocated_amount_syp = Column(Float, default=0.0)
    allocated_amount_usd = Column(Float, default=0.0)
    allocated_amount = Column(Float, default=0.0)  # Kept for backward compatibility
    tax_rate = Column(Float, default=0.0)  # Added tax rate field
    created_at = Column(DateTime, default=datetime.now)
    
    fund_history = relationship("BranchFund", back_populates="branch")
    # Relationships
    users = relationship("User", back_populates="branch")
    sent_transactions = relationship("Transaction", foreign_keys="[Transaction.branch_id]", back_populates="branch")
    received_transactions = relationship("Transaction", foreign_keys="[Transaction.destination_branch_id]", back_populates="destination_branch")


class BranchFund(Base):
    __tablename__ = "branch_funds"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    amount = Column(Float)
    type = Column(String)
    currency = Column(String, default="SYP")  # Added currency field
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    
    branch = relationship("Branch", back_populates="fund_history")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    sender = Column(String)
    sender_mobile = Column(String)
    sender_governorate = Column(String)
    sender_location = Column(String)
    sender_id = Column(String)  # Added sender ID field
    sender_address = Column(String)  # Added sender address field
    receiver = Column(String)
    receiver_mobile = Column(String)
    receiver_id = Column(String)
    receiver_address = Column(String)
    receiver_governorate = Column(String)
    receiver_location = Column(String)
    amount = Column(Float)  # Total amount
    base_amount = Column(Float, default=0.0)  # Added base amount
    benefited_amount = Column(Float, default=0.0)  # Added benefited amount
    currency = Column(String, default="ليرة سورية")
    message = Column(Text)
    
    # Branch relationships
    branch_id = Column(Integer, ForeignKey("branches.id"))
    destination_branch_id = Column(Integer, ForeignKey("branches.id"))
    type = Column(String)
    
    # Tax information
    tax_amount = Column(Float, default=0.0)  # Amount of tax collected
    tax_rate = Column(Float, default=0.0)    # Tax rate applied at time of transaction
    
    # User relationships
    employee_id = Column(Integer, ForeignKey("users.id"))
    received_by = Column(Integer, ForeignKey("users.id"))
    
    employee_name = Column(String)
    branch_governorate = Column(String)
    status = Column(String, default="processing")
    is_received = Column(Boolean, default=False)
    received_at = Column(DateTime)
    date = Column(DateTime, default=datetime.now)
    
    # Relationships
    branch = relationship("Branch", foreign_keys=[branch_id], back_populates="sent_transactions")
    destination_branch = relationship("Branch", foreign_keys=[destination_branch_id], back_populates="received_transactions")
    employee = relationship("User", foreign_keys=[employee_id])
    receiver_user = relationship("User", foreign_keys=[received_by])
    
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    recipient_phone = Column(String)
    message = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)

    transaction = relationship("Transaction", backref="notifications")   