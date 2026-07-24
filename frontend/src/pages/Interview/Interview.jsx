import "./Interview.css";
import { useLocation} from "react-router-dom"

function Interview() {

    const location = useLocation();
    const job = location.state.job;

    return(

        <div>
            <h1>Interview Page</h1>
            <h1>{job}</h1>
        </div>

    );
}

export default Interview