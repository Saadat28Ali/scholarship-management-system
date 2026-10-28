from dotenv import load_dotenv
import httpx;

from os import getenv

from ..util.template_response import TemplateResponse;

load_dotenv();

# --------------------------------------------------

async def connect(filename: str, document_type: str) -> TemplateResponse:

# querying model server for tamper detection
# --------------------------------------------------

	try:
		async with httpx.AsyncClient(timeout = 240.0) as client:
			with open(filename, "rb") as f:
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
		print(type(e));
		return TemplateResponse(msg="Model err: " + str(e), details={
			"filename": filename
		});
