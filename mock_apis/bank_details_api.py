"""Mock Bank Details API — lookup bank details by name."""

import random

MOCK_BANKS = {
    "sbi":    {"full_name": "State Bank of India",    "ifsc_prefix": "SBIN0", "account_length": 11},
    "hdfc":   {"full_name": "HDFC Bank",              "ifsc_prefix": "HDFC0", "account_length": 14},
    "icici":  {"full_name": "ICICI Bank",             "ifsc_prefix": "ICIC0", "account_length": 12},
    "axis":   {"full_name": "Axis Bank",              "ifsc_prefix": "UTIB0", "account_length": 15},
    "kotak":  {"full_name": "Kotak Mahindra Bank",    "ifsc_prefix": "KKBK0", "account_length": 14},
    "pnb":    {"full_name": "Punjab National Bank",   "ifsc_prefix": "PUNB0", "account_length": 16},
    "bob":    {"full_name": "Bank of Baroda",         "ifsc_prefix": "BARB0", "account_length": 14},
    "canara": {"full_name": "Canara Bank",            "ifsc_prefix": "CNRB0", "account_length": 13},
    "union":  {"full_name": "Union Bank of India",    "ifsc_prefix": "UBIN0", "account_length": 15},
    "idbi":   {"full_name": "IDBI Bank",              "ifsc_prefix": "IBKL0", "account_length": 13},
}

_ALIASES = {
    "state bank": "sbi", "state bank of india": "sbi",
    "hdfc bank": "hdfc", "icici bank": "icici",
    "axis bank": "axis", "kotak mahindra": "kotak", "kotak mahindra bank": "kotak",
    "punjab national": "pnb", "punjab national bank": "pnb",
    "bank of baroda": "bob", "baroda": "bob",
    "canara bank": "canara", "union bank": "union", "union bank of india": "union",
    "idbi bank": "idbi",
}


def get_bank_details(bank_name: str) -> dict:
    """Lookup bank by name (fuzzy). Returns account number + IFSC."""
    normalized = bank_name.strip().lower().replace(".", "")

    bank_key = None
    if normalized in MOCK_BANKS:
        bank_key = normalized
    elif normalized in _ALIASES:
        bank_key = _ALIASES[normalized]
    else:
        for alias, key in _ALIASES.items():
            if normalized in alias or alias in normalized:
                bank_key = key
                break

    if bank_key is None:
        available = ", ".join(sorted(b["full_name"] for b in MOCK_BANKS.values()))
        return {"found": False, "bank_name": None, "account_number": None, "ifsc": None,
                "error": f"Bank '{bank_name}' not found. Available: {available}"}

    bank = MOCK_BANKS[bank_key]
    account_number = "".join([str(random.randint(0, 9)) for _ in range(bank["account_length"])])
    ifsc = bank["ifsc_prefix"] + "".join([str(random.randint(0, 9)) for _ in range(6)])

    print(f"\n   Bank Details Retrieved:")
    print(f"     Bank: {bank['full_name']}")
    print(f"     Account: {account_number}")
    print(f"     IFSC: {ifsc}\n")

    return {"found": True, "bank_name": bank["full_name"], "account_number": account_number,
            "ifsc": ifsc, "error": None}
