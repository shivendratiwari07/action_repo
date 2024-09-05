import argparse
import os
from datetime import datetime
import requests
import tiktoken

MAX_TOKENS = 1000
DEFAULT_TIMEOUT = 20

def chunk_text_by_tokens(text, max_tokens, tokenizer):
    """Chunks text into manageable sizes based on token count."""
    tokens = tokenizer.encode(text)
    token_chunks = [tokens[i:i + max_tokens] for i in range(0, len(tokens), max_tokens)]
    return [tokenizer.decode(chunk) for chunk in token_chunks]

def get_failed_steps(owner, repo, run_id, headers):
    """Fetch failed steps from a GitHub actions run."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    try:
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
        failed_steps = extract_failed_steps(jobs, owner, repo)
        return failed_steps
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch failed steps: {e}")
        return []

def extract_failed_steps(jobs, repo_owner, repo_name):
    """Extract failed steps from the jobs data."""
    failed_steps = []
    for job in jobs:
        # Directly use the passed repo_owner and repo_name
        job_logs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/jobs/{job['id']}/logs"
        for step in job.get("steps", []):
            if step.get("conclusion") == "failure":
                failed_steps.append({
                    "job_name": job.get("name", "unknown"),
                    "step_name": step.get("name", "unknown"),
                    "job_logs_url": job_logs_url
                })
    return failed_steps

def download_logs(logs_url, headers, output_filename):
    """Download logs from a given URL and save them to a file."""
    try:
        response = requests.get(logs_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        if not response.content:
            raise ValueError("Received empty content from GitHub API.")
        with open(output_filename, 'wb') as file:
            file.write(response.content)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to download logs: {e}")
        return False

def analyze_logs_with_custom_service(log_chunks, tokenizer):
    """Send log chunks to a custom analysis service."""
    url = "https://www.dex.inside.philips.com/philips-ai-chat/chat/api/user/SendImageMessage"
    headers = {
        'Cookie': os.getenv('CUSTOM_SERVICE_COOKIE'),
        'Content-Type': 'application/json'
    }
    combined_logs = "\n".join(log_chunks)
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Provide only a summary of the root cause of the job failure. "
                                "Print the file name, line number and code exactly where job failed:\n\n"
                                + combined_logs
                    }
                ]
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        print(f"Raw response content: {response.text}")
        analysis_result = response.json()
        summary = analysis_result.get('choices', [{}])[0].get('message', {}).get('content', 'No summary available')
        return summary
    except requests.exceptions.RequestException as e:
        print(f"Failed to analyze logs: {e}")
        return "Analysis failed due to a request error."

def process_failed_step(step, headers, tokenizer):
    """Process a single failed step: download logs, analyze them, and save the results."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_filename = f"{step['job_name']}_{step['step_name']}_logs_{timestamp}.txt"
    if not download_logs(step["job_logs_url"], headers, log_filename):
        print(f"Failed to download logs for {step['job_name']} - {step['step_name']}")
        return

    try:
        with open(log_filename, 'r', encoding='utf-8') as file:
            log_content = file.read()

        log_chunks = chunk_text_by_tokens(log_content, MAX_TOKENS, tokenizer)
        summary = analyze_logs_with_custom_service(log_chunks, tokenizer)

        print(summary)

        print(f"Current working directory before saving file: {os.getcwd()}")
        analysis_filename = f"./action_repo/.github/actions/script/{step['job_name']}_analysis_{timestamp}.txt"
        with open(analysis_filename, 'w', encoding='utf-8') as analysis_file:
            analysis_file.write(f"Job Name: {step['job_name']}\n")
            analysis_file.write(summary)

        print(f"Analysis saved to {analysis_filename}")

    except (FileNotFoundError, IOError) as e:
        print(f"Failed to analyze logs for {log_filename}: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=False, help='The GITHUB_RUN_ID to use')
    args = parser.parse_args()

    run_id = args.run_id or os.getenv('GITHUB_RUN_ID')
    repo_owner = os.getenv('REPO_OWNER')
    repo_name = os.getenv('REPO_NAME')
    token = os.getenv('GITHUB_TOKEN')

    print(f"repo_owner: {repo_owner}")
    print(f"repo_name: {repo_name}")
    print(f"run_id: {run_id}")
    print(f"token: {token}")

    if not all([repo_owner, repo_name, run_id, token]):
        raise ValueError("REPO_OWNER, REPO_NAME, GITHUB_RUN_ID, and GITHUB_TOKEN must be set")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    failed_steps = get_failed_steps(repo_owner, repo_name, run_id, headers)
    if not failed_steps:
        print("No failed steps found.")
        return

    tokenizer = tiktoken.get_encoding("cl100k_base")

    for step in failed_steps:
        process_failed_step(step, headers, tokenizer)

if __name__ == "__main__":
    main()
