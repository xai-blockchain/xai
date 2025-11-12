from pathlib import Path
path = Path('core/api_extensions.py')
text = path.read_text()
start = text.index('        def setup_wallet_trades_routes')
end = text.index('    def setup_personal_ai_routes')
print('start', start)
print('end', end)
print(text[start:end][:300])
