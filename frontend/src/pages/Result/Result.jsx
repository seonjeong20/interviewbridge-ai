import { useLocation, useNavigate } from "react-router-dom";
import "./Result.css";

function Result() {
  const location = useLocation();
  const navigate = useNavigate();
  const { job, country, nativeLanguage, result } = location.state ?? {};

  if (!result) {
    return (
      <div className="result-page">
        <main className="result-container">
          <p>분석 결과가 없습니다. 인터뷰를 먼저 진행해 주세요.</p>
        </main>
      </div>
    );
  }

  const { evaluation, coaching } = result;
  const scoreItems = [
    ["Logical Thinking", evaluation.evaluationScores.logicalThinking],
    ["Specificity", evaluation.evaluationScores.specificity],
    ["Communication", evaluation.evaluationScores.communication],
    ["Job Fit", evaluation.evaluationScores.jobFit],
    ["STAR Structure", evaluation.evaluationScores.starStructure],
  ];

  return (
    <div className="result-page">
      <main className="result-container">
        <header className="result-header">
          <span className="result-eyebrow">AI INTERVIEW ANALYSIS</span>
          <h1>Interview Result</h1>
          <p className="job-title">{job?.title}</p>
        </header>

        <section className="score-card">
          <div className="score-heading">
            <h2>Overall Score</h2>
            <span>Interview performance</span>
          </div>
          <p className="score">{result.overallScore} <span>/ 100</span></p>
          <div
            className="score-progress"
            style={{ "--score": `${result.overallScore}%` }}
            aria-label={`Overall score: ${result.overallScore} out of 100`}
          >
            <div className="score-progress-fill" />
          </div>
        </section>

        <div className="response-grid">
          <section className="content-card">
            <h3>Question</h3>
            <p>{result.question}</p>
          </section>

          <section className="content-card">
            <h3>Your Answer</h3>
            <p>{result.answer}</p>
          </section>
        </div>

        <section className="feedback-card improvement-card">
          <h3>Question Summary</h3>
          <p>{evaluation.summary}</p>
        </section>

        <section className="model-answer-card">
          <h3>Evaluation Scores</h3>
          {scoreItems.map(([label, score]) => (
            <div key={label}>
              <h4>{label}</h4>
              <p>{score.score} / 100</p>
              <p>{score.feedback}</p>
            </div>
          ))}
        </section>

        <section className="feedback-card strength-card">
          <h3><span aria-hidden="true">✅</span> Strength</h3>

          <ul>
            {evaluation.strengths.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="feedback-card weakness-card">
          <h3><span aria-hidden="true">⚠️</span> Weakness</h3>

          <ul>
            {evaluation.weaknesses.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="feedback-card improvement-card">
          <h3><span aria-hidden="true">💡</span> Overall Summary</h3>
          <p>{coaching.overallSummary}</p>
        </section>

        <section className="feedback-card improvement-card">
          <h3>Improvement Tips</h3>
          <ul>
            {coaching.improvementTips.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="model-answer-card">
          <h3><span aria-hidden="true">📄</span> Model Answer (Korean)</h3>
          <p>{coaching.modelAnswer.nativeLanguage}</p>
        </section>

        <section className="model-answer-card">
          <h3><span aria-hidden="true">📄</span> Model Answer (Target Language)</h3>
          <p>{coaching.modelAnswer.targetLanguage}</p>
        </section>

        <section className="model-answer-card">
          <h3>Next Practice Question (Target Language)</h3>
          <p>{coaching.nextPracticeQuestion.targetLanguage}</p>
        </section>

        <section className="model-answer-card">
          <h3>Question Translation (Native Language)</h3>
          <p>{coaching.nextPracticeQuestion.nativeLanguage}</p>
        </section>

        <div className="button-container">
          <button
            className="analyze-btn"
            onClick={() =>
              navigate("/interview", {
                state: {
                  job,
                  country,
                  nativeLanguage,
                  question: coaching.nextPracticeQuestion.targetLanguage,
                },
              })
            }
          >
            Next Practice Question
          </button>
        </div>
      </main>
    </div>
  );
}

export default Result;
