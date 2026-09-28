from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;

def scholarships():
	req_json: request.get_json();
	if not checkDictShape(req_json, {
		"offset",
		"limit"
	}):
		return TemplateResponse(msg="Request JSON must contain keys 'offset' and 'limit'.", details={
			"req_json": req_json
		}).getJSON();

	result: dict = getScholarships(req_json.offset, req_json.limit);
	if not result["success"]:
		return TemplateResponse(msg="DB Err: " + result["msg"], details={
			"req_json": req_json
		}).getJSON();

	scholarships: list[dict] = result["details"].get("rows");
	if scholarships is None:
		return TemplateResponse(success=True, msg="No scholarships available.").getJSON();

	return TemplateResponse(success=True, msg="Scholarships found.", details={
		"rows": [
			filterDictByKeys(row, {
				"name",
				"min_education_level",
				"min_passing_percentage",
				"max_age",
				"one_child_req",
				"minority_category_req",
				"benefit_amount",
				"deadline"
			}) for row in scholarships["rows"]
		]
	}).getJSON();

