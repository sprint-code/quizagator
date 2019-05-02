"""Student endpoints"""
import flask

from flask import current_app as app
from . import db_connect as db
from . import grade


@app.route("/students/")
@db.validate_student
def student_home():
    """Student default page"""
    return flask.render_template(
        "/students/index.html", classes=db.get_student_classes()
    )


@app.route("/students/classes/")
@db.validate_student
def student_classes_home():
    """Student classes page"""
    return flask.render_template(
        "/students/classes.html", classes=db.get_student_classes()
    )


@app.route("/students/classes/join/", methods=["POST"])
@db.validate_student
def student_class_join():
    """If student joins a class"""
    db.insert_db(
        "INSERT INTO roster (person_id, class_id) VALUES (?, ?);",
        [flask.session["id"], flask.request.form["id"]],
    )
    flask.flash(f"You joined the class with an id of {flask.request.form['id']}")
    return flask.redirect("/students/classes")


@app.route("/students/classes/<class_id>/")
@db.validate_student
def student_class_page(class_id):
    """Show classes"""
    class_name = db.query_db(
        "SELECT name FROM classes WHERE class_id=?;", [class_id], one=True
    )
    return flask.render_template(
        "/students/class_page.html",
        class_id=class_id,
        class_name=str(class_name[0]),
        quizzes=db.get_class_quizzes(class_id),
        grades=db.get_student_grade(class_id),
    )


@app.route("/students/classes/<class_id>/quizzes/<quiz_id>/")
@db.validate_student
def student_quiz_page(class_id, quiz_id):
    """Allows students to view/take quizzes"""
    quiz_name = str(
        db.query_db(
            "SELECT name FROM quizzes WHERE quiz_id=? AND class_id=?;",
            [quiz_id, class_id],
        )[0][0]
    )
    result = db.query_db(
        "SELECT grade from quiz_grades WHERE quiz_id=? AND student_id=?;",
        [quiz_id, flask.session["id"]],
        one=True,
    )
    # check if the person has already completed the test
    if result is None:
        questions_db = db.query_db(
            "SELECT question_id, question_type, question_text, a_text, b_text,"
            " c_text, d_text, correct_answer FROM questions WHERE quiz_id=?;",
            [quiz_id],
        )
        questions = []
        for question in questions_db:
            question_info = {}
            question_info["id"] = question[0]
            question_info["type"] = question[1]
            question_info["text"] = question[2]
            # if this is a multiple-choice question
            if question[0] == 1:
                question_info["answers"] = {}
                question_info["answers"]["a"] = question[3]
                question_info["answers"]["b"] = question[4]
                question_info["answers"]["c"] = question[5]
                question_info["answers"]["d"] = question[6]
            questions.append(question_info)
        return flask.render_template(
            "/students/quiz_page.html",
            questions=questions,
            quiz_name=quiz_name,
            quiz_id=quiz_id,
            class_id=class_id,
        )

    flask.flash(f"You receieved {result[0]} on this quiz.")
    return flask.render_template("/students/quiz_page.html", quiz_name=quiz_name)


@app.route(
    "/students/classes/<class_id>/quizzes/<quiz_id>/grade/", methods=["GET", "POST"]
)
@db.validate_student
def student_grade_quiz(class_id, quiz_id):
    """Show or calculate a student's grade on a quiz"""
    # display grades
    if flask.request.method == "GET":
        quiz_name = str(
            db.query_db(
                "SELECT name FROM quizzes WHERE quiz_id=? AND class_id=?;",
                [quiz_id, class_id],
            )[0][0]
        )
        result = db.query_db(
            "SELECT grade from quiz_grades WHERE quiz_id=? AND student_id=?;",
            [quiz_id, flask.session["id"]],
            one=True,
        )

        return flask.render_template(
            "/students/quiz_grade.html", quiz_name=quiz_name, grade=result[0]
        )

    # process quiz form from POST request
    answers = flask.request.form.to_dict()

    print(answers)

    # insert answers into quiz_responses table -- for each question answer, do:
    for question_id in answers:
        response = answers[question_id]
        db.insert_db(
            "INSERT INTO quiz_responses (student_id, quiz_id, question_id,"
            " response) VALUES (?, ?, ?, ?)",
            [flask.session["id"], quiz_id, question_id, response],
        )

    # grade answers (handoff to grade.py)
    grade_result = grade.grade(quiz_id, answers.items())

    # insert grading text result into quiz_grades table
    # optionally also go back and set the "grade" entry in quiz_responses
    # for a per-answer grade (not planned for this iteration)
    db.insert_db(
        "INSERT INTO quiz_grades (student_id, quiz_id, grade) VALUES (?, ?, ?)",
        [flask.session["id"], quiz_id, str(grade_result)],
    )

    # redirect to grade viewing page
    return flask.redirect(f"/students/classes/{class_id}/quizzes/{quiz_id}/grade/")
