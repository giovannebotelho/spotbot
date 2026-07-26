import sys
sys.path.insert(0, '.')
from services.database import DatabaseManager
from services.pdf_generator import generate_weekly_telemetry_pdf

def test_pdf():
    print("Testing Weekly Telemetry PDF Generator...")
    db = DatabaseManager()
    output_pdf = generate_weekly_telemetry_pdf(db, output_path="docs/Relatorio_Semanal_Telemetria.pdf")
    print(f"SUCCESS: PDF generated cleanly at {output_pdf}")

if __name__ == "__main__":
    test_pdf()
