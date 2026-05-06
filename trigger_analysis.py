import sys
sys.path.insert(0, 'src')
from app import create_app
app = create_app()
with app.app_context():
    from projects.services import ProjectService
    print('Starting analysis for project 2...')
    result = ProjectService.analyze(2)
    if 'error' in result:
        print(f'Error: {result["error"]}')
    else:
        print(f'Done! Status: {result.get("status", "?")}')
        print(f'Summary: {len(result.get("summary",""))} chars')
        print(f'Diagrams: {len(result.get("diagrams",[])) if result.get("diagrams") else 0}')
        print(f'Lessons: {len(result.get("lessons_learned",""))} chars')
