import "./JobCard.css"

function JobCard({title, description, selected, onClick}) {
    return (
        <div className={`job-card ${selected ? "selected" : ""}`}
            onClick={onClick}
        >
            <h3 className="job-title">{title}</h3>
            <p className="job-description">{description}</p>
        </div>
    );
}

export default JobCard;