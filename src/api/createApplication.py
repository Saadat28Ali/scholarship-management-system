from flask import request;

from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import createApplication as dbCreateApplication, searchUser;

def createApplication():

# checking request JSON shape
# --------------------------------------------------

	req_json = request.get_json();
	if not checkDictShape(req_json, {
		"scholarship_id",
		"education_level",
		"passing_percentage",
		"income",
		"minority_category"
	}):
		return TemplateResponse(msg="Request JSON must contain keys scholarship_id, education_level, passing_percentage, income and minority_category.", details={
			"req_json": req_json
		}).getJSON();

# getting token data
# --------------------------------------------------

	token_data: dict = getTokenData(request);
	if not token_data.success:
		return TemplateResponse(msg="JWT err: " + token_data.msg, details={
			"req_json": req_json
		}).getJSON();

# making sure the user is a student
# --------------------------------------------------

	if token_data.details["token_data"]["role"] != "student":
		return TemplateResponse(msg="User must be a student for creating scholarship.", details={
			"req_json": req_json
		}).getJSON();

# searching user and getting user details
# --------------------------------------------------

	result: TemplateResponse = searchUser(
		email = token_data.details["token_data"]["email"],
		password = token_data.details["token_data"]["password"],
		role = token_data.details["token_data"]["role"]
	);
	if not result.success:
		return TemplateResponse(msg="Db Error: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

	user_id = result.details["row"]["user_id"];

# creating application and returning response
# --------------------------------------------------

	result: TemplateResponse = dbCreateApplication(
		user_id = user_id,
		scholarship_id = req_json["scholarship_id"],
		status = "submitted",
		education_level = req_json["education_level"],
		passing_percentage = req_json["passing_percentage"],
		income = req_json["income"],
		minority_category = req_json["minority_category"]
	);
	if not result.success:
		return TemplateResponse(msg="DB Error: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

	return TemplateResponse(success = True, msg = "Created application.", details = {
		"application_id": result.details["application_id"]
	}).getJSON();
