# GitHub PR Reviewer

This project automates the process of reviewing GitHub Pull Requests using Azure OpenAI.
It fetches PR details and diffs, sends them to an Azure OpenAI model for analysis,
generates expert-like review comments, saves them to a Markdown file, and can optionally
post the review as a general comment on the PR.

## Features

-   Fetches PR title, description, and diff from a given GitHub PR URL.
-   Utilizes Azure OpenAI to generate comprehensive code reviews.
-   Saves the generated review to a local Markdown file.
-   Prompts the user for approval before posting the review to GitHub.
-   Posts the review as a general comment on the PR (inline commenting is a future enhancement).

## Setup

1.  **Clone the repository (if applicable) or ensure you have the script `reviewer.py`.**

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file:**
    Copy the `.env.example` file to a new file named `.env` in the `github_pr_reviewer` directory:
    ```bash
    cp .env.example .env
    ```
    Then, fill in your actual credentials in the `.env` file:
    *   `GITHUB_TOKEN`: Your GitHub Personal Access Token with `repo` scope (or `public_repo` for public repositories).
    *   `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key.
    *   `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI resource endpoint (e.g., `https://your-resource-name.openai.azure.com/`).
    *   `AZURE_OPENAI_MODEL_ID`: The deployment name of your Azure OpenAI model (e.g., `gpt-4-turbo`, `gpt-35-turbo`).
    *   `AZURE_OPENAI_API_VERSION`: The API version you are using (e.g., `2024-02-01`).

    **Important:** Never commit your `.env` file to version control. The `.gitignore` file should already be configured to ignore it.

## Usage

Run the script from your terminal, providing the GitHub PR URL as a command-line argument:

```bash
python reviewer.py "https://github.com/owner/repository-name/pull/123"
```

The script will:
1.  Fetch the PR data.
2.  Send the data to Azure OpenAI for review.
3.  Print a preview of the review to the console.
4.  Save the full review to a Markdown file named `review_PR_<PR_NUMBER>.md`.
5.  Ask if you want to post the review as a comment on the GitHub PR.

## Dependencies

-   `requests`: For making HTTP requests to the GitHub API.
-   `python-dotenv`: For managing environment variables.
-   `openai`: The official OpenAI Python library, used here for Azure OpenAI.

## Future Enhancements

-   Support for posting inline comments directly to the diff.
-   More sophisticated handling of large diffs (e.g., chunking, summarization before sending to AI).
-   Configuration options for review depth, tone, etc.
-   Caching mechanisms to avoid re-reviewing unchanged parts of a PR.
