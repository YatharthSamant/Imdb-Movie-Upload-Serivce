import io
import os

import bcrypt
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from file_upload.app import app, db, redis_client


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = False
    app.config['MONGO_URI'] = "mongodb://localhost:27017/test_db"  # Use a test database
    with app.test_client() as client:
        yield client

@pytest.fixture
def setup_mongo():
    # Setup test database
    db.users.delete_many({})
    db.file_upload_tasks.delete_many({})
    db.file_upload_service.delete_many({})
    yield db
    # Cleanup test database
    db.users.delete_many({})
    db.file_upload_tasks.delete_many({})
    db.file_upload_service.delete_many({})

def test_register_user(client, setup_mongo):
    response = client.post('/register', data={
        "username": "test_user",
        "password": "test_password",
        "confirm_password": "test_password"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful!" in response.data

    # Verify the user exists in the database
    user = db.users.find_one({"username": "test_user"})
    assert user is not None

def test_login_user(client, setup_mongo):
    # Add a user to the database
    db.users.insert_one({
        "username": "test_user",
        "password": bcrypt.hashpw("test_password".encode('utf-8'), bcrypt.gensalt())
    })

    response = client.post('/login', data={
        "username": "test_user",
        "password": "test_password"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data

def test_dashboard_access(client, setup_mongo):
    # Simulate a logged-in user
    user = db.users.insert_one({
        "username": "test_user",
        "password": bcrypt.hashpw("test_password".encode('utf-8'), bcrypt.gensalt())
    })

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.inserted_id)

    response = client.get('/dashboard?user_id=' + str(user.inserted_id))
    assert response.status_code == 200
    assert b"User Task Dashboard" in response.data

def test_upload_file_page(client, setup_mongo):
    user_id = "12345"
    response = client.get(f'/upload-file?user_id={user_id}')
    assert response.status_code == 200
    assert b"Upload File" in response.data

@patch("file_upload.app.upload_csv_to_mongo")
def test_upload_file_post(mock_upload, client, setup_mongo):
    user_id = "12345"
    mock_upload.return_value = None

    # Simulate file upload
    data = {
        'file': (io.BytesIO(b"header1,header2\nvalue1,value2"), 'test.csv')
    }
    response = client.post(f'/upload-file?user_id={user_id}', data=data, content_type='multipart/form-data')

    assert response.status_code == 302  # Redirect to dashboard
    assert f'/dashboard?user_id={user_id}' in response.location

def test_get_tasks_api(client, setup_mongo):
    user_id = "12345"
    db.file_upload_tasks.insert_one({
        "task_id": "task_1",
        "user_id": user_id,
        "status": "In Progress",
        "progress": 50
    })

    response = client.get(f'/api/tasks/{user_id}')
    data = response.json

    assert response.status_code == 200
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['task_id'] == "task_1"

def test_uploaded_data_page(client, setup_mongo):
    user_id = "12345"
    response = client.get(f'/uploaded-data?user_id={user_id}')
    assert response.status_code == 200
    assert b"Uploaded Data" in response.data

def test_uploaded_data_api(client, setup_mongo):
    db.file_upload_service.insert_many([
        {"title": "file1", "date_added": "2024-11-15", "release_year": "2023", "duration": 120},
        {"title": "file2", "date_added": "2024-11-14", "release_year": "2022", "duration": 90}
    ])

    response = client.get('/api/uploaded-data?page=1&page_size=1&sort_by=date_added&order=desc')
    data = response.json

    assert response.status_code == 200
    assert len(data['uploads']) == 1
    assert data['uploads'][0]['file_name'] == "file1"
    assert data['page'] == 1
    assert data['total_pages'] == 2

##
@patch("os.path.getsize", return_value=11 * 1024 * 1024 * 1024)  # Mock file size for >10GB
def test_upload_file_no_file(mock_getsize, client):
    # Simulate the case where no file is included
    response = client.post('/upload-file?user_id=12345')

    # Check for error response
    assert response.status_code == 400
    assert b"No file part" in response.data


@patch("os.path.getsize", return_value=1024 * 1024)  # Mock file size to be less than 10MB
def test_upload_file_empty_filename(mock_getsize, client):
    # Simulate the case where the file has no filename
    mock_file = MagicMock()
    mock_file.filename = ''
    data = {
        'file': (io.BytesIO(b"dummy data"), mock_file.filename)
    }

    response = client.post('/upload-file?user_id=12345', data=data, content_type='multipart/form-data')

    # Check for error response
    assert response.status_code == 400
    assert b"No selected file" in response.data


@patch("os.path.getsize", return_value=1024 * 1024)  # Mock file size
def test_upload_file_invalid_format(mock_getsize, client):
    # Simulate the case where the file is not a CSV
    mock_file = MagicMock()
    mock_file.filename = 'test.txt'  # Invalid file extension
    data = {
        'file': (io.BytesIO(b"dummy data"), mock_file.filename)
    }

    response = client.post('/upload-file?user_id=12345', data=data, content_type='multipart/form-data')

    # Check for error response
    assert response.status_code == 400
    assert b"Invalid file format. Only CSV is allowed." in response.data

@patch("os.path.getsize", return_value=1024 * 1024)  # Mock valid file size
@patch("file_upload.app.upload_csv_to_mongo")  # Mock the CSV processing function
def test_upload_file_valid(mock_upload_csv, mock_getsize, client):
    # Simulate the case where the file is valid (CSV and under 10GB)
    mock_file = MagicMock()
    mock_file.filename = 'valid_file.csv'
    data = {
        'file': (io.BytesIO(b"dummy data"), mock_file.filename)
    }

    response = client.post('/upload-file?user_id=12345', data=data, content_type='multipart/form-data')

    # Check for successful redirect
    assert response.status_code == 302
    # Compare response.location directly without decoding
    assert "dashboard?user_id=12345" in response.location
    mock_upload_csv.assert_called_once()  # Ensure the background task is called

