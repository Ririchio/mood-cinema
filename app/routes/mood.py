from flask import Blueprint, redirect, render_template, request, url_for

from app.extensions import db
from app.services.mood_questions import get_mood_questions
from app.services.recommendation import (
    create_mood_profile,
    extract_answers,
    get_recommendations,
)

mood_bp = Blueprint("mood", __name__, url_prefix="/mood")


@mood_bp.route("/", methods=["GET"])
def form():
    questions = get_mood_questions()

    return render_template(
        "mood.html",
        questions=questions,
    )


@mood_bp.route("/result", methods=["POST"])
def result():
    answers = extract_answers(request.form)

    if not answers.get("main_state") or not answers.get("mood_direction"):
        return redirect(url_for("mood.form"))

    mood_profile = create_mood_profile(answers)

    db.session.add(mood_profile)
    db.session.commit()

    recommendation_result = get_recommendations(mood_profile)

    return render_template(
        "mood_result.html",
        result=recommendation_result,
    )