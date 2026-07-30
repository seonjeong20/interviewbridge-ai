import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./pages/Login/Login";
import Dashboard from "./pages/Dashboard/Dashboard";
import Interview from "./pages/Interview/Interview";
import Result from "./pages/Result/Result";
import Notebook from "./pages/Notebook/Notebook";

function App() {
    return (
        <BrowserRouter>

            <Routes>

                <Route path="/" element={<Login />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/interview" element={<Interview />} />
                <Route path="/result" element={<Result />} />
                <Route path="/notebook" element={<Notebook />} />

            </Routes>

        </BrowserRouter>
    );
}

export default App;