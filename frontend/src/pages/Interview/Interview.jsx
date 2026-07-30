import "./Interview.css";
import { useLocation, useNavigate } from "react-router-dom";
import interviewQuestions from "../../data/interviewQuestions";
import { useState } from "react";
import { analyzeInterview } from "../../api/interviewApi";

function Interview() {
  const location = useLocation();
  const job = location.state.job;

  const questions = interviewQuestions[job.id];

  const [generatedQuestion, setGenerateQuestion] = useState("");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [loading, setLoading] = useState(false);

  const [showQuestions, setShowQuestions] = useState(false);

  const [country, setCountry] = useState("Japan");
  const [nativeLanguage, setNativeLanguage] = useState("한국어");

  const navigate = useNavigate();

  return (
    <div className="interview-page">
      <main className="interview-card">
        <header className="interview-header">
          <span className="header-eyebrow">INTERVIEWBRIDGE AI</span>
          <h1>AI Interview Practice</h1>
          <p>{job.title}</p>
        </header>

      <section className="example-section">
        <button
          className="toggle-btn"
          onClick={() => setShowQuestions(!showQuestions)}
        >
          <span>Sample Interview Questions</span>
          <span className="toggle-icon">{showQuestions ? "−" : "+"}</span>
        </button>

        {showQuestions && (
          <ul className="question-list">
            {questions.map((question, index) => (
              <li key={index}>
                <span>{index + 1}</span>
                {question}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="setting-container">
        <div className="section-heading">
          <h2>Interview Settings</h2>
          <p>Set the context for your practice question.</p>
        </div>
        <div className="setting-group">
          <div className="setting-item">
            <label>Target Country</label>

            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            >
              <option value="Korea">Korea</option>
              <option value="Japan">Japan</option>
              <option value="USA">USA</option>
              <option value="Australia">Australia</option>
              <option value="Canada">Canada</option>
              <option value="Singapore">Singapore</option>
            </select>
          </div>

          <div className="setting-item">
            <label>Native Language</label>

            <select
              value={nativeLanguage}
              onChange={(e) => setNativeLanguage(e.target.value)}
            >
              <option value="한국어">한국어</option>
              <option value="English">English</option>
              <option value="日本語">日本語</option>
            </select>
          </div>
        </div>

        <button
          className="generate-btn"
          onClick={() =>
            setGenerateQuestion(
              "Explain a challenging AI project you have worked on."
            )
          }
        >
          Generate Question
        </button>
      </section>

      {generatedQuestion && (
        <section className="generated-question">
          <h3>Generated Question</h3>
          <p>{generatedQuestion}</p>
        </section>
      )}

      <section className="question-input input-card">
        <h3>Question</h3>

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter your interview question..."
        />
      </section>

      <section className="answer-input input-card">
        <h3>Answer</h3>

        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Enter your interview answer..."
        />
      </section>

      <div className="button-container">
        <button
          className="analyze-btn"
          disabled={loading}
          onClick={async () => {
            setLoading(true);

            const analysisResult = await analyzeInterview(
              job,
              question,
              answer
            );

            navigate("/result", {
              state: {
                job,
                question,
                answer,
                analysisResult,
              },
            });
          }}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>
      </main>
    </div>
  );
}

export default Interview;
