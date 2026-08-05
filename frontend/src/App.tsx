import { BrowserRouter, Routes, Route } from "react-router-dom";

// Pages will be added in Phase 4
function Home() {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Mastery Pulse</h1>
      <p>
        Backend API: <code>http://localhost:8000</code>
      </p>
      <p>Phase 4 will add the full UI. See project_plan.md.</p>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
