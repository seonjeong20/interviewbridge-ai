from pydantic import BaseModel
from typing import List

# ==========================================================
# Question
# ==========================================================

class QuestionRequest(BaseModel):
    job: str
    country: str
    native_language: str


class QuestionResponse(BaseModel):
    question: str


# ==========================================================
# Interview Analysis Request
# ==========================================================

class EvaluationRequest(BaseModel):
    job: str
    country: str
    native_language: str
    question: str
    answer: str


# ==========================================================
# Evaluation Models
# ==========================================================

class ScoreDetail(BaseModel):
    score: int
    feedback: str


class EvaluationScores(BaseModel):
    logicalThinking: ScoreDetail
    specificity: ScoreDetail
    communication: ScoreDetail
    jobFit: ScoreDetail
    starStructure: ScoreDetail


class EvaluationResult(BaseModel):
    summary: str
    evaluationScores: EvaluationScores
    strengths: List[str]
    weaknesses: List[str]


# ==========================================================
# Coaching Models
# ==========================================================

class ModelAnswer(BaseModel):
    nativeLanguage: str
    targetLanguage: str


class NextPracticeQuestion(BaseModel):
    nativeLanguage: str
    targetLanguage: str


class CoachingResult(BaseModel):
    overallSummary: str
    improvementTips: List[str]
    modelAnswer: ModelAnswer
    nextPracticeQuestion: NextPracticeQuestion


# ==========================================================
# Final Response
# ==========================================================

class InterviewAnalysisResponse(BaseModel):
    overallScore: int

    question: str
    answer: str

    evaluation: EvaluationResult

    coaching: CoachingResult