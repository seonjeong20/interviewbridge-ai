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

  const navigate = useNavigate();

  return (
    <div>
      <h1>Interview Page</h1>
      <h1>{job.title}</h1>

      <ul>
        {questions.map((question, index) => (
          <li key={index}>{question}</li>
        ))}
      </ul>

      <button
        className="generate-btn"
        onClick={() =>
          setGenerateQuestion(
            "Explain a challenging AI project you have worked on.",
          )
        }
      >
        🤖 AI Generate
      </button>

      {generatedQuestion && (
        <div className="generated-question">
          <h3>Generated Question</h3>
          <p>{generatedQuestion}</p>
        </div>
      )}

      <div className="question-input">
        <h3>Question</h3>

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter your interview question..."
        />
      </div>

      <div className="answer-input">
        <h3>Answer</h3>

        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Enter your interview answer..."
        />
      </div>

      <div className="button-container">
        <button
          className="analyze-btn"
          disabled={loading}
          onClick={async() =>{

            setLoading(true);

            const analysisResult = await analyzeInterview(
                job,
                question,
                answer
            );

            navigate("/result", { 
                state: { 
                    job, question, answer, analysisResult 
                },
            });
          }}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>
    </div>
  );
}

export default Interview;
