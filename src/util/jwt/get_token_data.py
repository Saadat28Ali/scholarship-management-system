from .token import getPayload, verifyToken;
from ..template_response import TemplateResponse;
from flask import Request;

def getTokenData(request: Request) -> dict:
	auth = request.authorization;
	jwt_token = None;

	if (auth is None or auth.type != "bearer"):
		# invalid auth header
		return TemplateResponse(msg="Invalid authorization header.");
	else:
		jwt_token = auth.token;

	if jwt_token is None:
		return TemplateResponse(msg="No JWT passed.");

	if not verifyToken(jwt_token):
		return TemplateResponse(msg="JWT could not be verified. Maybe it is expired?");

	token_data: dict = getPayload(jwt_token);
	if (not token_data):
		return TemplateResponse(msg="Invalid payload in auth token");

	return TemplateResponse(True, "Token data extracted.", {
		"token_data": token_data
	});
