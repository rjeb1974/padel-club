from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server. Use host="0.0.0.0" to reach it from other devices on your network.
    app.run(debug=True)
