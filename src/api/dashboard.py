from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import getDashboard;

from flask import request;

def dashboard():
# checking request JSON shape
# --------------------------------------------------

	req_json: dict = request.get_json();
	if not checkDictShape(req_json, {
		"days"
	}):
		return TemplateResponse(msg="Request JSON must contain key 'days'.", details={
			"req_json": req_json
		}).getJSON();

# getting token data
# --------------------------------------------------

	token_data: dict = getTokenData(request);
	if not token_data.success:
		return TemplateResponse(msg="JWT err: " + token_data.msg, details={
			"req_json": req_json
		}).getJSON();

# restricting dashboard analytics for only officers
# --------------------------------------------------

	if token_data.details["token_data"]["role"] != "officer":
		return TemplateResponse(msg="Dashboard data is only accessible for officers.", details={
			"req_json": req_json
		});

# returning dashboard analytics
# --------------------------------------------------

	result: dict = getDashboard(days=days);
	if not result.success:
		return TemplateResponse(msg="DB err: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

	return TemplateResponse(True, "Dashboard data fetched.", {
		"rows": result.details["rows"]
	}).getJSON();
