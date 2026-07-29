import { useLocation } from "react-router-dom";
import "./Result.css";

function Result() {
  const location = useLocation();

  const { job,  question, answer, analysisResult} = location.state

  return (
    <div className="result-container">
      <h1>Interview Result</h1>

      <h2>{job.title}</h2>

      <section>
        <h3>Overall Score</h3>
        <p className="score">{analysisResult.score} / 100</p>
      </section>

      <section>
        <h3>Question</h3>
        <p>{question}</p>
      </section>

      <section>
        <h3>Your Answer</h3>
        <p>{answer}</p>
      </section>

      <section>
        <h3>Strength</h3>

        <ul>
          {analysisResult.strengths.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Weakness</h3>

        <ul>
          {analysisResult.weaknesses.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Improvement</h3>
        <p>{analysisResult.improvement}</p>
      </section>

      <section>
        <h3>Model Answer</h3>
        <p>{analysisResult.modelAnswer}</p>
      </section>
    </div>
  );
}

export default Result;
