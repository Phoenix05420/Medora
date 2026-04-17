import subprocess
import json
import os

# Path to R executable found earlier
R_PATH = r"C:\Program Files\R\R-4.5.3\bin\R.exe"

def run_health_analysis(medical_records_json: str):
    script_path = os.path.join(os.path.dirname(__file__), "..", "analytics", "health_stats.R")
    
    try:
        # Call R script using subprocess
        result = subprocess.run(
            [R_PATH, "--vanilla", "--slave", "-f", script_path, "--args", medical_records_json],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": f"R execution failed: {str(e)}", "details": result.stderr if 'result' in locals() else ""}
