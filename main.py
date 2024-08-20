from website import create_app

# Create a Flask app instance
app = create_app()

# The code is only executed when the script is run directly
if __name__ == '__main__':
    # Start the Flask development server with debug enabled
    app.run(debug=True)
