from flask import request;

from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import getScholarship as dbGetScholarship;

def getScholarship():

# checking request JSON shape
# --------------------------------------------------

	req_json = request.get_json();
	if not checkDictShape(req_json, {
		"scholarship_id"
	}):
		return TemplateResponse(msg="Request JSON must contain key scholarship_id.", details={
			"req_json": req_json
		}).getJSON();

# returning final response
# --------------------------------------------------

	result: TemplateResponse = dbGetScholarship(req_json["scholarship_id"]);
	if not result.success:
		return TemplateResponse(msg="DB Error: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

	return TemplateResponse(True, "Scholarship found.", {
		*result.details
	}).getJSON();
