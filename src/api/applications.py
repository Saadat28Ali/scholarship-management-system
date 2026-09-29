from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
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

	result: dict = getApplications(user_id=None, offset=offset, limit=limit);
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
