import pylint.lint
from pylint.reporters.text import TextReporter
import io
import os

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
    

    pylint.lint.Run(pylint_args, reporter=reporter, exit=False)


    pylint_output.seek(0)
    report = pylint_output.read()
    print(report)


    cleaned_report = clean_text(report)

    score = 0
    try:
        lines = cleaned_report.splitlines()
        for line in lines:
            print(f"DEBUG LINE: {line.strip()}")
            if "Code has been rated at" in line:
                print(f"POTENTIAL MATCH LINE: {line.strip()}")
                score = extract_score_from_line(line)
                if score > 0:
                    break
    except Exception as e:
        print(f"Error parsing the score: {e}")

if __name__ == "__main__":
    test_script_with_pylint()
