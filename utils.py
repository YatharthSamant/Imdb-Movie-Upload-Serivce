import time
from datetime import datetime
import pandas as pd


def upload_csv_to_mongo(file_path, task_id, chunk_size=10000):
    print("start")
    # Initialize progress tracking in Redis
    set_task_status(task_id, "In Progress", 0)

    # Calculate total rows for progress tracking
    total_rows = sum(1 for _ in open(file_path)) - 1  # Exclude header row

    # Read and process CSV in chunks
    chunk_iter = pd.read_csv(file_path, chunksize=chunk_size)
    rows_processed = 0

    for chunk in chunk_iter:
        # Convert chunk to dictionary and upload to MongoDB
        records = chunk.to_dict("records")
        db.file_upload_service.insert_many(records)

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
            mongo.db.file_upload_service.insert_many(records)

            # Update Redis and MongoDB with progress
            rows_processed += len(records)
            progress = (rows_processed / total_rows) * 100
            set_task_status(task_id, "In Progress", int(progress))

        # Mark task as completed in Redis and MongoDB
        set_task_status(task_id, "Completed", 100)
        save_task_metadata_to_mongo(task_id, user_id, "Completed", 100)
        print("stop")
    except Exception as e:
        # If any error occurs, set the task status to failed
        set_task_status(task_id, "Failed", 0)
        save_task_metadata_to_mongo(task_id, user_id, "Failed", 0)
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
    DatabaseManager().instance.db.file_upload_tasks.update_one(
        {"task_id": task_id},  # Find the task by task_id
        {"$set": task_metadata},  # Update the task metadata
        upsert=True  # Create the task if it doesn't exist
    )


def set_task_status(task_id, status, progress=0):
    from file_upload.app1 import redis_client
    redis_client.hmset(f"task:{task_id}", {"status": status, "progress": progress})
