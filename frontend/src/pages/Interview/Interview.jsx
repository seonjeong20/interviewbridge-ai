import "./Interview.css";
import { useLocation } from "react-router-dom"
import interviewQuestions from "../../data/interviewQuestions";
import { useState } from "react";

function Interview() {

    const location = useLocation();
    const job = location.state.job;

    const questions = interviewQuestions[job.id];

    const [generateQuestion, setGenerateQuestion] = useState("");

    return (

        <div>
            <h1>Interview Page</h1>
            <h1>{job.title}</h1>

            <ul>
                {questions.map((question, index) =>
                (<li key={index}>{question}</li>

                ))}
            </ul>

            <button
                className="generate-btn"
                onClick={() =>
                    setGenerateQuestion(
                        "Explain a chellenging AI project you have worked on."
                    )
                }
            >🤖 AI Generate</button>

            {generateQuestion && (
                <div className="generated-question">
                    <h3>Generated Question</h3>
                    <p>{generatedQuestion}</p>
                </div>
            )}

            <div className="question-input">
                <h3>Question</h3>

                <textarea
                    placeholder="Enter your interview question..."
                />
            </div>

        </div>

    );
}

export default Interview