"""
AI Math Agent - Backend (FastAPI + SymPy)
==========================================
Provides a REST API that solves mathematical problems with exact, symbolic
computation instead of text-based inference.

Endpoints:
  POST /solve  – main solver endpoint
  GET  /health – health check
"""

from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

import numpy as np
import sympy as sp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Math Agent",
    description="Exact symbolic & numerical mathematics engine powered by SymPy/NumPy",
    version="1.0.0",
)

# Allow the Streamlit frontend (any origin in dev) to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SolveRequest(BaseModel):
    expression: str = Field(..., description="Mathematical expression or equation")
    operation: str = Field(
        "auto",
        description=(
            "Operation type: auto | simplify | solve | diff | integrate | "
            "limit | expand | factor | stats"
        ),
    )
    variable: Optional[str] = Field(
        "x", description="Primary variable for calculus operations"
    )
    limit_point: Optional[str] = Field(
        None, description="Point for limit evaluation (e.g. 'oo' for infinity)"
    )
    stats_data: Optional[List[float]] = Field(
        None, description="List of numbers for statistical analysis"
    )


class StepResult(BaseModel):
    step: int
    description: str
    result: str


class SolveResponse(BaseModel):
    input_expression: str
    operation: str
    result: str
    steps: List[StepResult]
    latex: Optional[str] = None
    numeric_value: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Core math engine
# ---------------------------------------------------------------------------

def _parse_expression(expr_str: str, var_symbols: Dict[str, sp.Symbol]) -> sp.Expr:
    """Parse a string into a SymPy expression using a safe namespace."""
    # Build a namespace with common math functions so users can type sin(x), etc.
    namespace: Dict[str, Any] = {
        **{name: getattr(sp, name) for name in dir(sp) if not name.startswith("_")},
        **var_symbols,
        "pi": sp.pi,
        "e": sp.E,
        "oo": sp.oo,
        "inf": sp.oo,
    }
    try:
        return sp.sympify(expr_str, locals=namespace)
    except Exception as exc:
        raise ValueError(f"Cannot parse expression: '{expr_str}'. {exc}") from exc


def _auto_detect_operation(expr_str: str) -> str:
    """Guess the best operation from the expression string."""
    lower = expr_str.lower()
    if "=" in expr_str and "==" not in expr_str:
        return "solve"
    if "diff(" in lower or "d/d" in lower:
        return "diff"
    if "integrate(" in lower or "integral" in lower:
        return "integrate"
    if "limit(" in lower:
        return "limit"
    if "factor(" in lower:
        return "factor"
    if "expand(" in lower:
        return "expand"
    return "simplify"


def _numeric_approximation(expr: sp.Expr) -> Optional[str]:
    """Return a numeric floating-point approximation when possible."""
    try:
        val = complex(expr.evalf())
        if val.imag == 0:
            return str(round(val.real, 10))
        return str(val)
    except Exception:
        return None


# ---- Individual operation handlers ----------------------------------------

