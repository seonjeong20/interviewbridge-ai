import { useNavigate } from "react-router-dom";
import "./Notebook.css";

function Notebook() {
  const navigate = useNavigate();

  const notebookItems = [
    {
      job: { title: "AI Engineer" },
      question: "Explain a challenging AI project you have worked on.",
      answer: "I built an AI-powered recommendation workflow and improved its evaluation process through iterative testing.",
      analysisResult: {
        score: 85,
        strengths: ["Clear project ownership", "Relevant technical experience"],
        weaknesses: ["Could include more measurable outcomes"],
        improvement: "Add concrete metrics to show the impact of your work.",
        modelAnswer: "Describe the project context, your contribution, the technical decisions, and measurable results.",
      },
      date: "Latest practice",
      summary: "Strong technical direction with room for more measurable impact.",
    },
    {
      job: { title: "Data Analyst" },
      question: "How do you turn raw data into a business recommendation?",
      answer: "I validate the data, identify patterns, and connect the findings to the business goal.",
      analysisResult: {
        score: 78,
        strengths: ["Structured approach", "Business-focused thinking"],
        weaknesses: ["Could explain validation steps in more detail"],
        improvement: "Give a specific example of the analysis method and result.",
        modelAnswer: "Start with the decision to be made, validate the dataset, analyze key trends, and present an actionable recommendation.",
      },
      date: "Previous practice",
      summary: "Well-structured answer that would benefit from a more concrete example.",
    },
  ];

  return (
    <div className="notebook-page">
      <main className="notebook-container">
        <button
          className="dashboard-button"
          onClick={() => navigate("/dashboard")}
        >
          ← Dashboard
        </button>

        <header className="notebook-header">
          <span className="notebook-eyebrow">INTERVIEW HISTORY</span>
          <h1>Interview Notebook</h1>
          <p>Review your previous practice sessions and track your progress.</p>
        </header>

        <div className="search-wrapper">
          <span aria-hidden="true">⌕</span>
          <input
            className="search-input"
            type="search"
            placeholder="Search by job title or keyword"
          />
        </div>

        <section className="notebook-list">
          {notebookItems.map((item, index) => (
            <article className="notebook-card" key={index}>
              <div className="card-left">
                <div className="card-title-row">
                  <h2>{item.job.title}</h2>
                  <span className={`score-badge score-${item.analysisResult.score}`}>
                    {item.analysisResult.score} / 100
                  </span>
                </div>
                <p className="card-question">{item.question}</p>
                <p className="card-summary">{item.summary}</p>
              </div>

              <div className="card-right">
                <span className="card-date">{item.date}</span>
                <button
                  className="view-result-button"
                  onClick={() =>
                    navigate("/result", {
                      state: {
                        job: item.job,
                        question: item.question,
                        answer: item.answer,
                        analysisResult: item.analysisResult,
                      },
                    })
                  }
                >
                  View Result →
                </button>
              </div>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}

export default Notebook;
