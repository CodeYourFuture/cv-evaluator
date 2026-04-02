# cv-evaluator
CV Evaluator sends a CV to an LLM for review. A CodeYourFuture project.

## Local Development Instructions

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
From the project root directory:
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

## Docker

## Install Docker
https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

## Build the image
From the root of the project, where the `Dockerfile` is located:

```
$ sudo docker build -t cyf-cv-evaluator .
```

## Run locally
Run the local image, passing in the openrouter API key as an environment variable:

```bash
sudo docker run -ti --rm -e OPENROUTER_API_KEY=your_openrouter_api_key_here --name cyf-cv-evaluator -p 8000:8000 cyf-cv-evaluator
```

## Export the image to a file
```bash
sudo docker save -o ~/cyf-cv-evaluator.tar cyf-cv-evaluator:latest

sudo chmod 777 ~/cyf-cv-evaluator.tar
```

# If needed, copy the image elsewhere
```bash
scp ~/cyf-cv-evaluator.tar user@server:/home/user
```

## If needed, remove the old cyf-cv-evaluator container and image
```bash
sudo docker stop cyf-cv-evaluator

sudo docker rm cyf-cv-evaluator

sudo docker rmi cyf-cv-evaluator
```

## Load the image elsewhere
Load the image into docker:
```bash
sudo docker load -i ./cyf-cv-evaluator.tar

sudo docker images
```

## Create and run a container from the image
Copy `docker-compose.yaml` to the server, update the `OPENROUTER_API_KEY` environment variable, and run:

```bash
sudo docker compose up -d
```
