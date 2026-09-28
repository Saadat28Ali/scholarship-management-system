from ..util.template_response import TemplateResponse;

def health():
	return TemplateResponse(True, "Server is working.").getJSON();
