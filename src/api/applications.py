from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import getApplications;

from flask import request;

def applications():
	req_json: dict = request.get_json();
	if not checkDictShape(req_json, {
		"offset",
		"limit"
	}):
		return TemplateResponse(msg="Request JSON must contain keys 'offset' and 'limit'.", details={
			"req_json": req_json
		}).getJSON();

	token_data: TemplateResponse = getTokendata(request);
	if not token_data.success:
		return TemplateResponse(msg="JWT Err: " + token_data.msg, details=token_data.details);

	result: dict = {};
	if token_data.details["token_data"]["role"] == "officer":
		result: dict = getApplications(user_id=None, offset=offset, limit=limit);
	else:
		result = searchUser(
			token_data.details["token_data"]["email"],
			token_data.details["token_data"]["password"],
			token_data.details["token_data"]["role"],
		);
		if not result.success:
			return TemplateResponse(msg="Could not find user from token data., DB err: " + result.msg, details={
				"req_json": req_json
			}).getJSON();
		if result.details["row"] is None:
			return TemplateResponse(msg="User from token data does not exist.", details={
				"req_json": req_json
			}).getJSON();

		result = getApplications(user_id=result.details["row"]["user_id"], offset=offset, limit=limit);

	if not result["success"]:
		return TemplateResponse(msg="DB Err: " + result["msg"], details={
			"req_json": req_json
		}).getJSON();

	applications: list[dict] | None = result["details"].get("rows");
	if applications is None:
		return TemplateResponse(success=True, msg="No applications in system.").getJSON();

	return TemplateResponse(success=True, msg="Applications found.", details={
		"rows": [
			filterDictByKeys(row, {
				"application_id",
				"user_name",
				"scholarship_name",
				"status",
				"education_level",
				"passing_percentage",
				"income",
				"timestamp",
				"minority_category"
			}) for row in applications
		]
	}).getJSON();
