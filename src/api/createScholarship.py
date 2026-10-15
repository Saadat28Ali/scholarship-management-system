from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
# from ..db.queries import createScholarship as dbCreateScholarship;

from flask import request;

def createScholarship():

# checking request JSON shape
# --------------------------------------------------

	req_json = request.get_json();
	if not checkDictShape(req_json, {
		"name",
		"min_education_level",
		"min_passing_percentage",
		"max_age",
		"max_income",
		"one_child_req",
		"minority_category_req",
		"benefit_amount",
		"deadline"
	}):
		return TemplateResponse(msg="Request JSON must contain keys ", details={
			"req_json": req_json
		}).getJSON();

# getting token data
# --------------------------------------------------

	token_data: dict = getTokenData(request);
	if not token_data.success:
		return TemplateResponse(msg="JWT err: " + token_data.msg, details={
			"req_json": req_json
		}).getJSON();

# making sure the user is an officer and an admin
# --------------------------------------------------

	if token_data.details["token_data"]["role"] != "officer":
		return TemplateResponse(msg="User must be an officer for creating scholarship.", details={
			"req_json": req_json
		}).getJSON();

	if token_data.details["token_data"]["is_admin"] != 1:
		return TemplateResponse(msg="User must be an admin for creating scholarship.", details={
			"req_json": req_json
		}).getJSON();

# creating scholarship and returning result
# --------------------------------------------------

	result: TemplateResponse = dbCreateScholarship(*req_json);
	if not result.success:
		return TemplateResponse(msg="DB error: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

	return TemplateResponse(success=True, msg="Created scholarship.").getJSON();
