import "./Interview.css";
import { useLocation, useNavigate } from "react-router-dom";
import interviewQuestions from "../../data/interviewQuestions";
import { useState } from "react";
import { analyzeInterview, generateQuestion } from "../../api/interviewApi";

function Interview() {
  const location = useLocation();
  const job = location.state?.job;

  const questions = interviewQuestions[job?.id] ?? [];
  const initialQuestion = location.state?.question ?? "";

  const [generatedQuestion, setGenerateQuestion] = useState("");

  const [question, setQuestion] = useState(initialQuestion);
  const [answer, setAnswer] = useState("");

  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const [showQuestions, setShowQuestions] = useState(false);

  const [country, setCountry] = useState(location.state?.country ?? "Japan");
  const [nativeLanguage, setNativeLanguage] = useState(
    location.state?.nativeLanguage ?? "Korean"
  );

  const navigate = useNavigate();

  const jobName = job?.title
    ? job.title.replace(/^[^\p{L}\p{N}]+/u, "").trim()
    : "";

  const handleGenerateQuestion = async () => {
    setGenerating(true);
    setError("");

    try {
      const response = await generateQuestion({
        job: jobName,
        country,
        nativeLanguage,
      });
      setGenerateQuestion(response.question);
      setQuestion(response.question);
    } catch {
      setError("질문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setGenerating(false);
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await analyzeInterview({
        job: jobName,
        country,
        nativeLanguage,
        question,
        answer,
      });

      navigate("/result", {
        state: { job, country, nativeLanguage, result },
      });
    } catch {
      setError("답변을 분석하지 못했습니다. 서버 상태를 확인하고 다시 시도해 주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="interview-page">
      <main className="interview-card">
        <header className="interview-header">
          <span className="header-eyebrow">INTERVIEWBRIDGE AI</span>
          <h1>AI Interview Practice</h1>
          <p>{job?.title}</p>
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
              <li
                key={index}
                role="button"
                tabIndex={0}
                onClick={() => setQuestion(question)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    setQuestion(question);
                  }
                }}
              >
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
              <option value="Korean">한국어</option>
              <option value="English">English</option>
              <option value="Japanese">日本語</option>
            </select>
          </div>
        </div>

        <button
          className="generate-btn"
          disabled={generating}
          onClick={handleGenerateQuestion}
        >
          {generating ? "Generating..." : "Generate Question"}
        </button>
      </section>

      {generatedQuestion && (
        <section className="generated-question">
          <h3>Generated Question</h3>
          <p
            role="button"
            tabIndex={0}
            onClick={() => setQuestion(generatedQuestion)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                setQuestion(generatedQuestion);
              }
            }}
          >
            {generatedQuestion}
          </p>
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
        {error && <p role="alert">{error}</p>}
        <button
          className="analyze-btn"
          disabled={loading || !question.trim() || !answer.trim()}
          onClick={handleAnalyze}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>
      </main>
    </div>
  );
}

export default Interview;
