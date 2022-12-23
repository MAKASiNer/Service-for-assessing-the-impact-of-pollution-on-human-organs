# -----------------database------------- 
from web import models
models.mk_database()

# -----------------application---------- 
from config import *
from flask import Flask
app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
app.static_folder = STATIC_FOLDER
app.template_folder= TEMPLATE_FOLDER

# -----------------mail----------------- 
from flask_mail import Mail
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
app.config['MAIL_MAX_EMAILS'] = MAIL_MAX_EMAILS
app.config['MAIL_ASCII_ATTACHMENTS'] = MAIL_ASCII_ATTACHMENTS
mail = Mail(app)

# -----------------views---------------- 
from web import views

# -----------------tasks---------------- 
from flask_apscheduler import APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
from web import tasks
scheduler.start()
