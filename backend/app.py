from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client["webhooks"]
collection = db["events"]

@app.route("/")
def home():
    return "Webhook server running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get('X-GitHub-Event')
    data = request.json
    timestamp = datetime.utcnow().isoformat()

    try:
        # Prepare event object
        if event_type == "push":
            author = data['pusher']['name']
            to_branch = data['ref'].split("/")[-1]
            event = {
                "action": "push",
                "author": author,
                "to_branch": to_branch,
                "timestamp": timestamp
            }

        elif event_type == "pull_request":
            author = data['pull_request']['user']['login']
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            event = {
                "action": "pull_request",
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }

        elif event_type == "merge":
            author = data['sender']['login']
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            event = {
                "action": "merge",
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }

        else:
            return jsonify({"msg": "Event ignored"}), 200

        # Insert into MongoDB
        collection.insert_one(event)

        # Return cleaned data (without _id)
        response_data = {
            "action": event["action"],
            "author": event["author"],
            "to_branch": event["to_branch"],
            "timestamp": event["timestamp"]
        }

        # Optional: include from_branch if available
        if "from_branch" in event:
            response_data["from_branch"] = event["from_branch"]

        return jsonify({"msg": "Event stored", "data": response_data}), 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/events", methods=["GET"])
def get_events():
    raw_events = collection.find()
    events = []

    for event in raw_events:
        if "_id" in event:
            del event["_id"]
        events.append(event)

    return jsonify(events), 200

if __name__ == "__main__":
    app.run(debug=True)
