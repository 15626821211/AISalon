import sys
sys.path.insert(0, 'src')
from app import create_app
app = create_app()
with app.app_context():
    from models import Project
    p = Project.query.get(2)
    print(f"Status: {p.status}")
    diagrams = p.diagrams if p.diagrams else []
    for d in diagrams:
        print(f"=== {d.get('type')} ===")
        code = d.get('mermaid', '')
        print(repr(code[:400]))
        print()
