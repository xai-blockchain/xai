from pathlib import Path
text = Path('core/api_extensions.py').read_text().splitlines()
for idx,line in enumerate(text):
    if 360 <= idx <= 430:
        print(repr(line))
