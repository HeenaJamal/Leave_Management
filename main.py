from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Enum, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from enum import Enum as PyEnum
import datetime

# Database Configuration
DATABASE_URL = "mysql+pymysql://root:Arhaanjamal@localhost/leave_management"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# Enums for role and leave status
class Role(str, PyEnum):
    admin = "admin"
    employee = "employee"

class LeaveStatus(str, PyEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

# Models (SQLAlchemy ORM)
class Employee(Base):
    __tablename__ = 'employees'
    employee_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    department = Column(String(100))
    email = Column(String(100), unique=True)
    role = Column(Enum(Role), default=Role.employee)

class LeaveRequest(Base):
    __tablename__ = 'leave_requests'
    leave_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.employee_id'))
    start_date = Column(Date)
    end_date = Column(Date)
    leave_type = Column(String(50))
    status = Column(Enum(LeaveStatus), default=LeaveStatus.pending)
    employee = relationship("Employee")

# Pydantic Schemas
class LeaveRequestSchema(BaseModel):
    employee_id: int
    start_date: datetime.date
    end_date: datetime.date
    leave_type: str

    class Config:
        orm_mode = True

class LeaveUpdateSchema(BaseModel):
    status: LeaveStatus

# Dependency for Database Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)

# APIs

# 1. Submit a New Leave Request (Employee Role)
@app.post("/leave/request")
def submit_leave_request(leave_request: LeaveRequestSchema, db: Session = Depends(get_db)):
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.employee_id == leave_request.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Create new leave request
    new_leave = LeaveRequest(
        employee_id=leave_request.employee_id,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        leave_type=leave_request.leave_type
    )
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return {"msg": "Leave request submitted", "leave_request": new_leave}

# 2. Approve/Reject Leave Request (Admin Role)
@app.put("/leave/{leave_id}/status")
def update_leave_status(leave_id: int, leave_update: LeaveUpdateSchema, db: Session = Depends(get_db)):
    # Find leave request
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.leave_id == leave_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # Update leave status
    leave_request.status = leave_update.status
    db.commit()
    return {"msg": f"Leave request {leave_request.leave_id} status updated to {leave_update.status}"}

# 3. View Leave Status for an Employee (Employee Role)
@app.get("/leave/{employee_id}/status")
def view_leave_status(employee_id: int, db: Session = Depends(get_db)):
    leave_requests = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id).all()
    if not leave_requests:
        raise HTTPException(status_code=404, detail="No leave requests found for this employee")
    
    return {"leave_requests": leave_requests}

# 4. List All Pending Leave Requests (Admin View)
@app.get("/leave/pending")
def list_pending_leave_requests(db: Session = Depends(get_db)):
    pending_requests = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.pending).all()
    return {"pending_leave_requests": pending_requests}
