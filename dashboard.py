"""
Ponto de entrada legado para a interface Web NiceGUI.
Delegando para o novo módulo ui.dashboard.
"""
from ui.dashboard import start_dashboard

if __name__ in {"__main__", "__mp_main__"}:
    start_dashboard()
