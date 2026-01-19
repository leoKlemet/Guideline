# Guideline Prototype

A prototype repo for "Guideline" with:
- Frontend: Vite + React + TypeScript + Tailwind
- Backend: FastAPI + SQLite (single file DB)

## Run Instructions

### ⚡ Local LLM Setup (Required for AI Features)
This project uses **LM Studio** for local AI processing to ensure data privacy.
1.  **Install LM Studio** from [lmstudio.ai](https://lmstudio.ai/).
2.  **Download a Model**: Search for `Llama 3` (e.g., `Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`) and download it.
3.  **Start Local Server**:
    *   Click the **Chat** icon on the left sidebar.
    *   Select your downloaded model at the top drop down.
    *   Click the **Developer** icon on the left sidebar.
    *   Click **Start Server** switch at the top left (next to Status: Stopped).
    *   Ensure the port is **1234**.
    *   *Keep LM Studio running in the background.*

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
