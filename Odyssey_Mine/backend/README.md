# AI Travel Planner — Backend

Backend for an AI-powered Smart Travel Planner built with Python and FastAPI.

The backend provides APIs and services for travel planning, recommendations, itinerary generation, budget optimization, route optimization, tourism data, authentication, and AI-assisted travel queries.

## Features

- AI Travel Assistant
- Travel intent detection
- Personalized travel recommendations
- Dynamic itinerary generation
- Budget optimization
- Route optimization
- Tourism data APIs
- Hotel and activity recommendations
- Weather and crowd-aware planning support
- RAG-based tourism information retrieval
- User authentication
- Trip management
- Expense management
- REST APIs
- Automated testing

## AI Components

### AI Travel Assistant
Processes natural-language travel requests and identifies the user's intent.

Examples:

- Make my trip cheaper
- Add an activity
- Change my hotel
- Avoid crowded places
- Optimize my route

### Recommendation Engine
Ranks travel options based on factors such as:

- Budget
- Destination
- Interests
- Ratings
- Distance
- Preferences

### Itinerary Generator
Generates day-wise travel plans based on:

- Destination
- Trip duration
- Budget
- Interests
- Travel pace

### Budget Optimizer
Optimizes the travel plan according to the user's budget while considering travel preferences.

### Route Optimizer
Provides optimized routes between multiple travel locations.

### RAG Retriever
Provides tourism-related information retrieval capabilities for the AI travel system.

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite
- MongoDB
- Pytest
- REST API
- LLM integration layer

## Project Structure

text
backend/
│
├── app/
│   ├── ai/
│   │   ├── agent/
│   │   ├── assistant/
│   │   ├── itinerary/
│   │   ├── llm/
│   │   ├── optimizer/
│   │   ├── rag/
│   │   ├── recommendation/
│   │   └── tools/
│   │
│   ├── api/
│   │   └── routes/
│   │
│   ├── core/
│   ├── data/
│   ├── models/
│   ├── schemas/
│   └── services/
│
├── tests/
├── .env.example
├── .gitignore
└── requirements.txt

Setup
1. Clone the repository
git clone https://github.com/HarshK-Dev108/Odyssey.git
2. Go to the backend
cd Odyssey/backend
3. Create virtual environment
python -m venv venv
4. Activate virtual environment
macOS / Linux
source venv/bin/activate
Windows
venv\Scripts\activate
5. Install dependencies
pip install -r requirements.txt
6. Configure environment variables

Create a .env file using .env.example.

cp .env.example .env

Add the required configuration and API keys.

Never commit .env or secret API keys to GitHub.

Run the Backend

Start the FastAPI server:

uvicorn app.main:app --reload

The API will be available at:

http://127.0.0.1:8000
API Documentation

Swagger UI:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc
Testing

Run the test suite:

pytest

The test suite covers areas including:

Authentication
AI abstractions
AI assistant
Budget optimization
Itinerary generation
Route optimization
Tourism API
Tourism services
Trip validation
Environment Variables

Use .env.example to configure the backend.

Sensitive values such as API keys and credentials should remain inside .env and must not be committed to the repository.

Backend Architecture
Client
  │
  ▼
FastAPI REST API
  │
  ├── Authentication
  ├── Trips
  ├── Expenses
  ├── Tourism APIs
  ├── AI Assistant
  └── Optimization
          │
          ▼
      AI Layer
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
  LLM   RAG   Recommendation
    │           │
    └─────┬─────┘
          ▼
   Itinerary / Budget / Route
       Optimization
          │
          ▼
    Travel Data & Database
