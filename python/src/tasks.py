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
- Calculate overallScore as the average of:
  logicalThinking,
  specificity,
  communication,
  jobFit,
  and starStructure.

Output Format

Return ONLY valid JSON.

{
  "overallScore": 0,

  "summary": "",

  "evaluationScores": {
    "logicalThinking": {
      "score": 0,
      "feedback": ""
    },
    "specificity": {
      "score": 0,
      "feedback": ""
    },
    "communication": {
      "score": 0,
      "feedback": ""
    },
    "jobFit": {
      "score": 0,
      "feedback": ""
    },
    "starStructure": {
      "score": 0,
      "feedback": ""
    }
  },

  "strengths": [
    ""
  ],

  "weaknesses": [
    ""
  ]
}

Rules

- Return JSON only.
- Do not use markdown.
- Do not wrap with ```json.
- No explanations outside JSON.
""",

    expected_output="""
A valid JSON object containing:

overallScore

summary

evaluationScores
- logicalThinking
- specificity
- communication
- jobFit
- starStructure

strengths

weaknesses
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
""",

    expected_output="""
Return the reviewed evaluation in exactly the same JSON format received from the Answer Evaluation task.

Do not remove fields.

Only improve consistency, objectivity, and clarity.
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
- Do NOT repeat strengths, weaknesses, scores, or detailed evaluation feedback.

Improvement Tips Rules

- Write all improvement tips in {native_language}.
- Provide at most FOUR improvement tips.
- Keep each tip concise (maximum 2 sentences).
- Prioritize the most important improvements first.
- Base every improvement tip on the reviewed evaluation.
- Avoid repeating similar advice.
- Explain why each improvement is important for interviews in {country}.

Model Answer Rules

- Generate an improved version of the candidate's original answer.
- Preserve the candidate's original experience whenever possible.
- Do NOT invent new experiences, projects, achievements, or technologies that were not mentioned.
- Never invent numbers, percentages, metrics, dates, project names, technologies, awards, or achievements that were not explicitly mentioned by the candidate.
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

Return ONLY valid JSON.

{
  "overallSummary": "",

  "improvementTips": [
    ""
  ],

  "modelAnswer": {
    "nativeLanguage": "",
    "targetLanguage": ""
  },

  "nextPracticeQuestion": {
    "targetLanguage": "",
    "nativeLanguage": ""
  }
}

Rules

- Return JSON only.
- Do not use markdown.
- Do not wrap with ```json.
- No explanations outside JSON.
""",

    expected_output="""
A valid JSON object containing:

overallSummary

improvementTips

modelAnswer
- nativeLanguage
- targetLanguage

nextPracticeQuestion
- targetLanguage
- nativeLanguage
""",

    agent=interview_coach,

    context=[
        question_analysis_task,
        reflection_task
    ]
)