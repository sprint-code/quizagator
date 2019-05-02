"""Grade student responses by handing off determinations to user code"""

import subprocess

from typing import List, Tuple
from . import db_connect as db


def grade(quiz_id, answer_list: List[Tuple[int, str]]) -> str:
    """
    Grade a single student's quiz

    This method runs an uploaded python file. This file is not checked for
    security issues, and could result in changes to the entire server. However,
    the server itself is run inside a docker container in production, and so
    actual malicious effects can be cleared fairly easily; the only malicious
    action that may need manual intervention is dropping databases.
    """

    report = ""
    for (question_type, answer) in answer_list:
        report += f"{question_type}:{answer}\n"

    # Look into edx/codejail for actual sandboxing in the future
    grader = db.query_db("SELECT grader FROM quizzes WHERE quiz_id=?", [quiz_id])[0][0]

    print(f"Running python:\n{grader}")
    result = subprocess.Popen(
        ["python", "-c", grader],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output = result.communicate(report)

    print(f"Grading stderr:\n{output[1]}")
    print(f"Grading stdout:\n{output[0]}")

    actual_grade = str(output[0])
    if result.returncode != 0:
        actual_grade = "Error during grading"
    elif not actual_grade:
        actual_grade = "No grade calculated"

    return actual_grade


def verify_python(source) -> str:
    """Verify a python file is correctly written"""
    compile(source, "<string>", "exec", dont_inherit=True)
