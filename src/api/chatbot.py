from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.jwt.get_token_data import getTokenData;
from ..ai.chatbot import respond;

from flask import request;

CHATBOT_PROFILE_FIELDS = {
	"_pending_question",
	"_last_results",
	"_last_offset",
	"_last_total",
	"_last_filters"
};

def chatbot():
# checking request JSON shape
# --------------------------------------------------

	req_json: dict = request.get_json();
	if not checkDictShape(req_json, {
		"message",
		"profile"
	}):
		return TemplateResponse(msg="Request JSON must contain keys 'message' and 'profile'.", details={
			"req_json": req_json
		}).getJSON();

	if not checkDictShape(req_json["profile"], CHATBOT_PROFILE_FIELDS):
		return TemplateResponse(msg="Profile dictionary must contain keys " + ", ".join(CHATBOT_PROFILE_FIELDS) + ".", details={
			"req_json": req_json
		}).getJSON();

# returning final response
# -------------------------------------------------

	chat_response: str = respond(req_json["message"], req_json["profile"]);
	return TemplateResponse(success=True, msg="Chat message processed.", details={
		"updated_profile": req_json["profile"],
		"chat_response": chat_response
	}).getJSON();
