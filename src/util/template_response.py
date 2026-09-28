from flask import jsonify;

class TemplateResponse:
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
