from flask import request;

from os.path import abspath, join;
from os import getcwd, mkdir;
from time import strftime;

from ..util.template_response import TemplateResponse;
from ..ai.document_tampering import connect;

try:
	mkdir(join(abspath(getcwd()), "user_documents"));
except FileExistsError:
	pass;

async def verifyDocument():
# checking request form data and saving document
# --------------------------------------------------

	document = request.files.get("document");
	if document is None:
		return TemplateResponse(msg="Form data must contain field document.", details={}).getJSON();

	file_path: str = abspath(join(getcwd(), f"user_documents/{strftime('%Y-%m-%d %H-%M-%S')}.jpg"));
	document.save(file_path);

# verifying document
# --------------------------------------------------

	result: TemplateResponse = await connect(file_path, "passport");
	if not result.success:
		return TemplateResponse(msg="Model error: " + result.msg, details={}).getJSON();
	return TemplateResponse(True, "Model run.", {
		"verification_result": result.details
	}).getJSON();
