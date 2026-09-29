from os import path, getcwd, getenv;

from dotenv import load_dotenv
import httpx;

from ..util.template_response import TemplateResponse;

load_dotenv();

# GLOBALS
# --------------------------------------------------

ROOT_DIR: str = path.abspath(getcwd());

# --------------------------------------------------

async def connect(filename: str, document_type: str):
	try:
		async with httpx.AsyncClient(timeout = 60.0) as client:
			with open(path.abspath(path.join(ROOT_DIR, filename)), "rb") as f:
				response = await client.post(
					getenv("MODEL_URL"),
					files = {
						"file": f
					},
					data = {
						"doc_type": document_type
					}
				);
				response.raise_for_status();
				return TemplateResponse(True, "Model run.", {
					"model_response": response.json()
				});
	except Exception as e:
		return TemplateResponse(msg="Model err: " + str(e), details={
			"filename": filename
		});
