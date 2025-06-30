# FILE: manage.py
# A command-line interface for administrative tasks.

import click
from flask.cli import with_appcontext
from app import app, db
from models import User, UserProfile
import logging

logger = logging.getLogger(__name__)

@app.cli.group()
def admin():
    """Performs administrative tasks."""
    pass

@admin.command("create")
@click.option('--name', required=True, help="Administrator's full name.")
@click.option('--email', required=True, help="Administrator's email address.")
def create_admin(name, email):
    """Creates the initial administrator user."""
    with app.app_context():
        if User.query.filter_by(email=email).first():
            logger.warning(f"Admin user with email {email} already exists.")
            return

        try:
            admin_user = User(name=name, email=email)
            # Create the associated profile
            admin_profile = UserProfile(user=admin_user)
            db.session.add(admin_user)
            db.session.add(admin_profile)
            db.session.commit()
            logger.info(f"Successfully created administrator account for {email}.")
            print(f"Admin user '{name}' with email '{email}' created successfully.")
        except Exception as e:
            db.session.rollback()
            logger.exception("Failed to create admin user.")
            print(f"Error: Could not create admin user. {e}")

# To use this, run from your terminal:
# export FLASK_APP=manage.py
# flask admin create --name "Your Name" --email "your.email@example.com"
