import pylint.lint
from pylint.reporters.text import TextReporter
import io
import os
import subprocess

def clean_text(text):
    """Clean the text to remove any hidden characters, color codes, or extra spaces."""
    return text.strip()

def extract_score_from_line(line):
    """Extracts the score from the line that contains 'rated at'."""
    print(f"Extracting score from line: '{line}'")
    try:
        
        parts = line.split("rated at")
        if len(parts) > 1:
            score_part = parts[1].split("/")[0].strip()
            print(f"Extracted score part: '{score_part}'")
            score = float(score_part)
            print(f"Successfully converted to float: {score}")
            return score
        else:
            print("Failed to find the 'rated at' part in the line.")
    except Exception as e:
        print(f"Error extracting score from line: {e}")
    return 0

def run_bandit_security_check():
    """Run Bandit to perform security checks on the code."""
    print("Running Bandit for security checks...")
    result = subprocess.run(['bandit', '-r', '../script/'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Bandit found potential security issues. Please review the report above.")
    else:
        print("No security issues found by Bandit.")

def test_script_with_pylint():
    """Run Pylint on the log analysis script and check for compliance."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, '../script/log_analysis.py')

    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script file not found at {script_path}")

    pylint_args = [
        script_path,
        '--disable=C0114,C0116',
        '--output-format=colorized'
    ]

    pylint_output = io.StringIO()
    reporter = TextReporter(output=pylint_output)
    
    # Run Pylint and capture the output
    pylint.lint.Run(pylint_args, reporter=reporter, exit=False)

    # Read the Pylint output
    pylint_output.seek(0)
    report = pylint_output.read()
    print(report)

    # Clean the report to remove any non-visible characters that might affect matching
    cleaned_report = clean_text(report)

    # Attempt to extract the score from the cleaned report
    score = 0
    try:
        lines = cleaned_report.splitlines()
        for line in lines:
            print(f"DEBUG LINE: {line.strip()}")
            # Check if the line contains the score
            if "Your code has been rated at" in line:
                print(f"POTENTIAL MATCH LINE: {line.strip()}")
                score = extract_score_from_line(line)
                if score > 0:
                    break  # Stop after finding the first valid score
    except Exception as e:
        print(f"Error parsing the score: {e}")


    # Run Bandit for security checks
    run_bandit_security_check()

if __name__ == "__main__":
    test_script_with_pylint()
