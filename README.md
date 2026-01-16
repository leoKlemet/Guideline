# Guideline Prototype

A prototype repo for "Guideline" with:
- Frontend: Vite + React + TypeScript + Tailwind
- Backend: FastAPI + SQLite (single file DB)

## Run Instructions

### Backend
1. Navigate to the api directory:
   ```bash
   cd apps/api
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Unix
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Seed the database:
   ```bash
   python -m app.seed
   ```
5. Run the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend
1. Navigate to the web directory:
   ```bash
   cd apps/web
   ```
2. Install dependencies:
   ```bash
   npm install
   # or
   pnpm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   # or
   pnpm dev --host
   ```
