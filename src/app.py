from flask import Flask, request;
from flask_cors import CORS;

from os import path, getcwd;
from time import strftime;

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
from .api.getScholarship import getScholarship;
from .api.verifyDocument import verifyDocument;

ROOT_DIR: str = path.abspath(getcwd())

app = Flask(__name__);
CORS(app);

@app.before_request
def logRequest():
	print(f"REQS [{strftime('%Y-%m-%d %H:%M:%S')}]: {request.method} {request.url}, from: {request.remote_addr}");
	print("-"*100);

@app.after_request
def logResponse(response):
	print(f"RESP [{strftime('%Y-%m-%d %H:%M:%S')}]: {response.status} for {request.method} {request.url}, from: {request.remote_addr}");
	print("-"*100);
	return response;

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
app.add_url_rule(rule="/getScholarship", view_func=getScholarship, methods=["POST"]);
app.add_url_rule(rule="/verifyDocument", view_func=verifyDocument, methods=["POST"]);

if __name__ == "__main__":
	app.run(debug=True, host="127.0.0.1", port=5000);

