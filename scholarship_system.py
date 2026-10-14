import ast
import json
import logging
import math
import operator
import sys

# Global state
results = {}
MERIT_FORMULA = "gpa * 10 + credits * 2"
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

def evaluate_formula(formula, gpa, credits):
    try:
        tree = ast.parse(formula, mode="eval")
        return safe_eval(tree, {"gpa": gpa, "credits": credits})
    except (SyntaxError, ZeroDivisionError) as exc:
        raise ValueError("Invalid merit formula: %s" % formula) from exc

def calculate_merit_score(gpa, credits):
    return evaluate_formula(MERIT_FORMULA, gpa, credits)

def evaluate_applicant(student_id, test_scores, logs=[]):
    gpa = test_scores["gpa"]
    credits = test_scores.get("credits", 0)
    income = test_scores.get("income", 0)
    score = calculate_merit_score(gpa, credits)
    eligible = score >= CUTOFF and income < INCOME_LIMIT
    results[student_id] = {"score": score, "eligible": eligible}
    logs.append("%s scored %s" % (student_id, score))
    return eligible

def change_formula(new_formula):
    global MERIT_FORMULA
    evaluate_formula(new_formula, 1, 1)  # reject bad formulas up front
    MERIT_FORMULA = new_formula

def persist_results(file="scholarships.json"):
    f = open(file, "w")
    f.write(json.dumps(results))
    f.close()

def load_results(file="scholarships.json"):
    global results
    try:
        results = json.loads(open(file).read())
    except FileNotFoundError:
        logging.info("%s not found; starting with empty results", file)
    except json.JSONDecodeError:
        logging.warning("%s is not valid JSON; ignoring it", file)

def printShortlist():
    print("Shortlisted applicants:")
    for r in results:
        if results[r]["eligible"] == True:
            print(" ", r, "score =", results[r]["score"])

def main():
    evaluate_applicant("U001", {"gpa": 9.1, "credits": 4, "income": 450000})
    evaluate_applicant("U002", {"gpa": 7.2, "credits": 1, "income": 300000})
    evaluate_applicant("U003", {"gpa": 12.5, "credits": -3, "income": -1})
    evaluate_applicant("U004", {"gpa": 6.5})
    formula = input("Merit formula (Enter to keep default): ")
    if formula:
        try:
            change_formula(formula)
        except ValueError as exc:
            print("%s -- keeping default formula" % exc)
    evaluate_applicant("U005", {"gpa": 8.4, "credits": 3, "income": 600000})
    persist_results()
    load_results()
    printShortlist()

main()
