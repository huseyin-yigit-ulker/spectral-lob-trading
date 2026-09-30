import sys

filepath = "scripts/run_agent.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_code = 'table.add_row("Piyasa Fiyati", f"${self.current_price:,.2f}")'
new_code = 'decimals = 5 if self.current_price < 10.0 else 2\n        table.add_row("Piyasa Fiyati", f"${self.current_price:,.{decimals}f}")'

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("VS Code kilidi asildi ve kod guncellendi!")
else:
    print("Kod bulunamadi. (Belki de VS Code formati degistirdi)")
