from app import db, app

# Use the application context
try:
    with app.app_context():
        db.create_all()
    print("Database tables created successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