def _op_simplify(expr: sp.Expr, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    result = sp.simplify(expr)
    steps.append(StepResult(step=2, description="Apply SymPy simplify()", result=str(result)))
    trigsimp = sp.trigsimp(result)
    if trigsimp != result:
        result = trigsimp
        steps.append(StepResult(step=3, description="Apply trigonometric simplification", result=str(result)))
    return result


def _op_solve(expr_str: str, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    """Solve an equation (supports = sign or plain expression = 0)."""
    steps.append(StepResult(step=1, description="Identify equation", result=expr_str))

    if "=" in expr_str:
        lhs_str, rhs_str = expr_str.split("=", 1)
        namespace: Dict[str, Any] = {
            **{n: getattr(sp, n) for n in dir(sp) if not n.startswith("_")},
            str(var): var,
            "pi": sp.pi,
            "e": sp.E,
            "oo": sp.oo,
        }
        lhs = sp.sympify(lhs_str.strip(), locals=namespace)
        rhs = sp.sympify(rhs_str.strip(), locals=namespace)
        equation = sp.Eq(lhs, rhs)
        steps.append(StepResult(step=2, description="Form equation object", result=str(equation)))
    else:
        namespace = {
            **{n: getattr(sp, n) for n in dir(sp) if not n.startswith("_")},
            str(var): var,
            "pi": sp.pi,
            "e": sp.E,
            "oo": sp.oo,
        }
        lhs = sp.sympify(expr_str, locals=namespace)
        equation = sp.Eq(lhs, 0)
        steps.append(StepResult(step=2, description="Treat as f(x) = 0", result=str(equation)))

    solution = sp.solve(equation, var)
    steps.append(StepResult(step=3, description=f"Solve for {var}", result=str(solution)))
    return sp.sympify(str(solution))


def _op_diff(expr: sp.Expr, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    result = sp.diff(expr, var)
    steps.append(StepResult(step=2, description=f"Differentiate with respect to {var}", result=str(result)))
    simplified = sp.simplify(result)
    if simplified != result:
        steps.append(StepResult(step=3, description="Simplify derivative", result=str(simplified)))
        result = simplified
    return result


def _op_integrate(expr: sp.Expr, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    result = sp.integrate(expr, var)
    steps.append(StepResult(step=2, description=f"Integrate with respect to {var}", result=str(result)))
    # Add constant of integration note
    steps.append(StepResult(step=3, description="Add constant of integration C", result=f"{result} + C"))
    return result


def _op_limit(
    expr: sp.Expr, var: sp.Symbol, point_str: str, steps: List[StepResult]
) -> sp.Expr:
    namespace: Dict[str, Any] = {
        **{n: getattr(sp, n) for n in dir(sp) if not n.startswith("_")},
        str(var): var,
        "pi": sp.pi,
        "e": sp.E,
        "oo": sp.oo,
        "inf": sp.oo,
    }
    point = sp.sympify(point_str, locals=namespace)
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    steps.append(StepResult(step=2, description=f"Evaluate limit as {var} → {point}", result=""))
    result = sp.limit(expr, var, point)
    steps.append(StepResult(step=3, description="Limit result", result=str(result)))
    return result


def _op_expand(expr: sp.Expr, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    result = sp.expand(expr)
    steps.append(StepResult(step=2, description="Expand expression", result=str(result)))
    return result


def _op_factor(expr: sp.Expr, var: sp.Symbol, steps: List[StepResult]) -> sp.Expr:
    steps.append(StepResult(step=1, description="Parse expression", result=str(expr)))
    result = sp.factor(expr)
    steps.append(StepResult(step=2, description="Factor expression", result=str(result)))
    return result


def _op_stats(data: List[float], steps: List[StepResult]) -> str:
    """Return a rich statistical summary using NumPy."""
    arr = np.array(data)
    steps.append(StepResult(step=1, description="Input data", result=str(arr.tolist())))

    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    variance = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0
    minimum = float(np.min(arr))
    maximum = float(np.max(arr))
    total = float(np.sum(arr))
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1

    steps.append(StepResult(step=2, description="Calculate descriptive statistics", result=""))
    steps.append(StepResult(step=3, description="Mean (Average)", result=str(round(mean, 6))))
    steps.append(StepResult(step=4, description="Median", result=str(round(median, 6))))
    steps.append(StepResult(step=5, description="Standard Deviation (sample)", result=str(round(std, 6))))
    steps.append(StepResult(step=6, description="Variance (sample)", result=str(round(variance, 6))))
    steps.append(StepResult(step=7, description="Min / Max", result=f"{minimum} / {maximum}"))
    steps.append(StepResult(step=8, description="Sum", result=str(round(total, 6))))
    steps.append(StepResult(step=9, description="Q1 / Q3 / IQR", result=f"{round(q1,4)} / {round(q3,4)} / {round(iqr,4)}"))

    summary = (
        f"Mean={round(mean,6)}, Median={round(median,6)}, "
        f"Std={round(std,6)}, Var={round(variance,6)}, "
        f"Min={minimum}, Max={maximum}, Sum={round(total,6)}, "
        f"Q1={round(q1,4)}, Q3={round(q3,4)}, IQR={round(iqr,4)}"
    )
    return summary


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok", "engine": "SymPy + NumPy"}


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    """
    Solve a mathematical expression.

    Supported operations (auto-detected or explicit):
      - simplify   : simplify an algebraic expression
      - solve      : solve an equation (use = sign)
      - diff       : differentiate with respect to `variable`
      - integrate  : indefinite integral with respect to `variable`
      - limit      : evaluate limit; requires `limit_point`
      - expand     : expand/distribute an expression
      - factor     : factor a polynomial
      - stats      : descriptive statistics; requires `stats_data`
    """
    steps: List[StepResult] = []
    expr_str = request.expression.strip()

    if not expr_str:
        raise HTTPException(status_code=400, detail="Expression cannot be empty.")

    # Determine operation
    operation = request.operation.lower()
    if operation == "auto":
        operation = _auto_detect_operation(expr_str)

    # Define the primary variable symbol
    var_name = request.variable or "x"
    var: sp.Symbol = sp.Symbol(var_name)
    var_symbols = {var_name: var}

    try:
        # Stats branch – no SymPy parsing needed
        if operation == "stats":
            if not request.stats_data:
                raise ValueError(
                    "stats operation requires 'stats_data' (a list of numbers)."
                )
            summary = _op_stats(request.stats_data, steps)
            return SolveResponse(
                input_expression=expr_str,
                operation=operation,
                result=summary,
                steps=steps,
            )

        # Solve branch – parse differently (handles = sign)
        if operation == "solve":
            result_expr = _op_solve(expr_str, var, steps)
        else:
            # Parse expression to SymPy for all other operations
            parsed = _parse_expression(expr_str, var_symbols)

            if operation == "simplify":
                result_expr = _op_simplify(parsed, var, steps)
            elif operation == "diff":
                result_expr = _op_diff(parsed, var, steps)
            elif operation == "integrate":
                result_expr = _op_integrate(parsed, var, steps)
            elif operation == "limit":
                point = request.limit_point or "0"
                result_expr = _op_limit(parsed, var, point, steps)
            elif operation == "expand":
                result_expr = _op_expand(parsed, var, steps)
            elif operation == "factor":
                result_expr = _op_factor(parsed, var, steps)
            else:
                # Fallback: simplify
                operation = "simplify"
                result_expr = _op_simplify(parsed, var, steps)

        result_str = str(result_expr)
        latex_str = sp.latex(result_expr) if isinstance(result_expr, sp.Basic) else None
        numeric = _numeric_approximation(result_expr) if isinstance(result_expr, sp.Basic) else None

        return SolveResponse(
            input_expression=expr_str,
            operation=operation,
            result=result_str,
            steps=steps,
            latex=latex_str,
            numeric_value=numeric,
        )

    except ValueError as exc:
        # User-facing validation error
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Unexpected computation error – return structured error
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Computation error: {exc}\n\nTraceback:\n{tb}",
        ) from exc
