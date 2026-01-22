from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM API Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Tax Assistant System Message
TAX_ASSISTANT_SYSTEM_MESSAGE = """You are MyCA AI Tax Assistant, an expert Chartered Accountant specializing in Indian taxation. You provide professional advice on:

1. **Income Tax Returns (ITR)**: Filing guidance, tax slabs, deductions under 80C, 80D, HRA exemptions, capital gains
2. **GST Returns**: GSTR-1, GSTR-3B filing, input tax credit, GST rates, compliance
3. **Tax Planning & Savings**: Legal tax-saving strategies, investment options (ELSS, PPF, NPS), HRA optimization
4. **Business Taxation**: For proprietors, partnerships, companies - TDS, advance tax, professional tax
5. **Compliance**: Due dates, penalties, notices handling

Guidelines:
- Always provide accurate, up-to-date information based on Indian tax laws
- Suggest legal tax-saving methods only
- Recommend consulting a CA for complex situations
- Be helpful, professional, and explain concepts clearly
- Use examples with INR amounts when helpful"""

# Models
class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ContactForm(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    phone: str
    service: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactFormCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    service: str
    message: str

class TaxCalculationRequest(BaseModel):
    income: float
    deductions_80c: float = 0
    deductions_80d: float = 0
    hra_exemption: float = 0
    other_deductions: float = 0
    regime: str = "new"  # "new" or "old"

class TaxCalculationResponse(BaseModel):
    gross_income: float
    total_deductions: float
    taxable_income: float
    tax_amount: float
    cess: float
    total_tax: float
    effective_rate: float
    regime: str

class DocumentUpload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    purpose: str
    user_email: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def calculate_tax_old_regime(taxable_income: float) -> float:
    """Calculate tax under old regime FY 2024-25"""
    if taxable_income <= 250000:
        return 0
    elif taxable_income <= 500000:
        return (taxable_income - 250000) * 0.05
    elif taxable_income <= 1000000:
        return 12500 + (taxable_income - 500000) * 0.20
    else:
        return 12500 + 100000 + (taxable_income - 1000000) * 0.30

def calculate_tax_new_regime(taxable_income: float) -> float:
    """Calculate tax under new regime FY 2024-25"""
    if taxable_income <= 300000:
        return 0
    elif taxable_income <= 700000:
        return (taxable_income - 300000) * 0.05
    elif taxable_income <= 1000000:
        return 20000 + (taxable_income - 700000) * 0.10
    elif taxable_income <= 1200000:
        return 20000 + 30000 + (taxable_income - 1000000) * 0.15
    elif taxable_income <= 1500000:
        return 20000 + 30000 + 30000 + (taxable_income - 1200000) * 0.20
    else:
        return 20000 + 30000 + 30000 + 60000 + (taxable_income - 1500000) * 0.30

# API Routes
@api_router.get("/")
async def root():
    return {"message": "MyCA API - Tax Assistant Service"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """Chat with the AI Tax Assistant"""
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=request.session_id,
            system_message=TAX_ASSISTANT_SYSTEM_MESSAGE
        ).with_model("gemini", "gemini-3-flash-preview")
        
        # Get chat history for context
        history = await db.chat_messages.find(
            {"session_id": request.session_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(20)
        
        # Build context from history
        context_messages = []
        for msg in history[-10:]:  # Last 10 messages for context
            context_messages.append(f"{msg['role'].upper()}: {msg['content']}")
        
        # Create message with context
        full_message = request.message
        if context_messages:
            full_message = f"Previous conversation:\n" + "\n".join(context_messages) + f"\n\nUser's new question: {request.message}"
        
        # Send message to LLM
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Save user message
        user_msg = ChatMessage(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        user_doc = user_msg.model_dump()
        user_doc['timestamp'] = user_doc['timestamp'].isoformat()
        await db.chat_messages.insert_one(user_doc)
        
        # Save assistant response
        assistant_msg = ChatMessage(
            session_id=request.session_id,
            role="assistant",
            content=response
        )
        assistant_doc = assistant_msg.model_dump()
        assistant_doc['timestamp'] = assistant_doc['timestamp'].isoformat()
        await db.chat_messages.insert_one(assistant_doc)
        
        return ChatResponse(response=response, session_id=request.session_id)
        
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@api_router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    messages = await db.chat_messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    return {"messages": messages}

@api_router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    await db.chat_messages.delete_many({"session_id": session_id})
    return {"message": "Chat history cleared"}

@api_router.post("/contact")
async def submit_contact_form(form: ContactFormCreate):
    """Submit a contact/consultation request"""
    try:
        contact = ContactForm(**form.model_dump())
        doc = contact.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        await db.contact_forms.insert_one(doc)
        return {"message": "Thank you! We'll contact you within 24 hours.", "id": contact.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/calculate-tax", response_model=TaxCalculationResponse)
async def calculate_tax(request: TaxCalculationRequest):
    """Calculate income tax based on income and deductions"""
    total_deductions = 0
    
    if request.regime == "old":
        # Old regime allows deductions
        total_deductions = min(request.deductions_80c, 150000) + \
                          min(request.deductions_80d, 75000) + \
                          request.hra_exemption + \
                          request.other_deductions
        taxable_income = max(0, request.income - total_deductions)
        tax_amount = calculate_tax_old_regime(taxable_income)
    else:
        # New regime - standard deduction of 75000 only
        total_deductions = 75000
        taxable_income = max(0, request.income - total_deductions)
        tax_amount = calculate_tax_new_regime(taxable_income)
        
        # Rebate u/s 87A for income up to 7 lakhs
        if taxable_income <= 700000:
            tax_amount = 0
    
    cess = tax_amount * 0.04
    total_tax = tax_amount + cess
    effective_rate = (total_tax / request.income * 100) if request.income > 0 else 0
    
    return TaxCalculationResponse(
        gross_income=request.income,
        total_deductions=total_deductions,
        taxable_income=taxable_income,
        tax_amount=tax_amount,
        cess=cess,
        total_tax=total_tax,
        effective_rate=round(effective_rate, 2),
        regime=request.regime
    )

@api_router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    purpose: str = Form(...),
    user_email: str = Form(...)
):
    """Upload a document for GST/Tax filing assistance"""
    try:
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="File type not allowed. Please upload PDF, JPG, PNG, or Excel files.")
        
        # Save file info to database
        doc_record = DocumentUpload(
            filename=file.filename,
            file_type=file.content_type,
            purpose=purpose,
            user_email=user_email
        )
        doc_dict = doc_record.model_dump()
        doc_dict['timestamp'] = doc_dict['timestamp'].isoformat()
        await db.documents.insert_one(doc_dict)
        
        # Read file content (in production, save to cloud storage)
        content = await file.read()
        
        return {
            "message": "Document uploaded successfully! Our CA will review it within 24 hours.",
            "document_id": doc_record.id,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/services")
async def get_services():
    """Get list of CA services offered"""
    services = [
        {
            "id": "itr",
            "title": "ITR Filing",
            "description": "Expert income tax return filing for individuals and businesses",
            "price": "Starting ₹999",
            "features": ["All ITR forms", "Tax optimization", "Quick processing", "Expert review"]
        },
        {
            "id": "gst",
            "title": "GST Returns",
            "description": "Complete GST compliance - GSTR-1, 3B, Annual returns",
            "price": "Starting ₹1,499/month",
            "features": ["GSTR-1 & GSTR-3B", "Input credit reconciliation", "E-invoicing setup", "Compliance calendar"]
        },
        {
            "id": "tax-planning",
            "title": "Tax Planning",
            "description": "Strategic tax planning to maximize your savings legally",
            "price": "Starting ₹2,999",
            "features": ["Investment advice", "Deduction optimization", "Future planning", "Tax projections"]
        },
        {
            "id": "business",
            "title": "Business Services",
            "description": "Complete accounting and compliance for businesses",
            "price": "Custom pricing",
            "features": ["Company registration", "TDS returns", "Audit support", "Advisory services"]
        }
    ]
    return {"services": services}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
