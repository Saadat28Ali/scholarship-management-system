from flask import Request;

def checkDictShape(d: dict, keys: set[str]) -> bool:

	# Checks the input dictionary and makes sure all the
	# strings in keys set are present in dictionary d

	ret: bool = True;
	for each in keys:
		if each not in d: return False;
	return ret;
