from src import create_app, db
from src.config import DevelopmentConfig 

app = create_app(DevelopmentConfig)

@app.cli.command('seed_db')
def seed_db_command():
    """Seeds the database with initial data."""
    print("Database seeded with example data.")

@app.shell_context_processor
def make_shell_context():
    """Register items for the Flask shell."""
    return {'db': db}