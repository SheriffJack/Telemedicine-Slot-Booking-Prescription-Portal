"""Scholarship eligibility system.

Scores applicants with a configurable merit formula, checks income limits,
persists the results to JSON and prints the shortlist.
"""
import ast
import json
import logging
import operator

# Global state
results = {}
CONFIG = {"merit_formula": "gpa * 10 + credits * 2"}
INCOME_LIMIT = 800000
CUTOFF = 85

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def safe_eval(node, variables):
    """Evaluate a parsed arithmetic expression using only whitelisted nodes.

    Supports numbers, names present in ``variables``, ``+ - * /`` and unary
    ``+``/``-``. Anything else raises ValueError.
    """
    if isinstance(node, ast.Expression):
        return safe_eval(node.body, variables)
    if (isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)):
        return node.value
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        return BINARY_OPS[type(node.op)](
            safe_eval(node.left, variables),
            safe_eval(node.right, variables))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](safe_eval(node.operand, variables))
    raise ValueError("Unsupported element in merit formula")

def evaluate_formula(formula, gpa, credit_count):
    """Evaluate ``formula`` for the given GPA and credits, safely."""
    try:
        tree = ast.parse(formula, mode="eval")
        return safe_eval(tree, {"gpa": gpa, "credits": credit_count})
    except (SyntaxError, ZeroDivisionError) as exc:
        raise ValueError(f"Invalid merit formula: {formula}") from exc

def calculate_merit_score(gpa, credit_count):
    """Return the merit score for a GPA and credit count."""
    return evaluate_formula(CONFIG["merit_formula"], gpa, credit_count)

def evaluate_applicant(student_id, test_scores, logs=None):
    """Score one applicant, record the result and return eligibility.

    If ``logs`` is given, a human-readable line is appended to it.
    """
    gpa = test_scores["gpa"]
    credit_count = test_scores.get("credits", 0)
    income = test_scores.get("income", 0)
    score = calculate_merit_score(gpa, credit_count)
    eligible = score >= CUTOFF and income < INCOME_LIMIT
    results[student_id] = {"score": score, "eligible": eligible}
    if logs is not None:
        logs.append(f"{student_id} scored {score}")
    return eligible

def change_formula(new_formula):
    """Replace the merit formula after checking that it is valid."""
    evaluate_formula(new_formula, 1, 1)  # reject bad formulas up front
    CONFIG["merit_formula"] = new_formula

def persist_results(file="scholarships.json"):
    """Write the current results to a JSON file."""
    with open(file, "w", encoding="utf-8") as handle:
        json.dump(results, handle)

def load_results(file="scholarships.json"):
    """Load results from a JSON file, keeping current ones on failure."""
    try:
        with open(file, encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        logging.info("%s not found; starting with empty results", file)
        return
    except json.JSONDecodeError:
        logging.warning("%s is not valid JSON; ignoring it", file)
        return
    results.clear()
    results.update(loaded)

def print_shortlist():
    """Print every applicant marked eligible."""
    print("Shortlisted applicants:")
    for student_id, record in results.items():
        if record["eligible"]:
            print(" ", student_id, "score =", record["score"])

def main():
    """Run the demo: evaluate sample applicants and print the shortlist."""
    evaluate_applicant("U001", {"gpa": 9.1, "credits": 4, "income": 450000})
    evaluate_applicant("U002", {"gpa": 7.2, "credits": 1, "income": 300000})
    evaluate_applicant("U003", {"gpa": 12.5, "credits": -3, "income": -1})
    evaluate_applicant("U004", {"gpa": 6.5})
    formula = input("Merit formula (Enter to keep default): ")
    if formula:
        try:
            change_formula(formula)
        except ValueError as exc:
            print(f"{exc} -- keeping default formula")
    evaluate_applicant("U005", {"gpa": 8.4, "credits": 3, "income": 600000})
    persist_results()
    load_results()
    print_shortlist()

if __name__ == "__main__":
    main()
