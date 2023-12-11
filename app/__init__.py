from flask import Flask
import os
import sys

if getattr(sys, 'frozen', False):
    print(f"Running in pyinstaller mode...")
    template_folder = os.path.join(sys._MEIPASS, 'app/templates')
    static_folder = os.path.join(sys._MEIPASS, 'app/static')
    print(f"template folder: {template_folder}")
    print(f"static folder: {static_folder}")
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

app.secret_key = "bezelify"

from app import views
from app.utils import bezelify


