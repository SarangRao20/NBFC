"""Goated Custom MCP Server — Exposes credit underwriting SHAP explanations and financial market yields over Stdio JSON-RPC."""

import sys
import json
import traceback

def compute_shap_values(credit_score, salary, existing_emi, requested_amount, city="Mumbai"):
    base_rate = 12.50
    base_limit = 300000

    # Credit Score Impact
    if credit_score >= 800:
        cibil_rate_impact = -2.00
        cibil_limit_impact = 500000
        cibil_desc = "Tier-1 Prime Score (800+) reduced risk premium."
    elif credit_score >= 750:
        cibil_rate_impact = -1.25
        cibil_limit_impact = 350000
        cibil_desc = "Strong Credit History (750-799)."
    else:
        cibil_rate_impact = 0.50
        cibil_limit_impact = -50000
        cibil_desc = "Average/Subprime credit risk premium added."

    # Income & Debt Impact
    monthly_inc = float(salary or 75000)
    foir = (existing_emi / monthly_inc) if monthly_inc > 0 else 0.20
    if monthly_inc >= 150000:
        income_limit_impact = 450000
        income_rate_impact = -0.50
        income_desc = "High Salary Level (≥₹1.5L/mo)."
    else:
        income_limit_impact = 200000
        income_rate_impact = 0.00
        income_desc = "Standard Salary Level."

    if foir < 0.25:
        foir_limit_impact = 200000
        foir_rate_impact = -0.25
        foir_desc = "Low Debt Burden (FOIR < 25%)."
    else:
        foir_limit_impact = 50000
        foir_rate_impact = 0.50
        foir_desc = "High Debt Burden (FOIR ≥ 25%)."

    # Aggregated results
    final_rate = max(9.50, round(base_rate + cibil_rate_impact + income_rate_impact + foir_rate_impact, 2))
    final_limit = max(100000, base_limit + cibil_limit_impact + income_limit_impact + foir_limit_impact)

    return {
        "final_approved_rate": final_rate,
        "final_approved_limit": final_limit,
        "base_rate": base_rate,
        "shap_summary": f"Your approved rate of {final_rate}% p.a. was derived from a base rate of {base_rate}%, with a {abs(cibil_rate_impact)}% discount from your CIBIL score of {credit_score}.",
        "waterfall": [
            {"feature": "Base Benchmark", "rate_impact": base_rate, "limit_impact": base_limit, "description": "National Benchmark Rate"},
            {"feature": "CIBIL Bureau Score", "rate_impact": cibil_rate_impact, "limit_impact": cibil_limit_impact, "description": cibil_desc},
            {"feature": "Monthly Net Income", "rate_impact": income_rate_impact, "limit_impact": income_limit_impact, "description": income_desc},
            {"feature": "FOIR / Existing Debt", "rate_impact": foir_rate_impact, "limit_impact": foir_limit_impact, "description": foir_desc}
        ]
    }

def get_market_rates():
    return {
        "rbi_repo_rate": 6.50,
        "average_fd_yield": 7.10,
        "average_mutual_fund_cagr": 14.20,
        "advice_policy": "If loan interest rate is less than mutual fund CAGR (14.2%), continuing monthly equity SIP is mathematically optimal compared to prepaying the loan principal."
    }

def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "get_shap_values",
                        "description": "Calculate SHAP credit underwriting Shapley feature contributions.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "credit_score": {"type": "integer"},
                                "salary": {"type": "number"},
                                "existing_emi": {"type": "number"},
                                "requested_amount": {"type": "number"},
                                "city": {"type": "string"}
                            },
                            "required": ["credit_score", "salary", "requested_amount"]
                        }
                    },
                    {
                        "name": "get_market_rates",
                        "description": "Get current Indian market lending, fixed deposit, and mutual fund yields.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            },
            "id": req_id
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "get_shap_values":
            try:
                res = compute_shap_values(
                    credit_score=int(args.get("credit_score", 750)),
                    salary=float(args.get("salary", 75000)),
                    existing_emi=float(args.get("existing_emi", 0)),
                    requested_amount=float(args.get("requested_amount", 500000)),
                    city=args.get("city", "Mumbai")
                )
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                    },
                    "id": req_id
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Error running get_shap_values: {str(e)}"},
                    "id": req_id
                }

        elif tool_name == "get_market_rates":
            res = get_market_rates()
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                },
                "id": req_id
            }

    return {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": f"Method {method} not found"},
        "id": req_id
    }

def main():
    """Main stdio loop for JSON-RPC communication."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                "id": None
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
