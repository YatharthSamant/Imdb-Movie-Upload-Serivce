# app1.py
import uuid
from datetime import datetime
from threading import Thread

import bcrypt
import pandas as pd
import redis
from bson import ObjectId
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_login import login_required, logout_user, LoginManager, login_user
from pymongo import MongoClient, DESCENDING, ASCENDING
import os
from file_upload.config import Config
from file_upload.enums import UploadStatus
from file_upload.models import User
from file_upload.forms import LoginForm, RegistrationForm

redis_client = redis.StrictRedis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True  # Decode byte responses to strings automatically
)

app = Flask(__name__)
app.config.from_object(Config)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize PyMongo client
client = MongoClient(app.config['MONGO_URI'])
db = client.get_default_database()  # Connect to default database

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def upload_csv_to_mongo(file_path, task_id, user_id, chunk_size=10000):
    # Initialize progress tracking in Redis
    set_task_status(task_id, UploadStatus.IN_PROGRESS, 0)

    # Calculate total rows for progress tracking
    total_rows = sum(1 for _ in open(file_path)) - 1  # Exclude header row

    # Read and process CSV in chunks
    chunk_iter = pd.read_csv(file_path, chunksize=chunk_size)
    rows_processed = 0

    for chunk in chunk_iter:
        # Convert chunk to dictionary and upload to MongoDB
        records = chunk.to_dict("records")
        db.movies_data.insert_many(records)

        # Update Redis with progress
        rows_processed += len(records)
        progress = (rows_processed / total_rows) * 100
        redis_client.set(f"{task_id}_progress", int(progress))

    # Mark completion
    redis_client.set(f"{task_id}_file_upload_progress", 100)

    # Calculate total rows for progress tracking
    total_rows = sum(1 for _ in open(file_path)) - 1  # Exclude header row

    try:
        # Read and process CSV in chunks
        chunk_iter = pd.read_csv(file_path, chunksize=chunk_size)
        rows_processed = 0

        for chunk in chunk_iter:
            # Convert chunk to dictionary and upload to MongoDB
            records = chunk.to_dict("records")
            db.movies_data.insert_many(records)

            # Update Redis and MongoDB with progress
            rows_processed += len(records)
            progress = (rows_processed / total_rows) * 100
            set_task_status(task_id, UploadStatus.IN_PROGRESS, int(progress))

        # Mark task as completed in Redis and MongoDB
        set_task_status(task_id, UploadStatus.COMPLETED, 100)
        save_task_metadata_to_mongo(task_id, user_id, UploadStatus.COMPLETED, 100)
    except Exception as e:
        # If any error occurs, set the task status to failed
        set_task_status(task_id, UploadStatus.FAILED, 0)
        save_task_metadata_to_mongo(task_id, user_id, UploadStatus.FAILED, 0)
        print(f"Error occurred: {e}")


def save_task_metadata_to_mongo(task_id, user_id, status, progress):
    task_metadata = {
        "task_id": task_id,
        "user_id": user_id,
        "status": status,
        "progress": progress,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    # Insert or update task metadata in the task_progress_collection
    db.file_upload_tasks.update_one(
        {"task_id": task_id},  # Find the task by task_id
        {"$set": task_metadata},  # Update the task metadata
        upsert=True  # Create the task if it doesn't exist
    )


def set_task_status(task_id, status, progress=0):
    redis_client.hmset(f"task:{task_id}", {"status": status, "progress": progress})

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Main route to upload a file
@app.route("/upload-file", methods=["GET", "POST"])
def upload_file():
    user_id = request.args.get('user_id') or session["_user_id"]
    if request.method == "POST":
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not file or not file.filename.endswith('.csv'):
            return jsonify({"error": "Invalid file format. Only CSV is allowed."}), 400

        # Check file size
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

        if file_size > 10 * 1024 * 1024 * 1024:  # 10GB in bytes
            return jsonify({"error": "File size exceeds the maximum limit of 10GB"}), 400

        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        # Save the uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        save_task_metadata_to_mongo(task_id, user_id, UploadStatus.IN_PROGRESS, 0)
        # Start the background task to process the file
        Thread(target=upload_csv_to_mongo, args=(file_path, task_id, user_id)).start()
        return redirect(f"/dashboard?user_id={user_id}")

    return render_template("upload.html")

@app.route("/", methods=["GET"])
def home():

    return redirect("/register")

@app.route("/register", methods=["GET","POST"])
def register():
    if session and session.get("_user_id"):
        return redirect(url_for("dashboard"))

    form = RegistrationForm()
    if request.method == 'POST':
        users = db.users
        existing_user = users.find_one({"username": form.username.data})

        if existing_user:
            flash("User already exists!")
        else:
            hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
            users.insert_one({"username": form.username.data, "password": hashed_password})
            flash("Registration successful!")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET","POST"])
def login():
    if session and '_user_id' in session:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if request.method == 'POST':
        users = db.users
        user = users.find_one({"username": form.username.data})

        if user and bcrypt.checkpw(form.password.data.encode('utf-8'), user['password']):
            user_data = User(user)
            login_user(user_data)
            return redirect(url_for("dashboard", user_id=user_data.id))

        flash("Invalid username or password")

    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = request.args.get('user_id') or session["_user_id"]
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Fetch tasks for the given user_id from the task_progress_collection
    tasks = list(db.file_upload_tasks.find({"user_id": user_id}))

    # Prepare task data for rendering
    task_data = []
    for task in tasks:
        task_data.append({
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"]
        })

    return render_template("dashboard.html", tasks=task_data, user_id=user_id)

@app.route('/api/tasks/<user_id>', methods=['GET'])
def get_tasks(user_id):
    tasks = list(db.file_upload_tasks.find({"user_id": user_id}))
    for task in tasks:
        task["_id"] = str(task["_id"])  # Convert ObjectId to string
    return jsonify(tasks=tasks)


@app.route('/uploaded-data', methods=['GET'])
def uploaded_data_page():
    # Render the HTML template for the uploaded data page
    user_id = request.args.get('user_id') or session["_user_id"]
    return render_template('uploaded_data.html', user_id=user_id)

@app.route('/api/uploaded-data', methods=['GET'])
def get_uploaded_data():
    # Retrieve query parameters
    page = int(request.args.get('page', 1))  # Default to page 1
    page_size = int(request.args.get('page_size', 10))  # Default to 10 items per page
    sort_by = request.args.get('sort_by', 'date_added')  # Default sort field
    sort_order = request.args.get('order', 'desc')  # Default sort order

    # Set sorting direction
    sort_direction = DESCENDING if sort_order == 'desc' else ASCENDING

    # MongoDB query with pagination and sorting
    skips = (page - 1) * page_size
    cursor = db.movies_data.find().sort(sort_by, sort_direction).skip(skips).limit(page_size)

    # Format results
    uploads = []
    for upload in cursor:
        uploads.append({
            "file_name": upload.get("title"),
            "date_added": upload.get("date_added"),
            "release_date": upload.get("release_year"),
            "duration": upload.get("duration")
        })
    # Get total count for pagination metadata
    total_count = db.movies_data.count_documents({})
    total_pages = (total_count + page_size - 1) // page_size

    # Return JSON response with pagination and sorting info
    return jsonify({
        "uploads": uploads,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_count": total_count,
        "sort_by": sort_by,
        "sort_order": sort_order
    })


@app.route("/debug-templates")
def debug_templates():
    import os
    templates_path = os.path.join(os.getcwd(), "templates")
    templates_list = os.listdir(templates_path)
    return f"Templates found: {templates_list}"

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None


if __name__ == "__main__":
    app.run(debug=True)
