from crewai import Task

from src.agents import (
    question_generator,
    question_analyzer,
    answer_evaluator,
    reflection_agent,
    interview_coach
)


# ==========================================================
# 1. Interview Question Generation
# ==========================================================

question_generation_task = Task(
    description="""
Generate ONE realistic interview question.

Job Role:
{job}

Target Country:
{country}

Target Interview Language:
{target_language}

Interview Culture:
{culture}

Communication Style:
{style}

Rules:
- Generate exactly ONE interview question.
- Match the interview style of {country}.
- The interview question must be written in {target_language}.
- Do not generate explanations.
- Do not generate multiple questions.
- Do not generate a model answer.
- Return only the interview question.
""",

    expected_output="""
One interview question in {target_language} only.
""",

    agent=question_generator
)


# ==========================================================
# 2. Interview Question Analysis
# ==========================================================

question_analysis_task = Task(
    description="""
Analyze the generated interview question.

Target Country:
{country}

Interview Culture:
{culture}

Communication Style:
{style}

Return ONLY in {native_language}.

Output Format

Question Intent:
...

Core Competencies:
- ...
- ...

Question Type:
Technical / Behavioral / HR

STAR Recommended:
Yes / No
""",

    expected_output="""
Question Intent

Core Competencies

Question Type

STAR Recommended
""",

    agent=question_analyzer,

    context=[
        question_generation_task
    ]
)


# ==========================================================
# 3. Interview Answer Evaluation
# ==========================================================

answer_evaluation_task = Task(
    description="""
Evaluate the candidate's interview answer.

Question:
{question}

Answer:
{answer}

Target Country:
{country}

Interview Culture:
{culture}

Communication Style:
{style}

Return everything in {native_language}.

Rules

- Evaluate only.
- Never provide coaching.
- Never generate a model answer.
- Never generate another interview question.
- Consider the interview expectations of {country}.
- Always calculate Overall Score.

Output Format

Overall Score: XX

Evaluation Scores

Logical Thinking: X/10

Specificity: X/10

Communication: X/10

Job Fit: X/10

STAR Structure: X/10

Strengths:
- ...

Weaknesses:
- ...
""",

    expected_output="""
Overall Score

Evaluation Scores

Logical Thinking

Specificity

Communication

Job Fit

STAR Structure

Strengths

Weaknesses
""",

    agent=answer_evaluator,

    context=[
        question_generation_task,
        question_analysis_task
    ]
)


# ==========================================================
# 4. Reflection
# ==========================================================

reflection_task = Task(
    description="""
Review the previous evaluation before it is sent to the interview coach.

Do NOT evaluate the interview answer again.

Return everything in {native_language}.

Rules

- Review only the evaluation result.
- Review only the evaluation result.
- Do NOT evaluate the interview answer again.
- Check whether the scores are internally consistent.
- Verify that strengths are supported by the evaluation.
- Verify that weaknesses are supported by the evaluation.
- Remove duplicated or repetitive feedback.
- Make the feedback concise and easy to read.
- If multiple tips describe the same improvement, merge them into one.
- Preserve the original evaluation structure.
- Do not provide coaching.
- Do not generate a model answer.
- Do not generate another interview question.
- Correct any logical inconsistencies.
- Keep the same output format.
- Do not provide coaching.
- Do not generate a model answer.
- Do not generate another interview question.
""",

    expected_output="""
Reviewed Evaluation

Overall Score

Evaluation Scores

Logical Thinking

Specificity

Communication

Job Fit

STAR Structure

Strengths

Weaknesses
""",

    agent=reflection_agent,

    context=[
        answer_evaluation_task
    ]
)


# ==========================================================
# 5. Interview Coaching
# ==========================================================

interview_coaching_task = Task(
    description="""
Provide interview coaching using ONLY the reviewed evaluation.

Target Country:
{country}

Interview Culture:
{culture}

Communication Style:
{style}

Native Language:
{native_language}

Target Interview Language:
{target_language}

Rules

- Do NOT evaluate again.
- Do NOT calculate scores.
- Use ONLY the reviewed evaluation.
- Reflect the interview culture and communication style of {country}.
- Do NOT contradict the reviewed evaluation.

Improvement Tips Rules

- Write all improvement tips in {native_language}.
- Provide at most FOUR improvement tips.
- Keep each tip concise (maximum 2 sentences).
- Prioritize the most important improvements first.
- Avoid repeating similar advice.
- Explain why each improvement is important for interviews in {country}.

Model Answer Rules

- Generate an improved version of the candidate's original answer.
- Preserve the candidate's original experience whenever possible.
- Do NOT invent new experiences, projects, achievements, or technologies that were not mentioned.
- Improve clarity, structure, and professionalism.
- Follow the STAR method naturally when appropriate.
- Keep the answer realistic and interview-ready.
- Generate the model answer in {native_language}.
- Translate it naturally into {target_language}.

Next Practice Question Rules

- Generate exactly ONE follow-up interview question.
- The question should naturally continue from the previous interview topic.
- Do NOT suddenly change to an unrelated topic.
- Write the question in {target_language}.
- Translate the question into {native_language}.

Follow the output format exactly.

Output Format

==============================
Overall Summary
==============================
- Summarize the candidate's overall performance in ONE sentence.

==============================
Improvement Tips
==============================
1.
2.
3.
4.

==============================
Model Answer ({native_language})
==============================
...

==============================
Model Answer ({target_language})
==============================
...

==============================
Next Practice Question ({target_language})
==============================
...

==============================
Question Translation ({native_language})
==============================
...
""",

    expected_output="""
Overall Summary

Improvement Tips

Model Answer (Native Language)

Model Answer (Target Language)

Next Practice Question

Question Translation
""",

    agent=interview_coach,

    context=[
        question_generation_task,
        question_analysis_task,
        reflection_task
    ]
)