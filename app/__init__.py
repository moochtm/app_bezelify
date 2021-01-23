from flask import Flask

app = Flask(__name__)
app.secret_key = "bezelify"

from app import views
from app.utils import bezelify


