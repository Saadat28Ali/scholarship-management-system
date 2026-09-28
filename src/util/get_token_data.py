from .jwt.token import getPayload;

def getTokenData(request: Request) -> dict:
	auth = request.authorization;
	jwt_token = None;

	if (auth is None or auth.type != "bearer"):
		# invalid auth header
		return {
			"success": False,
			"error": "Invalid authorization header."
		};
	else:
		jwt_token = auth.token;

	if jwt_token is None:
		return {
			"success": False,
			"error": "No JWT passed."
		};

	token_data: dict = getPayload(jwt_token);
	if (not token_data):
		return {
			"success": False,
			"error": "Invalid payload in auth token"
		};

	return {
		"success": True,
		"token_data": token_data
	}
