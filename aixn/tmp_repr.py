from pathlib import Path
text = Path('core/api_extensions.py').read_text().splitlines()
for idx,line in enumerate(text):
    if "@self.app.route('/wallet-trades/wc/handshake'" in line:
        print(idx+1, repr(line))
        break
