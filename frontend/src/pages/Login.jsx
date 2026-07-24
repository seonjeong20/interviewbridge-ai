import "./Login.css"

function Login() {
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

            <button className="login-button">
                Login
            </button>

            <p className="signup-text">
                Don't have an account? <strong>Sign Up</strong>
            </p>

        </div>

    </div>
    );
}

export default Login;