# cv-evaluator
CV Evaluator sends a CV to an LLM for review. A CodeYourFuture project.

### Setup
1. Create a virtual environment:
   ```bash
   python -m venv cveval-venv
   ```

2. Activate the virtual environment:
   - Windows: `cveval-venv\Scripts\activate`
   - macOS/Linux: `source cveval-venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following content:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

5. Update `app/llm_evaluator.yml` with your desired LLM configuration (model, reasoning level, etc.).

### Running the Application
1. From the project root directory:
   ```bash
   python app/main.py
   ```
   
2. Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Accessing the Application
- Static site: http://localhost:8000
- API documentation: http://localhost:8000/api/docs

### Project Structure
```
app/
├── main.py          # Main FastAPI application with API and static file serving
├── llm_evaluator.py # LLM evaluator module
└── static/          # Static files served at root path 
    └── index.html   # Main HTML page for the CV Evaluation application
```

The application creates two FastAPI instances:
- `app`: Main application that serves static files and mounts the API
- `api_app`: API-specific application mounted under `/api` with CORS enabled

### Notes
- `slowapi` is used for rate limiting, since there's LLM cost involved with each evaluation. The default limit is set to 5 requests per minute per IP address.
- `markitdown` is used to convert uploaded CV files (PDF, DOCX) into markdown format for easier processing by the LLM.
