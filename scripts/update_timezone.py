import os

files_to_update = [
    r"c:\Py\spotbot\core\engine.py",
    r"c:\Py\spotbot\services\database.py",
    r"c:\Py\spotbot\services\telegram_notifier.py",
    r"c:\Py\spotbot\ui\dashboard.py",
    r"c:\Py\spotbot\services\pdf_generator.py",
    r"c:\Py\spotbot\services\gemini_ai.py",
    r"c:\Py\spotbot\core\post_trade.py"
]

for file in files_to_update:
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        import_zoneinfo = "from zoneinfo import ZoneInfo\n"
        if import_zoneinfo not in content and ("datetime.now" in content or "dt_module.datetime.now" in content):
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_idx = i + 1
            lines.insert(insert_idx, import_zoneinfo.strip())
            content = '\n'.join(lines)

        content = content.replace("dt_module.datetime.now()", "dt_module.datetime.now(ZoneInfo('America/Sao_Paulo'))")
        content = content.replace("datetime.now()", "datetime.now(ZoneInfo('America/Sao_Paulo'))")

        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {file}")
