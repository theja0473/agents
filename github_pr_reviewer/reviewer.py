# This script will contain the core logic for reviewing GitHub PRs.
# It will use AI to analyze changes and generate inline comments.

import os
import requests
# import argparse # No longer needed for CLI args
# from dotenv import load_dotenv # No longer needed for direct .env loading
from openai import AzureOpenAI
import gradio as gr
import tempfile # For temporary markdown file

# --- Core Logic Functions (Refactored) ---

def parse_pr_url(pr_url):
    """Extracts owner, repo, and PR number from a GitHub PR URL."""
    if not pr_url: return None, None, None
    parts = pr_url.strip("/").split("/")
    if len(parts) < 4 or parts[-2] != "pull":
        return None, None, None
    try:
        owner = parts[-4]
        repo = parts[-3]
        pr_number = int(parts[-1])
        return owner, repo, pr_number
    except (ValueError, IndexError):
        return None, None, None

def get_pr_details(owner, repo, pr_number, github_token):
    """Fetches PR details from the GitHub API."""
    if not all([owner, repo, pr_number, github_token]):
        return None, "Missing owner, repo, PR number, or GitHub token."
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching PR details: {e}"

def get_pr_diff(owner, repo, pr_number, github_token):
    """Fetches PR diff from the GitHub API."""
    if not all([owner, repo, pr_number, github_token]):
        return None, "Missing owner, repo, PR number, or GitHub token for diff."
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching PR diff: {e}"

def initialize_azure_openai_client(api_key, azure_endpoint, api_version):
    """Initializes and returns an AzureOpenAI client."""
    if not all([api_key, azure_endpoint, api_version]):
        return None, "Azure OpenAI environment variables (API_KEY, ENDPOINT, API_VERSION) not fully set."
    try:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version
        )
        return client, None
    except Exception as e:
        return None, f"Error initializing Azure OpenAI client: {e}"

def construct_review_prompt(pr_details, pr_diff):
    """Constructs a prompt for Azure OpenAI to review the PR."""
    title = pr_details.get('title', 'N/A')
    description = pr_details.get('body', 'No description provided.')
    max_diff_chars = 10000
    truncated_diff = pr_diff
    if len(pr_diff or "") > max_diff_chars:
        truncated_diff = (pr_diff or "")[:max_diff_chars] + "\n... (diff truncated due to length)"

    prompt = f"""\
Please review the following GitHub Pull Request as an expert software engineer.
Provide constructive feedback, identify potential bugs, suggest improvements, and comment on code style and best practices.
Format your review as a Markdown document. Pay close attention to the diff and how it relates to the PR title and description.

PR Title: {title}

PR Description:
{description}

PR Diff:
```diff
{truncated_diff}
```

Review:
"""
    return prompt

def get_ai_review(client, prompt, model_id):
    """Sends the prompt to Azure OpenAI and returns the generated review."""
    if not client:
        return None, "Azure OpenAI client not initialized."
    if not model_id:
        return None, "AZURE_OPENAI_MODEL_ID not set."
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are an expert software engineer providing a code review."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000, # Increased max_tokens for potentially longer reviews
        )
        review = response.choices[0].message.content
        return review, None
    except Exception as e:
        return None, f"Error getting review from Azure OpenAI: {e}"

