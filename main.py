"""NBFC Registration Agent — Standalone runner."""

from state import LoanState
from agents.registration_agent import registration_node


def main():
    """Run the Registration Agent as a standalone module."""
    print("\n" + "🔷" * 25)
    print("  NBFC LOAN — REGISTRATION AGENT")
    print("🔷" * 25 + "\n")

    # Ask loan type upfront (Registration Agent needs it for student loan ABC ID check)
    loan_type = ""
    valid_types = ["personal", "student", "business", "home"]
    while loan_type not in valid_types:
        loan_type = input(f"  Loan Type ({' / '.join(valid_types)}): ").strip().lower()
        if loan_type not in valid_types:
            print(f"  ⚠️  Choose from: {', '.join(valid_types)}")

    # Seed state with loan type
    initial_state: LoanState = {"loan_type": loan_type}

    # Run registration
    result = registration_node(initial_state)

    # Show final result
    print("\n" + "🔷" * 25)
    print("  REGISTRATION COMPLETE")
    print("🔷" * 25)

    if result.get("errors"):
        print("\n  ⚠️  Issues:")
        for err in result["errors"]:
            print(f"     • {err}")
    else:
        print("\n  ✅ All registration steps passed!")

    print()


if __name__ == "__main__":
    main()
