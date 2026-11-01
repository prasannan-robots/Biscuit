import os

from web import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode exposes an interactive console; only enable it locally.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
