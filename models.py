# app1/models.py
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data

    @property
    def id(self):
        return str(self.user_data.get('_id'))

    @property
    def is_active(self):
        return True  # You can add more checks if needed

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

