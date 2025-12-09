from pathlib import Path
path = Path('AI/intelligence/verify_ai_intelligence.py')
text = path.read_text()
old = '        self.installation_dir = Path(installation_dir)\n        ai_dir = installation_dir /  AI\n        self.data_dir = ai_dir / data / full_monitoring\n        self.models_dir = ai_dir / models\n        self.db_path = self.data_dir / full_monitoring.db\n'
new = '        self.installation_dir = Path(installation_dir)\n        ai_dir = installation_dir / AI\n        secure_data_dir = self.installation_dir / _secure_data / full_monitoring\n        legacy_data_dir = ai_dir / data / full_monitoring\n        if (secure_data_dir / full_monitoring.db).exists():\n            self.data_dir = secure_data_dir\n        else:\n            self.data_dir = legacy_data_dir\n        self.models_dir = ai_dir / models\n        self.db_path = self.data_dir / full_monitoring.db\n'
if old not in text:
    raise SystemExit('pattern not found in verify_ai_intelligence.py')
path.write_text(text.replace(old, new))
