from app import app
import os

port = int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "5000")))
app.run(host="0.0.0.0", port=port, debug=True)
