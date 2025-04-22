
import json
from pathlib import Path

def load_skills(path='app/data/skills.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
skills = load_skills()
