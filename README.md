# My-CA
# MyCA - AI-Powered Tax Assistant Website

A modern, full-stack CA (Chartered Accountant) website with AI-powered tax assistant built using React, FastAPI, and MongoDB.


##  Features

- **AI Tax Assistant** - Powered by Gemini 3 Flash for instant tax advice
- **Income Tax Calculator** - Calculate tax under Old & New regime (FY 2024-25)
- **GST Filing Support** - Document upload for GST compliance
- **Contact Form** - Consultation requests with email notifications
- **Service Pricing** - Transparent pricing for all CA services
- **Client Testimonials** - Social proof section
- **Responsive Design** - Mobile-friendly with glassmorphism effects

## 🛠️ Tech Stack

**Frontend:**
- React 19
- Tailwind CSS
- Shadcn/UI Components
- Lucide React Icons
- Axios

**Backend:**
- FastAPI (Python)
- MongoDB with Motor (async)
- Emergent Integrations (AI)
- Pydantic

## 📦 Installation

### Prerequisites
- Node.js 18+
- Python 3.11+
- MongoDB

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Run server
uvicorn server:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Create .env file
cp .env.example .env
# Edit .env with your backend URL

# Run development server
yarn start
```

## 🔧 Environment Variables

### Backend (.env)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="myca_db"
CORS_ORIGINS="*"
EMERGENT_LLM_KEY=your_emergent_llm_key_here
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/` | Health check |
| POST | `/api/chat` | AI chat assistant |
| GET | `/api/chat/history/{session_id}` | Get chat history |
| DELETE | `/api/chat/history/{session_id}` | Clear chat history |
| POST | `/api/calculate-tax` | Calculate income tax |
| POST | `/api/contact` | Submit contact form |
| POST | `/api/upload-document` | Upload documents |
| GET | `/api/services` | Get service list |

##  Design Features

- **Typography**: Playfair Display (headings) + Manrope (body)
- **Colors**: Deep Emerald (#022c22) + Amber Accent (#d97706)
- **Effects**: Glassmorphism, smooth animations, floating elements
- **Layout**: Bento grid, asymmetric sections

##  Sections

1. **Hero** - Main landing with CTA
2. **Services** - ITR, GST, Tax Planning, Business Services
3. **Tax Calculator** - Interactive calculator
4. **AI Assistant** - Chat interface
5. **Pricing** - 3-tier pricing plans
6. **Testimonials** - Client reviews
7. **Document Upload** - File submission
8. **Contact** - Consultation form
9. **Footer** - Links and info
