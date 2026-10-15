from flask import jsonify;

class TemplateResponse:

# class for creating standard responses to be sent
# back to the user and also for internal use
# --------------------------------------------------

	def __init__(
		self,
		success = False,
		msg = "Template response message.",
		details = {},
	):
		self.success = success;
		self.msg = msg;
		self.details = details;

	def getJSON(self):
		return jsonify({
			"success": self.success,
			"msg": self.msg,
			"details": self.details
		});

	def getDict(self):
		return {
			"success": self.success,
			"msg": self.msg,
			"details": self.details
		};
