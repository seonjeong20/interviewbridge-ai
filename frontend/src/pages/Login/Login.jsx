import "./Login.css"
import { useNavigate } from "react-router-dom";

function Login() {

        const navigate = useNavigate();

  return (
    <div className="login-container">

        <div className="login-card">

            <div className="logo">
                <h1>InterviewBridge AI</h1>
            </div>

            <h2 className="login-title">
                Login
            </h2>

           <input
                className="login-input"
                type="email"
                placeholder="Email"
            />

            <input
                className="login-input"
                type="password"
                placeholder="Password"
            />

            <button 
                className="login-button"
                onClick={() => navigate("/dashboard")}
            >
                Login
            </button>

            <p className="signup-text">
                Don't have an account? <span className="signup-link">Sign Up</span>
            </p>

        </div>

    </div>
    );
}

export default Login;