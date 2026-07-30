import { useLocation } from "react-router-dom";
import "./Result.css";

function Result() {
  const location = useLocation();

  const { job,  question, answer, analysisResult} = location.state

  return (
    <div className="result-page">
      <main className="result-container">
        <header className="result-header">
          <span className="result-eyebrow">AI INTERVIEW ANALYSIS</span>
          <h1>Interview Result</h1>
          <p className="job-title">{job.title}</p>
        </header>

        <section className="score-card">
          <div className="score-heading">
            <h2>Overall Score</h2>
            <span>Interview performance</span>
          </div>
          <p className="score">{analysisResult.score} <span>/ 100</span></p>
          <div
            className="score-progress"
            style={{ "--score": `${analysisResult.score}%` }}
            aria-label={`Overall score: ${analysisResult.score} out of 100`}
          >
            <div className="score-progress-fill" />
          </div>
        </section>

        <div className="response-grid">
          <section className="content-card">
            <h3>Question</h3>
            <p>{question}</p>
          </section>

          <section className="content-card">
            <h3>Your Answer</h3>
            <p>{answer}</p>
          </section>
        </div>

        <section className="feedback-card strength-card">
          <h3><span aria-hidden="true">✅</span> Strength</h3>

          <ul>
            {analysisResult.strengths.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="feedback-card weakness-card">
          <h3><span aria-hidden="true">⚠️</span> Weakness</h3>

          <ul>
            {analysisResult.weaknesses.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="feedback-card improvement-card">
          <h3><span aria-hidden="true">💡</span> Improvement</h3>
          <p>{analysisResult.improvement}</p>
        </section>

        <section className="model-answer-card">
          <h3><span aria-hidden="true">📄</span> Model Answer</h3>
          <p>{analysisResult.modelAnswer}</p>
        </section>
      </main>
    </div>
  );
}

export default Result;
