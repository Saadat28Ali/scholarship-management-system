from flask import request;

from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import getScholarship as dbGetScholarship;

DOCUMENTS: dict = {
	"max_age": {
		"birth_certificate",
		"10th_marksheet"
	},
	"max_income": {
		"income_certificate"
	},
	"min_education_level": {
		"10th": {
			"10th_marksheet"
		},
		"12th": {
			"10th_marksheet",
			"12th_marksheet"
		},
		"graduation": {
			"10th_marksheet",
			"12th_marksheet",
			"graduation_marksheet_or_degree"
		},
		"postgraduation": {
			"10th_marksheet",
			"12th_marksheet",
			"graduation_marksheet_or_degree",
			"postgraduation_marksheet_or_degree"
		}
	},
	"min_passing_percentage": {
		"10th": {
			"10th_marksheet"
		},
		"12th": {
			"12th_marksheet"
		},
		"graduation": {
			"graduation_marksheet"
		},
		"postgraduation": {
			"postgraduation_marksheet"
		}
	},
	"minority_category_req": {
		"religion_affidavit"
	},
	"one_child_req": {
		"sgc_affidavit"
	}
};

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

# getting scholarship data from DB
# --------------------------------------------------

	result: TemplateResponse = dbGetScholarship(req_json["scholarship_id"]);
	if not result.success:
		return TemplateResponse(msg="DB Error: " + result.msg, details={
			"req_json": req_json
		}).getJSON();

# getting document requirements
# --------------------------------------------------

	req_docs: dict = {};
	for key in result.details:
		if result.details[key] is not None and key in DOCUMENTS:
			if key in {"min_education_level", "min_passing_percentage"}:
				req_docs[key] = list(DOCUMENTS[key][result.details["min_education_level"]]);
			else:
				req_docs[key] = list(DOCUMENTS[key]);
	result.details["req_docs"] = req_docs;

# returning final response
# --------------------------------------------------

	return TemplateResponse(True, "Scholarship found.", {
		**result.details
	}).getJSON();
