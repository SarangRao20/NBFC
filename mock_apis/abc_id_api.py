"""Mock ABC ID API — Academic Bank of Credits student verification."""

MOCK_ABC_DB = {
    "ABC123456": {"name": "Rahul Sharma",  "university": "IIT Delhi",     "course": "B.Tech CS",        "year": 3, "status": "active"},
    "ABC789012": {"name": "Priya Patel",   "university": "NIT Trichy",    "course": "M.Tech Electronics","year": 2, "status": "active"},
    "ABC345678": {"name": "Amit Kumar",    "university": "BITS Pilani",   "course": "B.E. Mechanical",  "year": 4, "status": "inactive"},
    "ABC901234": {"name": "Sneha Reddy",   "university": "IIIT Hyderabad","course": "B.Tech AI & ML",   "year": 1, "status": "active"},
    "ABC567890": {"name": "Vikram Singh",  "university": "Delhi University","course": "B.Com Honours",   "year": 2, "status": "active"},
    "ABC112233": {"name": "Anjali Gupta",  "university": "JNU Delhi",     "course": "MA Economics",     "year": 1, "status": "inactive"},
}


def verify_abc_id(abc_id: str) -> dict:
    """Verify student ABC ID. Returns verified status + details."""
    abc_id = abc_id.strip().upper()

    if abc_id not in MOCK_ABC_DB:
        return {"verified": False, "student_name": None, "university": None, "course": None,
                "error": f"ABC ID '{abc_id}' not found."}

    record = MOCK_ABC_DB[abc_id]

    if record["status"] != "active":
        return {"verified": False, "student_name": record["name"], "university": record["university"],
                "course": record["course"], "error": f"ABC ID '{abc_id}' is inactive."}

    print(f"\n  ✅ ABC ID Verified: {record['name']} | {record['university']} | {record['course']} (Year {record['year']})\n")

    return {"verified": True, "student_name": record["name"], "university": record["university"],
            "course": record["course"], "error": None}
