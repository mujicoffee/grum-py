from website import create_app, db
from sqlalchemy import inspect

# Import all models from models.py dynamically
from website.models import * 

def check_db_connection():
    try:
        # Create an inspector object to inspect the database
        insp = inspect(db.engine)
        # Check if there is at least one table in the database to verify the connection
        if insp.get_table_names():
            print("Database connection successful.")
            return True
        else:
            print("Database is connected but no tables found.")
            return True  # Return True if connected even without tables
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return False

def create_tables():
    try:
        # Retrieve the existing table names in the database
        existing_tables = inspect(db.engine).get_table_names()
        new_tables = []

        if not existing_tables:
            # Get all the model classes dynamically from models.py
            model_classes = [cls for cls in globals().values() if isinstance(cls, type) and issubclass(cls, db.Model)]

            # Create all tables in the database
            for Model in model_classes:
                table_name = Model.__table__.name
                new_tables.append(table_name)
            
            db.create_all()
            print("Tables created successfully:", new_tables)
        else:
            # Get all the model classes dynamically from models.py
            model_classes = [cls for cls in globals().values() if isinstance(cls, type) and issubclass(cls, db.Model)]

            # Create new tables that do not exist in the database
            for Model in model_classes:
                table_name = Model.__table__.name
                if table_name not in existing_tables:
                    Model.__table__.create(db.engine)
                    new_tables.append(table_name)
            
            if new_tables:
                print("New tables created:", new_tables)
            else:
                print("Tables already exist in the database.")
                print("Existing tables:", existing_tables)
            
    except Exception as e:
        print(f"Error creating tables: {e}")

# Create the Flask App
app = create_app()

# Create an application context to access the database
with app.app_context():
    # Check the database connection and create tables if connected
    if check_db_connection():
        create_tables()
