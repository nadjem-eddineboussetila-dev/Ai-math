# 🧮 AI Math Agent

A full-stack **AI-powered mathematics agent** that solves algebraic, calculus, and statistical problems with **exact symbolic computation** (SymPy + NumPy) — no text-based guessing.

---

## ✨ Features

| Category | Capabilities |
|---|---|
| **Arithmetic / Algebra** | Simplify, expand, factor expressions |
| **Equations** | Solve single-variable equations (linear, quadratic, …) |
| **Calculus** | Differentiation, indefinite integration, limits |
| **Statistics** | Mean, median, std-dev, variance, IQR, quartiles |
| **UI** | Step-by-step solutions, LaTeX rendering, history log |

---

## 🗂️ Project Structure

```
Ai-math/
├── backend/
│   └── main.py          ← FastAPI + SymPy math engine
├── frontend/
│   └── app.py           ← Streamlit interactive UI
├── requirements.txt     ← All Python dependencies
└── README.md
```

---

## 🚀 Quick Start (Local)

### 1 — Clone & install dependencies

```bash
git clone https://github.com/nadjem-eddineboussetila-dev/Ai-math.git
cd Ai-math

# (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2 — Start the Backend (FastAPI)

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000**  
Interactive docs (Swagger UI): **http://localhost:8000/docs**

### 3 — Start the Frontend (Streamlit)

Open a **second terminal** in the same directory:

```bash
streamlit run frontend/app.py
```

The UI opens automatically at **http://localhost:8501**

---

## 🔌 API Reference

### `POST /solve`

| Field | Type | Description |
|---|---|---|
| `expression` | `string` | Math expression or equation |
| `operation` | `string` | `auto` \| `simplify` \| `solve` \| `diff` \| `integrate` \| `limit` \| `expand` \| `factor` \| `stats` |
| `variable` | `string` | Primary variable (default `x`) |
| `limit_point` | `string` | Point for limit evaluation (e.g. `oo`, `0`, `pi`) |
| `stats_data` | `[float]` | List of numbers for statistical analysis |

**Example request:**
```json
{
  "expression": "x**2 - 5*x + 6 = 0",
  "operation": "solve"
}
```

**Example response:**
```json
{
  "input_expression": "x**2 - 5*x + 6 = 0",
  "operation": "solve",
  "result": "[2, 3]",
  "steps": [
    {"step": 1, "description": "Identify equation", "result": "x**2 - 5*x + 6 = 0"},
    {"step": 2, "description": "Form equation object", "result": "Eq(x**2 - 5*x + 6, 0)"},
    {"step": 3, "description": "Solve for x", "result": "[2, 3]"}
  ],
  "latex": "\\left[ 2, \\  3\\right]"
}
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11+, FastAPI, SymPy, NumPy, Pydantic v2
- **Frontend:** Streamlit, Requests
- **Server:** Uvicorn (ASGI)

---

## 📝 Usage Examples

| Problem | Operation | Expression |
|---|---|---|
| Simplify sin²x + cos²x | `simplify` | `sin(x)**2 + cos(x)**2` |
| Solve x²-5x+6=0 | `solve` | `x**2 - 5*x + 6 = 0` |
| Derivative of x³sin(x) | `diff` | `x**3 * sin(x)` |
| ∫ eˣcos(x) dx | `integrate` | `exp(x)*cos(x)` |
| lim sin(x)/x as x→0 | `limit` | `sin(x)/x` (limit_point=`0`) |
| Factor x³-x²-x+1 | `factor` | `x**3 - x**2 - x + 1` |
| Stats of dataset | `stats` | stats_data=`[2,4,6,8,10]` |
