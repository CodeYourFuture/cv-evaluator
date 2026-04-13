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
   
   # GitHub OAuth (see "GitHub App Setup" section below)
   GITHUB_APP_CLIENT_ID=your_github_app_client_id
   GITHUB_APP_CLIENT_SECRET=your_github_app_client_secret
   
   # Session security - generate a random key
   SESSION_SECRET_KEY=your_random_secret_key_here
   
   # Organization restriction (users must be members of this org)
   ALLOWED_ORG=CodeYourFuture
   
   # Application URL (for OAuth callback)
   APP_URL=http://localhost:8000
   
   # Environment (use 'development' for local, 'production' for deployed)
   ENVIRONMENT=development
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

## GitHub App Setup

This application uses GitHub OAuth for authentication. Only members of the configured GitHub organization can access the CV evaluation feature.

### Creating a GitHub App

1. Go to your GitHub organization settings: https://github.com/organizations/CodeYourFuture/settings/apps

2. Click **"New GitHub App"**

3. Fill in the required fields:
   - **GitHub App name**: `CV Evaluator` (or similar)
   - **Homepage URL**: `https://example.com`
   - **Callback URL**: `https://example.com/api/auth/callback`
     - For local development, add: `http://localhost:8000/api/auth/callback`
   - **Webhook**: Uncheck "Active" (not needed)

4. Under **"Permissions"**, set:
   - **Account permissions**:
     - `Email addresses`: Read-only
   - **Organization permissions**:
     - `Members`: Read-only
   Note: changing these permissions may require approval from your GitHub organization admins, and the UI may not reflect whether the changes are actually in effect.

5. Under **"Where can this GitHub App be installed?"**, select:
   - "Only on this account" (recommended for org-only access)

6. Click **"Create GitHub App"**

7. After creation, note the **Client ID** shown on the app page

8. Click **"Generate a new client secret"** and save it securely

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_APP_CLIENT_ID` | Client ID from GitHub App settings | `Iv1.abc123...` |
| `GITHUB_APP_CLIENT_SECRET` | Client secret (keep secure!) | `abc123...` |
| `SESSION_SECRET_KEY` | Random string for signing cookies | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ALLOWED_ORG` | GitHub org name users must belong to | `CodeYourFuture` |
| `APP_URL` | Public URL of the application | `https://example.com` |
| `ENVIRONMENT` | `development` or `production` | `production` |

### Authentication Flow

1. User clicks "Sign in with GitHub"
2. User is redirected to GitHub to authorize
3. GitHub redirects back to `/api/auth/callback`
4. App verifies user is a member of the allowed organization
5. Session cookie is set (valid for 24 hours by default)
6. User can now access the CV evaluation feature

### Security Notes

- Session tokens are signed JWTs stored in HTTP-only cookies
- In production (`ENVIRONMENT=production`), cookies are set with `Secure` flag (HTTPS only)
- CORS is restricted to `APP_URL` in production
- Organization membership is verified during login

## Manual Docker Deployment Instructions

### Install Docker
https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

### Build the image
From the root of the project, where the `Dockerfile` is located:

```
$ sudo docker build -t cyf-cv-evaluator .
```

### Run locally
Run the local image, passing in environment variables:

```bash
sudo docker run -ti --rm \
  -e OPENROUTER_API_KEY=your_openrouter_api_key_here \
  -e GITHUB_APP_CLIENT_ID=your_client_id \
  -e GITHUB_APP_CLIENT_SECRET=your_client_secret \
  -e SESSION_SECRET_KEY=your_session_secret \
  -e ALLOWED_ORG=CodeYourFuture \
  -e APP_URL=http://localhost:8000 \
  -e ENVIRONMENT=development \
  --name cyf-cv-evaluator -p 8000:8000 cyf-cv-evaluator
```

### Export the image to a file
```bash
sudo docker save -o ~/cyf-cv-evaluator.tar cyf-cv-evaluator:latest

sudo chmod 777 ~/cyf-cv-evaluator.tar
```

### If needed, copy the image elsewhere
```bash
scp ~/cyf-cv-evaluator.tar user@server:/home/user
```

### If needed, remove the old cyf-cv-evaluator container and image
```bash
sudo docker stop cyf-cv-evaluator

sudo docker rm cyf-cv-evaluator

sudo docker rmi cyf-cv-evaluator
```

### Load the image elsewhere
Load the image into docker:
```bash
sudo docker load -i ./cyf-cv-evaluator.tar

sudo docker images
```

### Create and run a container from the image
Copy `docker-compose.yaml` to the server, update the environment variables (see "Environment Variables" section above), and run:

```bash
sudo docker compose up -d
```

## Coolify Deployment Instructions

1. Create a new application in Coolify.
2. Add `New Resource`, select `Public Repository`, and point to this GitHub repository.
3. Select `Dockerfile` as the build pack.
4. Set **domain** to the Coolify server (e.g. `my-server.example.com`)
5. Under **Network**, set **Ports Exposes** to `8000`.
6. Under **Environment Variables**, add the following variables with appropriate values:
   - `OPENROUTER_API_KEY`
   - `GITHUB_APP_CLIENT_ID`
   - `GITHUB_APP_CLIENT_SECRET`
   - `SESSION_SECRET_KEY`
   - `ALLOWED_ORG` (e.g. `CodeYourFuture`)
   - `APP_URL` (set to your Coolify domain, e.g. `https://my-server.example.com` with No trailing slash)
   - `ENVIRONMENT` (set to `production` for secure cookies and CORS)
7. Deploy the application.
