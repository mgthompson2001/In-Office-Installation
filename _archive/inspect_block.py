from pathlib import Path
path = Path('AI/intelligence/verify_ai_intelligence.py')
text = path.read_text()
old = '        self.installation_dir = Path(installation_dir)\n        ai_dir = installation_dir /  AI\n        self.data_dir = ai_dir / data / full_monitoring\n        self.models_dir = ai_dir / models\n        self.db_path = self.data_dir / full_monitoring.db\n'
print(repr(old))
start = text.find('self.data_dir = ai_dir')
print('start', start)
print(repr(text[start-50:start+150]))
