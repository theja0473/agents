# GitHub PR Reviewer

This project automates the process of reviewing GitHub Pull Requests using Azure OpenAI, accessible via a Gradio-based web interface.
It fetches PR details and diffs, sends them to an Azure OpenAI model for analysis,
generates expert-like review comments, allows downloading the review as a Markdown file, and can optionally
post the review as a general comment on the PR.

## Features

-   **Web Interface**: Easy-to-use UI built with Gradio.
-   **Configurable**: Set API keys and endpoints through the UI for the current session.
-   Fetches PR title, description, and diff from a given GitHub PR URL.
-   Utilizes Azure OpenAI to generate comprehensive code reviews.
-   Displays the generated review directly in the UI.
-   Allows downloading the review as a Markdown file.
-   Option to post the review as a general comment on the PR.

## Setup

1.  **Clone the repository (if applicable) or ensure you have the script `reviewer.py` and other project files.**

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will install `requests`, `python-dotenv`, `openai`, and `gradio`.

3.  **Environment Variables (Optional Initial Setup):**
    You can optionally create a `.env` file in the `github_pr_reviewer` directory to pre-fill configuration values when the Gradio app starts. Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
    Fill in your credentials in the `.env` file:
    *   `GITHUB_TOKEN`: Your GitHub Personal Access Token.
    *   `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key.
    *   `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI resource endpoint.
    *   `AZURE_OPENAI_MODEL_ID`: Your Azure OpenAI model deployment name.
    *   `AZURE_OPENAI_API_VERSION`: Your Azure OpenAI API version.

    **Note:** Configuration values entered in the Gradio UI's "Configuration" tab will take precedence over `.env` values and are saved for the current session only.

## Usage

Run the script from your terminal to launch the Gradio web interface:

```bash
python github_pr_reviewer/reviewer.py
```
(Ensure your current directory is the root of the project, not inside `github_pr_reviewer` itself, or adjust the path accordingly.)

This will typically start a local web server (e.g., at `http://127.0.0.1:7860`). Open this URL in your browser.

The interface has two tabs:

### 1. Configuration Tab
   -   Enter your `GitHub Token`, `Azure OpenAI API Key`, `Azure OpenAI Endpoint`, `Azure OpenAI Model ID`, and `Azure OpenAI API Version`.
   -   Click "Save Configuration for Session". These details are required for the review process and are stored only for the duration of your browser session with the app.
   -   If you have a `.env` file, these fields might be pre-filled on startup.

### 2. Review Tab
   -   Ensure your configuration is saved in the "Configuration" tab.
   -   Enter the full **GitHub PR URL** you want to review.
   -   Check the **"Post review as a comment on PR"** box if you want the generated review to be automatically posted as a single comment on the GitHub Pull Request.
   -   Click the **"Generate Review"** button.
   -   The status of the process will be updated, and upon completion:
        *   The AI-generated review will be displayed in Markdown format.
        *   A download link for the review (as a `.md` file) will be provided.

## Dependencies

-   `requests`: For making HTTP requests to the GitHub API.
-   `python-dotenv`: For managing environment variables (used for optional initial loading).
-   `openai`: The official OpenAI Python library, used for Azure OpenAI.
-   `gradio`: For creating the web UI.

## Future Enhancements

-   True inline commenting support (posting comments to specific lines in the diff).
-   More sophisticated handling of large diffs (e.g., chunking, summarization before sending to AI).
-   Configuration options for review depth, tone, etc.
-   Caching mechanisms to avoid re-reviewing unchanged parts of a PR.

## Running with Docker

You can also build and run this application using Docker and Docker Compose. This is a good way to run the application in a consistent environment.

**Prerequisites:**
- Docker installed (e.g., Docker Desktop).
- Docker Compose installed (usually comes with Docker Desktop).

**Steps:**

1.  **Environment Variables for Docker (Optional but Recommended for API Keys):**
    The application inside Docker will need access to API keys. While you can enter them via the Gradio UI each session, for more persistent local Docker runs, you can use a `.env` file at the project root (where `docker-compose.yml` is).
    Docker Compose will automatically load this `.env` file and make the variables available to the container if the `environment` section in `docker-compose.yml` is configured to use them (currently, it's commented out but shows examples like `GITHUB_TOKEN: ${GITHUB_TOKEN}`).

    To use this method:
    *   Create a `.env` file in the project root: `cp github_pr_reviewer/.env.example .env` (adjust source path if your `.env.example` is elsewhere).
    *   Edit this new `.env` file with your actual keys.
    *   If you use this method, ensure the `env_file` directive or `environment` variable mappings are correctly set up in your `docker-compose.yml`.

2.  **Build and Run the Container:**
    Navigate to the project root directory and run:
    ```bash
    docker-compose up --build
    ```
    This command builds the Docker image (if it's the first time or if `Dockerfile` or related files changed) and starts the application.
    To run in detached mode (in the background), add the `-d` flag:
    ```bash
    docker-compose up --build -d
    ```

3.  **Access the Application:**
    Open your web browser and go to `http://localhost:7860`.

4.  **Stopping the Application:**
    If running in the foreground (`Ctrl+C` might not always gracefully stop compose).
    The recommended way to stop the application, whether started in foreground or detached mode, is:
    ```bash
    docker-compose down
    ```
    This will stop and remove the containers defined in `docker-compose.yml`.

## Continuous Integration (CI)

This project includes a basic CI pipeline configuration using GitHub Actions, located in `.github/workflows/ci.yml`.
The current CI pipeline performs the following:
-   **Linting**: Checks the Python code in the `github_pr_reviewer/` directory for style issues using Flake8.
-   **Docker Build**: Builds the Docker image for the application to ensure it packages correctly.
-   **Test Placeholder**: The workflow includes commented-out placeholders indicating where automated tests (e.g., unit, integration, or UI tests using tools like Pytest or Robot Framework) would be executed. Implementing a comprehensive automated test suite is a planned future enhancement.

The CI workflow is configured to trigger on pushes and pull requests to the `main` branch.
