# Stock Intelligence Platform (CrewAI + Kimi 2.5)

This is a production-ready stock analysis platform that uses a multi-agent CrewAI workflow to gather real-time market data, analyze news sentiment, and provide expert-style investment verdicts.

## Features
- **Multi-Agent Workflow**: 5 specialized agents (Researcher, News Analyst, Data Analyst, Financial Expert, Orchestrator).
- **Kimi 2.5 Integration**: High-quality reasoning and synthesis.
- **Real-time Data**: Powered by `yfinance` and DuckDuckGo Search.
- **Modern Dashboard**: React + TypeScript + TailwindCSS + Recharts.

## Setup Instructions

### Backend
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` and add your Kimi/OpenAI API credentials.
4. Run the FastAPI server:
   ```bash
   python main.py
   ```

### Frontend
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Tech Stack
- **AI**: CrewAI, LangChain, Kimi 2.5
- **Data**: yfinance, DuckDuckGo Search
- **Backend**: FastAPI, Pydantic
- **Frontend**: React, TypeScript, TailwindCSS, Recharts, Lucide Icons
