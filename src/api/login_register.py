from ..util.check_dict_shape import checkDictShape;
from ..util.template_response import TemplateResponse;
from ..db.queries import searchUser, createUser;

from flask import request;

def login():

# Checking request JSON shape
# --------------------------------------------------

	req_json: dict = request.get_json();
	if not checkDictShape(req_json, {
		"email",
		"password",
		"role"
	}):
		return TemplateResponse(msg="Request JSON must contain keys 'email', 'password' and 'role'.", details={
			"req_json": req_json
		}).getJSON();

# Searching for user in DB
# --------------------------------------------------

	result: dict = searchUser(req_json.email, req_json.password, req_json.role);
	if not result["success"]:
		return TemplateResponse(msg="DB Err: " + result["msg"], details={
			"req_json": req_json
		}).getJSON();

# Returning response if user is not found
# --------------------------------------------------

	user_details: dict = result["details"].get("row");
	if user_details is None:
		return TemplateResponse(msg="User not found.", details={
			"req_json": req_json
		}).getJSON();

# Returning final response
# --------------------------------------------------

	return TemplateResponse(True, "User found.", {
		"token": createToken({
			"email": req_json["email"],
			"password": req_json["password"],
			"role": req_json["role"]
		})
	}).getJSON();

def register():

# Checking request JSON shape
# --------------------------------------------------

	req_json: dict = request.get_json();
	if not checkDictShape(req_json, {
		"name",
		"email",
		"password"
	}):
		return TemplateResponse(msg="Request JSON must contain keys 'name', 'email', 'password'.", details={
			"req_json": req_json
		}).getJSON();

# Searching for user in DB
# --------------------------------------------------

	result: dict = searchUser(req_json.email, None, "student");
	if not result["success"]:
		return TemplateResponse(msg="DB Err: " + result["msg"], details={
			"req_json": req_json
		}).getJSON();

# Returning response if user already exists
# --------------------------------------------------

	user_details: dict = result["details"].get("row");
	if user_details is not None:
		return TemplateResponse(False, "User already exists.", {
			"req_json": req_json
		}).getJSON();

# Creating user in DB
# --------------------------------------------------

	result: dict = createUser(req_json.name, req_json.email, req_json.password, "student");
	if not result["success"]:
		return TemplateResponse(msg="DB Err: " + result["msg"], details={
			"req_json": req_json
		}).getJSON();

# Returning final response
# --------------------------------------------------

	new_user_id: str = result["details"]["id"];
	return TemplateResponse(msg="User created.").getJSON();
