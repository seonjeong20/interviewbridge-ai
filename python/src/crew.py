from crewai import Crew, Process

from src.agents import (
    question_generator,
    question_analyzer,
    answer_evaluator,
    reflection_agent,
    interview_coach
)

from src.tasks import (
    question_generation_task,
    question_analysis_task,
    answer_evaluation_task,
    reflection_task,
    interview_coaching_task
)

# ==========================================================
# Interview Question Crew
# ==========================================================

question_crew = Crew(
    agents=[
        question_generator
    ],

    tasks=[
        question_generation_task
    ],

    process=Process.sequential,

    verbose=True
)


# ==========================================================
# Interview Evaluation Crew
# ==========================================================

evaluation_crew = Crew(
    agents=[
        question_analyzer,
        answer_evaluator,
        reflection_agent,
        interview_coach
    ],

    tasks=[
        question_analysis_task,
        answer_evaluation_task,
        reflection_task,
        interview_coaching_task
    ],

    process=Process.sequential,

    verbose=True
)