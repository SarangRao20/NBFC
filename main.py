import sys
import subprocess

def run_streamlit_app():
    """Entry point to launch the Streamlit graphical interface directly."""
    print("=== Launching NBFC Agentic Loan Pipeline... ===")
    
    # We call standard python 'subprocess' to auto-run streamlit instead of terminal execution
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])

if __name__ == "__main__":
    run_streamlit_app()
