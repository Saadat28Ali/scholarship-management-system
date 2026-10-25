from flask import Flask;
from flask_cors import CORS;

from os import path, getcwd;

from .util.template_response import TemplateResponse;
from .api.login_register import login, register;
from .api.health import health;
from .api.scholarships import scholarships;
from .api.applications import applications;
from .api.model import verify;
from .api.dashboard import dashboard;
from .api.createScholarship import createScholarship;
from .api.chatbot import chatbot;
from .api.createApplication import createApplication;
#from .api.getScholarship import getScholarship;

ROOT_DIR: str = path.abspath(getcwd())

app = Flask(__name__);
CORS(app);

app.add_url_rule(rule="/login", view_func=login, methods=["POST"]);
app.add_url_rule(rule="/register", view_func=register, methods=["POST"]);
app.add_url_rule(rule="/health", view_func=health, methods=["GET"]);
app.add_url_rule(rule="/scholarships", view_func=scholarships, methods=["POST"]);
app.add_url_rule(rule="/applications", view_func=applications, methods=["POST"]);
app.add_url_rule(rule="/verify", view_func=verify, methods=["POST"]);
app.add_url_rule(rule="/dashboard", view_func=dashboard, methods=["POST"]);
app.add_url_rule(rule="/createScholarship", view_func=createScholarship, methods=["POST"]);
app.add_url_rule(rule="/chatbot", view_func=chatbot, methods=["POST"]);
app.add_url_rule(rule="/createApplication", view_func=createApplication, methods=["POST"]);

if __name__ == "__main__":
	app.run(debug=True, host="127.0.0.1", port=5000);
