
# IMDb Movie Upload Service

The **IMDb Movie Upload Service** is a web application designed to upload, process, and display movie data in a structured and user-friendly way. Users can upload CSV files containing movie data, filter and sort the uploaded data, and view the details in a paginated table.

## Features

- **User Registration and Login**:
  - Secure user registration with hashed passwords.
  - Redirect to the dashboard if already logged in.

- **File Upload**:
  - Upload CSV files containing movie data.
  - Validate file type (only `.csv` allowed) and file size (maximum 10GB).
  - Background task processes and stores data.

- **Data Display and Filtering**:
  - View uploaded movie data in a paginated table.
  - Apply sorting and ordering filters (e.g., by release date, duration, or date added).

- **Error Handling**:
  - Comprehensive error handling for file uploads and invalid inputs.
  - User-friendly messages for better interaction.

---

## Installation and Setup

### Prerequisites
- Python 3.8 or later
- MongoDB (for storing user and movie data)
- A modern web browser

### Steps to Run Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/YatharthSamant/Imdb-Movie-Upload-Serivce.git
   cd Imdb-Movie-Upload-Serivce
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the project root directory with the following details:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   MONGO_URI=mongodb://localhost:27017/your_database_name
   UPLOAD_FOLDER=./uploads
   ```

4. Run the application:
   ```bash
   flask run
   ```
---
## Database 

- **User Table: The user table stores user credentials.**:
  ```bash
      {
      "user": {
        "indexes": [
          {
            "fields": ["username"],
            "unique": true
          }
        ],
        "schema": {
          "_id": {
            "type": "ObjectId"
          },
          "username": {
            "type": "str"
          },
          "password": {
            "type": "str"
          }
        }
      },
      
      Example : 
    {
    "_id": ObjectId("67388219712f6fe85e0fd194"),
    "username": "yath",
    "password": Binary.createFromBase64("JDJiJDEyJFBHWVQvcnp3SGZHbG80Vnd1YkFWcmVkM1VrVVVNUUJpV09NVjlXOE1SdWt1MUlMbnRMLjk2", 0)
    } 
  ```


- **File Upload Tasks Table**
  - The file_upload_tasks table stores information about the file upload tasks, including the status, progress, and user ID associated with the task
      ```bash
        "file_upload_tasks": {
        ""indexes": [
          {
            "fields": { "task_id": 1 },
            "unique": true
          },
          {
            "fields": { "user_id": 1 },
            "unique": false
          }
        ]
        "schema": {
          "_id": {
            "type": "ObjectId"
          },
          "task_id": {
            "type": "str"
          },
          "created_at": {
            "type": "ISODate"
          },
          "progress": {
            "type": "int"
          },
          "status": {
            "type": "str"
          },
          "updated_at": {
            "type": "ISODate"
          },
          "user_id": {
            "type": "str"
          }
        }
      },
    
    Example:
      {
      "_id": ObjectId("67388211c0ed5e66330fec2d"),
      "task_id": "1c44231c-4cb0-4992-81a3-8d515c19bc72",
      "created_at": ISODate("2024-11-16T11:29:21.587Z"),
      "progress": 0,
      "status": "In Progress",
      "updated_at": ISODate("2024-11-16T11:29:21.587Z"),
      "user_id": "12345"
    }
    ```

- **MOVIES_DATA Table**:
- The MOVIES_DATA table stores the movie data extracted from the uploaded CSV files. The structure of this table is based on the contents of the CSV file.
---

## Usage

### User Registration and Login
1. Go to `/register` to create a new account.
2. Log in via `/login` to access the dashboard.

### Upload CSV Files
1. Navigate to `/upload-file` after logging in.
2. Upload a valid CSV file (e.g., movies.csv).
3. The file will be processed, and the data will be available on your dashboard.

### Filter and Sort Uploaded Data
1. Use the filters on the dashboard to sort data by release date, duration, or date added.
2. View paginated results with easy navigation controls.

---

## API Endpoints

### `/api/uploaded-data`
- **Method**: GET
- **Parameters**:
  - `user_id`: ID of the logged-in user.
  - `page`: Current page number for pagination.
  - `per_page`: Number of records per page.
  - `sort_by`: Field to sort by (`date_added`, `release_year`, `duration`).
  - `order`: Sort order (`asc`, `desc`).

---

## Testing

To run the test suite:
```bash
pytest tests/test.py
```

Tests include:
- User registration and login.
- File upload validations (type and size).
- API endpoint responses and functionality.

---

## Folder Structure

```
Imdb-Movie-Upload-Service/
│
├── app.py                 # Main Flask application
├── templates/             # HTML templates
├── static/                # Static files (CSS, JS)
├── tests/                 # Unit tests
├── uploads/               # Uploaded files
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## Contributing

Contributions are welcome! If you encounter bugs or want to add features:
1. Fork the repository.
2. Create a new branch (`feature/your-feature-name`).
3. Commit and push your changes.
4. Submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgements

This project was created as a demonstration of a movie upload and filtering system. Special thanks to all contributors and the Flask community for their support.
