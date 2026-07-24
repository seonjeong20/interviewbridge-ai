import JobCard from "../../components/JobCard/JobCard";
import "./Dashboard.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const navigate = useNavigate();

  const [selectedJob, setSelectedJob] = useState(null);

  const jobs = [
    {
      title: "💻  Backend Developer",
      description: "REST API / Spring",
    },
    {
      title: "🎨  Frontend Developer",
      description: "React / CSS",
    },
    {
      title: "🤖  AI Engineer",
      description: "LLM / Python",
    },
    {
      title: "📊  Data Analyst",
      description: "Python / SQL",
    },
    {
      title: "📱  Mobile Developer",
      description: "Android / iOS",
    },
  ];

  return (
    <div className="dashboard-container">
      <h1>InterviewBridge AI</h1>

      <h2>오늘은 어떤 직무를 연습하시겠어요?</h2>

      <div className="job-grid">
        {jobs.map((job) => (
          <JobCard
            key={job.title}
            title={job.title}
            description={job.description}
            selected={selectedJob === job.title}
            onClick={() => setSelectedJob(job.title)}
          />
        ))}
      </div>

      <button
        className="start-button"
        disabled={!selectedJob}
        onClick={() =>
          navigate("/interview", {
            state: {
              job: selectedJob,
            },
          })
        }
      >
        Start Interview
      </button>
    </div>
  );
}

export default Dashboard;
