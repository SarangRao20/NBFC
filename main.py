"""FinServe NBFC — Main Entry Point."""

import subprocess
import sys


def main():
    print("=== Launching FinServe NBFC Agentic Loan Platform ===")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
                    "--server.port", "8501"], check=True)


if __name__ == "__main__":
    main()
