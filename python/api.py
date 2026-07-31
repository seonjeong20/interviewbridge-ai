import json

from fastapi import FastAPI

from schemas import (
    QuestionRequest,
    QuestionResponse,
    EvaluationRequest
)

from src.crew import question_crew, evaluation_crew
from src.config import COUNTRY_PROFILE

app = FastAPI(
    title="InterviewBridge AI API"
)


@app.get("/")
def root():
    return {
        "message": "InterviewBridge AI API is running."
    }


# ==========================================================
# Generate Interview Question
# ==========================================================

@app.post("/generate-question", response_model=QuestionResponse)
def generate_question(request: QuestionRequest):

    profile = COUNTRY_PROFILE[request.country]

    result = question_crew.kickoff(
        inputs={
            "job": request.job,
            "country": request.country,
            "native_language": request.native_language,
            "target_language": profile["language"],
            "culture": profile["culture"],
            "style": profile["style"]
        }
    )

    return QuestionResponse(
        question=str(result)
    )


# ==========================================================
# Analyze Interview Answer
# ==========================================================

@app.post("/analyze")
def analyze(request: EvaluationRequest):

    profile = COUNTRY_PROFILE[request.country]

    result = evaluation_crew.kickoff(
        inputs={
            "job": request.job,
            "country": request.country,
            "native_language": request.native_language,
            "target_language": profile["language"],
            "culture": profile["culture"],
            "style": profile["style"],
            "question": request.question,
            "answer": request.answer
        }
    )

    evaluation = None
    coaching = None

    for task in result.tasks_output:

        if task.agent == "Interview Evaluation Reviewer":
            evaluation = json.loads(task.raw)

        elif task.agent == "Global Interview Coach":
            coaching = json.loads(task.raw)

    return {
        "overallScore": evaluation["overallScore"],

        "question": request.question,
        "answer": request.answer,

        "evaluation": {
            "summary": evaluation["summary"],
            "evaluationScores": evaluation["evaluationScores"],
            "strengths": evaluation["strengths"],
            "weaknesses": evaluation["weaknesses"]
        },

        "coaching": coaching
    }