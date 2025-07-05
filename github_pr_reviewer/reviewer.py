# This script will contain the core logic for reviewing GitHub PRs.
# It will use AI to analyze changes and generate inline comments.

import os
import requests
import argparse
from dotenv import load_dotenv
from openai import AzureOpenAI

def main():
    load_dotenv() # Load environment variables from .env file

    parser = argparse.ArgumentParser(description="Automated GitHub PR Reviewer")
    parser.add_argument("pr_url", help="The URL of the GitHub Pull Request to review.")
    args = parser.parse_args()

    pr_url = args.pr_url
    print(f"Starting PR review process for: {pr_url}")

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN not found in environment variables.")
        return

    owner, repo, pr_number = parse_pr_url(pr_url)
    if not all([owner, repo, pr_number]):
        print("Error: Could not parse PR URL. Expected format: https://github.com/owner/repo/pull/number")
        return

    print(f"Fetching details for PR: {owner}/{repo}#{pr_number}")

    pr_details = get_pr_details(owner, repo, pr_number, github_token)
    if not pr_details:
        return

    pr_diff = get_pr_diff(owner, repo, pr_number, github_token)
    if not pr_diff:
        return

    print(f"PR Title: {pr_details.get('title')}")
    # print(f"PR Diff:\n{pr_diff}") # Potentially very long

    # Initialize Azure OpenAI client
    azure_openai_client = initialize_azure_openai()
    if not azure_openai_client:
        return

    # Construct prompt and get review
    print("Generating review comments with Azure OpenAI...")
    review_prompt = construct_review_prompt(pr_details, pr_diff)

    # Truncate prompt if too long (OpenAI has token limits)
    # A more sophisticated approach would be to summarize diffs or process in chunks
    max_prompt_length = 15000 # Approximate character limit, adjust as needed
    if len(review_prompt) > max_prompt_length:
        print(f"Warning: Prompt is very long ({len(review_prompt)} chars), truncating to {max_prompt_length} chars.")
        review_prompt = review_prompt[:max_prompt_length]

    ai_review = get_ai_review(azure_openai_client, review_prompt)

    if ai_review:
        print("\nAI Generated Review (preview):")
        print(ai_review[:500] + "..." if len(ai_review) > 500 else ai_review) # Preview long reviews

        # Save review to Markdown file
        md_filename = f"review_PR_{pr_number}.md"
        save_review_to_markdown(ai_review, md_filename)
        print(f"\nFull review saved to: {md_filename}")

        # Ask for approval to post to GitHub
        user_approval = input("Do you want to post this review as inline comments to the PR? (yes/no): ")
        if user_approval.lower() == 'yes':
            print("Attempting to post comments to GitHub...")
            success = post_general_pr_comment(owner, repo, pr_number, ai_review, github_token)
            if success:
                print("Successfully posted the review as a general comment on the PR.")
            else:
                print("Failed to post the review to the PR. The review is saved locally.")
        else:
            print("Review will not be posted to GitHub.")
    else:
        print("Failed to get review from Azure OpenAI.")

    print("PR review process finished.")

def save_review_to_markdown(review_content, filename):
    """Saves the review content to a Markdown file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(review_content)
        print(f"Review successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving review to Markdown file {filename}: {e}")

def post_general_pr_comment(owner, repo, pr_number, comment_body, token):
    """Posts a general comment to the PR, not inline."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": comment_body}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Comment posted successfully to PR #{pr_number}.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment to PR #{pr_number}: {e}")
        if response is not None:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
        return False

def initialize_azure_openai():
    """Initializes and returns an AzureOpenAI client."""
    try:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if not all([api_key, azure_endpoint, api_version]):
            print("Error: Azure OpenAI environment variables (API_KEY, ENDPOINT, API_VERSION) not fully set.")
            return None

        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version
        )
        return client
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {e}")
        return None

def construct_review_prompt(pr_details, pr_diff):
    """Constructs a prompt for Azure OpenAI to review the PR."""
    title = pr_details.get('title', 'N/A')
    description = pr_details.get('body', 'No description provided.')
    # Limit diff length in prompt to avoid exceeding token limits
    # A more robust solution would involve chunking or summarizing large diffs.
    max_diff_chars = 10000
    truncated_diff = pr_diff
    if len(pr_diff) > max_diff_chars:
        truncated_diff = pr_diff[:max_diff_chars] + "\n... (diff truncated due to length)"

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

def get_ai_review(client, prompt):
    """Sends the prompt to Azure OpenAI and returns the generated review."""
    try:
        model_id = os.getenv("AZURE_OPENAI_MODEL_ID")
        if not model_id:
            print("Error: AZURE_OPENAI_MODEL_ID not set in environment variables.")
            return None

        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are an expert software engineer providing a code review."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, # Adjust for creativity vs. precision
            max_tokens=1500, # Adjust as needed
        )
        review = response.choices[0].message.content
        return review
    except Exception as e:
        print(f"Error getting review from Azure OpenAI: {e}")
        return None

def parse_pr_url(pr_url):
    """Extracts owner, repo, and PR number from a GitHub PR URL."""
    parts = pr_url.strip("/").split("/")
    if len(parts) < 4 or parts[-2] != "pull":
        return None, None, None
    try:
        owner = parts[-4]
        repo = parts[-3]
        pr_number = int(parts[-1])
        return owner, repo, pr_number
    except ValueError:
        return None, None, None

def get_pr_details(owner, repo, pr_number, token):
    """Fetches PR details from the GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PR details: {e}")
        return None

def get_pr_diff(owner, repo, pr_number, token):
    """Fetches PR diff from the GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"  # Request diff format
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PR diff: {e}")
        return None

if __name__ == "__main__":
    main()
