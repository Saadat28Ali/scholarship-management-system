from os import path, mkdir, scandir, remove, getcwd;
from time import strftime;

from flask import request;

from ..util.template_response import TemplateResponse;
from ..util.check_dict_shape import checkDictShape;
from ..util.filter_dict import filterDictByKeys;
from ..ai.connect import connect;
from ..util.jwt.get_token_data import getTokenData;
from ..db.queries import searchUser, searchApplications, createDocument, createAuditLog;

ROOT_DIR: str = path.abspath(getcwd());

async def verify():
	document_type: str = request.form.get("document_type");
	application_id: str = request.form.get("application_id");

	if document_type is None or application_id is None:
		return TemplateResponse(msg="Request form data must contain keys 'document_type' and 'application_id'.", details={
			"form": request.form
		}).getJSON();

	if "file" not in request.files:
		return TemplateResponse(msg="Request files must contain key 'image'.").getJSON();

	token_data: dict = getTokenData(request);
	if not token_data.success:
		return TemplateResponse(msg="JWT err: " + token_data.msg, details={
			"form": request.form
		}).getJSON();

	result: TemplateResponse = searchUser(
		token_data.details["token_data"]["email"],
		token_data.details["token_data"]["password"],
		token_data.details["token_data"]["role"],
	);
	if not result.success:
		return TemplateResponse(msg="DB err: " + result.msg, details={
			"form": request.form
		}).getJSON();
	if result.details["row"] is None:
		return TemplateResponse(msg="User in JWT could not be found on DB.", details={
			"form": request.form
		}).getJSON();

	user_data: dict = result.details["row"];

	result: TemplateResponse = searchApplications(application_id);
	if not result.success:
		return TemplateResponse(msg="DB err: " + result.msg, details={
			"form": request.form
		}).getJSON();

	if result.details["row"] is None:
		return TemplateResponse(msg="Could not find application.", details={
			"form":> request.form
		}).getJSON();

	try:
		mkdir(path.abspath(path.join(ROOT_DIR, "./ocrfiles")));
	except FileExistsError:
		pass;

	filename: str = path.abspath(path.join(ROOT_DIR, f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png"));
	with open(filename, "wb") as fh:
		request.files["file"].save(fh);
		print(f"File saved as {filename}.");

	result: dict = searchApplications(application_id=application_id);
	if not result.success:
		return TemplateResponse(msg="Could not find application. DB err: " + result.msg, details={
			"form": request.form
		}).getJSON();
	if result.details["row"] is None:
		return TemplateResponse(msg="Given application does not exist.", details={
			"form": request.form
		}).getJSON();

	result: dict = createDocument(
		type=document_type,
		user_id=user_data["user_id"],
		application_id=result.details["row"]["application_id"],
		path=filename
	);
	if not result.success:
		return TemplateResponse(msg="Could not create document in DB. DB err: " + result.msg, details={
			"form": request.form
		}).getJSON();
	document_id: int = result.details["id"];

	result: dict = await connect(filename, document_type);
	if not result.success:
		return result.getJSON();

	audit_log_result: dict = createAuditLog(
		result="tampered" if result.details["model_response"]["tamper_detection"]["is_tampered"] else "verified",
		confidence=1 - float(result.details["model_response"]["tamper_detection"]["anomaly_score"]),
		document_id=document_id,
		user_id=user_data["user_id"],
		application_id=application_id
	);
	if not audit_log_result.success:
		return TemplateResponse(msg="Could not create audit log. DB err: " + audit_log_result.msg, details={
			"form": request.form
		}).getJSON();

	return TemplateResponse(True, "Model run.", {
		"model_response": filterDictByKeys(result.details["model_response"], {
			"success",
			"error_message",
			"tamper_detection",
			"ocr"
		})
	}).getJSON();
