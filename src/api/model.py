from os import path, mkdir, scandir, remove, getcwd;
from time import strftime;

from flask import request;

from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..ai.connect import connect;

ROOT_DIR: str = path.abspath(getcwd());

async def verify():
	document_type: str = request.form.get("document_type");

	if document_type is None:
		return TemplateResponse(msg="Request form data must contain key 'document_type'.", details={
			"form": request.form
		}).getJSON();

	if "file" not in request.files:
		return TemplateResponse(msg="Request files must contain key 'image'.").getJSON();

	try:
		mkdir(path.abspath(path.join(ROOT_DIR, "./ocrfiles")));
	except FileExistsError:
		pass;

	filename: str = path.abspath(path.join(ROOT_DIR, f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png"));
	with open(filename, "wb") as fh:
		request.files["file"].save(fh);
		print(f"File saved as {filename}.");

	result: dict = await connect(filename, document_type);
	if not result.success:
		return result.getJSON();

	return TemplateResponse(True, "Model run.", {
		"model_response": filterDictByKeys(result.details["model_response"], {
			"success",
			"error_message",
			"tamper_detection",
			"ocr"
		})
	}).getJSON();