def save_review_to_markdown_tempfile(review_content):
    """Saves the review content to a temporary Markdown file and returns its path."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".md") as tmp_file:
            tmp_file.write(review_content)
            return tmp_file.name, None
    except IOError as e:
        return None, f"Error saving review to temporary Markdown file: {e}"

def post_general_pr_comment(owner, repo, pr_number, comment_body, github_token):
    """Posts a general comment to the PR."""
    if not all([owner, repo, pr_number, github_token]):
        return False, "Missing owner, repo, PR number, or GitHub token for posting comment."
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": comment_body}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True, f"Comment posted successfully to PR #{pr_number}."
    except requests.exceptions.RequestException as e:
        error_message = f"Error posting comment to PR #{pr_number}: {e}"
        if response is not None:
            error_message += f" Status: {response.status_code}, Response: {response.text}"
        return False, error_message

# --- Gradio UI and Logic ---

# Global dictionary to store configuration (acting as a simple in-memory store for the session)
# In a more complex app, consider gr.State or a dedicated class for state management.
APP_CONFIG = {
    "GITHUB_TOKEN": None,
    "AZURE_OPENAI_API_KEY": None,
    "AZURE_OPENAI_ENDPOINT": None,
    "AZURE_OPENAI_MODEL_ID": None,
    "AZURE_OPENAI_API_VERSION": None,
}

def save_configuration(gh_token, az_api_key, az_endpoint, az_model_id, az_api_version):
    APP_CONFIG["GITHUB_TOKEN"] = gh_token
    APP_CONFIG["AZURE_OPENAI_API_KEY"] = az_api_key
    APP_CONFIG["AZURE_OPENAI_ENDPOINT"] = az_endpoint
    APP_CONFIG["AZURE_OPENAI_MODEL_ID"] = az_model_id
    APP_CONFIG["AZURE_OPENAI_API_VERSION"] = az_api_version
    # Try to load .env file as a fallback if some fields are empty
    # This is a bit of a hybrid approach. Pure UI-driven config might skip this.
    # from dotenv import load_dotenv
    # load_dotenv()
    # for key in APP_CONFIG:
    #     if APP_CONFIG[key] is None or APP_CONFIG[key] == "":
    #         APP_CONFIG[key] = os.getenv(key)

    missing_configs = [key for key, value in APP_CONFIG.items() if value is None or value == ""]
    if not missing_configs:
        return "Configuration saved successfully for this session."
    else:
        return f"Configuration saved, but some fields are still missing: {', '.join(missing_configs)}. Please fill them or ensure they are in a .env file if you want to use .env fallback (currently disabled)."

def generate_review_logic(pr_url, post_comment_bool):
    """Handles the logic for the 'Generate Review' button."""
    # Check if config is complete
    required_configs = [
        "GITHUB_TOKEN", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_MODEL_ID", "AZURE_OPENAI_API_VERSION"
    ]
    missing = [key for key in required_configs if not APP_CONFIG.get(key)]
    if missing:
        return f"Error: Configuration is incomplete. Please set these values in the Configuration tab: {', '.join(missing)}", None, "Configuration Error"

    status_updates = ["Starting review process..."]

    owner, repo, pr_number = parse_pr_url(pr_url)
    if not all([owner, repo, pr_number]):
        return "Error: Invalid PR URL. Expected format: https://github.com/owner/repo/pull/number", None, "\n".join(status_updates) + "\nError: Invalid PR URL."

    status_updates.append(f"Parsed PR URL: {owner}/{repo}#{pr_number}")

    github_token = APP_CONFIG["GITHUB_TOKEN"]
    pr_details, err = get_pr_details(owner, repo, pr_number, github_token)
    if err:
        return f"Error fetching PR details: {err}", None, "\n".join(status_updates) + f"\nError: {err}"
    status_updates.append(f"Fetched PR Details: {pr_details.get('title')}")

    pr_diff, err = get_pr_diff(owner, repo, pr_number, github_token)
    if err:
        return f"Error fetching PR diff: {err}", None, "\n".join(status_updates) + f"\nError: {err}"
    status_updates.append("Fetched PR Diff.")

    azure_client, err = initialize_azure_openai_client(
        APP_CONFIG["AZURE_OPENAI_API_KEY"],
        APP_CONFIG["AZURE_OPENAI_ENDPOINT"],
        APP_CONFIG["AZURE_OPENAI_API_VERSION"]
    )
    if err:
        return f"Error initializing Azure OpenAI client: {err}", None, "\n".join(status_updates) + f"\nError: {err}"
    status_updates.append("Azure OpenAI client initialized.")

    review_prompt = construct_review_prompt(pr_details, pr_diff)
    # Simple truncation, could be smarter
    max_prompt_length = 15000
    if len(review_prompt) > max_prompt_length:
        status_updates.append(f"Warning: Prompt is very long ({len(review_prompt)} chars), truncating to {max_prompt_length} chars.")
        review_prompt = review_prompt[:max_prompt_length]

    status_updates.append("Generating AI review...")
    ai_review, err = get_ai_review(azure_client, review_prompt, APP_CONFIG["AZURE_OPENAI_MODEL_ID"])
    if err:
        return f"Error getting AI review: {err}", None, "\n".join(status_updates) + f"\nError: {err}"
    status_updates.append("AI Review generated.")

    md_filepath, err = save_review_to_markdown_tempfile(ai_review)
    if err:
        return f"Error saving review to file: {err}", None, "\n".join(status_updates) + f"\nError: {err}"
    status_updates.append(f"Review saved to temporary file: {md_filepath}")

    final_message = "Review generation complete."
    if post_comment_bool:
        status_updates.append("Posting comment to GitHub PR...")
        success, msg = post_general_pr_comment(owner, repo, pr_number, ai_review, github_token)
        status_updates.append(msg)
        final_message += f" GitHub Comment Status: {msg}"

    return ai_review, md_filepath, "\n".join(status_updates)


# (Main Interface to be implemented in subsequent steps)

# --- Gradio Interface Definition ---

def create_gradio_interface():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# GitHub PR AI Reviewer")

        with gr.Tab("Review"):
            status_text_review = gr.Textbox(label="Status", interactive=False, lines=3)
            pr_url_input = gr.Textbox(label="GitHub PR URL", placeholder="e.g., https://github.com/owner/repo/pull/123")
            post_comment_checkbox = gr.Checkbox(label="Post review as a comment on PR", value=False)
            generate_button = gr.Button("Generate Review", variant="primary")

            gr.Markdown("## Generated Review")
            review_output_markdown = gr.Markdown()
            download_file_output = gr.File(label="Download Review (.md)")

            generate_button.click(
                fn=generate_review_logic,
                inputs=[pr_url_input, post_comment_checkbox],
                outputs=[review_output_markdown, download_file_output, status_text_review]
            )

        with gr.Tab("Configuration"):
            status_text_config = gr.Textbox(label="Status", interactive=False)
            gh_token_input = gr.Textbox(label="GitHub Token", type="password", placeholder="ghp_...")
            az_api_key_input = gr.Textbox(label="Azure OpenAI API Key", type="password")
            az_endpoint_input = gr.Textbox(label="Azure OpenAI Endpoint", placeholder="https://your-resource.openai.azure.com/")
            az_model_id_input = gr.Textbox(label="Azure OpenAI Model ID (Deployment Name)", placeholder="gpt-4-turbo")
            az_api_version_input = gr.Textbox(label="Azure OpenAI API Version", placeholder="2024-02-01")
            save_config_button = gr.Button("Save Configuration for Session", variant="primary")

            save_config_button.click(
                fn=save_configuration,
                inputs=[gh_token_input, az_api_key_input, az_endpoint_input, az_model_id_input, az_api_version_input],
                outputs=status_text_config
            )
            gr.Markdown("Note: Configuration is saved for the current session only.")
            gr.Markdown("You can also set these values in a `.env` file, but values entered here will take precedence if filled. The script currently does not automatically use `.env` values if fields here are left blank after initial load; this behavior might be adjusted in future versions.")


        # Attempt to load initial config from .env if available, but UI takes precedence
        # This is a simple way to pre-fill if .env exists but let UI override.
        # More sophisticated .env handling could be added.
        try:
            from dotenv import load_dotenv
            if load_dotenv():
                print("Loaded .env file for initial configuration values (UI will override).")
                gh_token_input.value = APP_CONFIG["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN", "")
                az_api_key_input.value = APP_CONFIG["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY", "")
                az_endpoint_input.value = APP_CONFIG["AZURE_OPENAI_ENDPOINT"] = os.getenv("AZURE_OPENAI_ENDPOINT", "")
                az_model_id_input.value = APP_CONFIG["AZURE_OPENAI_MODEL_ID"] = os.getenv("AZURE_OPENAI_MODEL_ID", "")
                az_api_version_input.value = APP_CONFIG["AZURE_OPENAI_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION", "")
                # Update APP_CONFIG directly after loading from .env
                save_configuration(APP_CONFIG["GITHUB_TOKEN"], APP_CONFIG["AZURE_OPENAI_API_KEY"],
                                   APP_CONFIG["AZURE_OPENAI_ENDPOINT"], APP_CONFIG["AZURE_OPENAI_MODEL_ID"],
                                   APP_CONFIG["AZURE_OPENAI_API_VERSION"])
        except ImportError:
            print("python-dotenv not installed, .env file will not be loaded automatically for initial values.")
        except Exception as e:
            print(f"Error loading .env for initial values: {e}")


    return demo

if __name__ == "__main__":
    # load_dotenv() # Ensure .env is loaded if present for initial config values.
    # No, moved dotenv loading inside create_gradio_interface for better control

    interface = create_gradio_interface()
    interface.launch()
