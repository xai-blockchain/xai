#!/usr/bin/env python3
import json

with open("coverage.json", "r") as f:
    cov_data = json.load(f)

files = cov_data.get("files", {})
wallet_modules = []

for filepath, filedata in files.items():
    if 'wallet' in filepath.lower() and ('src/xai' in filepath or 'src\\xai' in filepath):
        summary = filedata.get("summary", {})
        percent = summary.get("percent_covered", 0)
        statements = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", 0)
        missing = summary.get("missing_lines", 0)

        # Extract module name
        if 'src\\xai' in filepath:
            module_name = filepath.split('src\\xai\\')[-1]
        else:
            module_name = filepath.split('src/xai/')[-1]

        wallet_modules.append({
            'name': module_name,
            'percent': percent,
            'statements': statements,
            'covered': covered,
            'missing': missing,
            'full_path': filepath
        })

print("=== WALLET-RELATED MODULES ===\n")
for mod in sorted(wallet_modules, key=lambda x: x['percent']):
    print(f"{mod['name']}: {mod['percent']:.2f}%")
    print(f"  Statements: {mod['statements']} | Covered: {mod['covered']} | Missing: {mod['missing']}")
    print()
