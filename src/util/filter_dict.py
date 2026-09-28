def filterDictByKeys(d: dict, keyset: set[str]) -> dict:
	ret: dict = {};
	for k in keyset:
		if k in d:
			ret[k] = d[k];
	return ret;

def filterDictByFunc(d: dict, func: "Function") -> dict:
	ret: dict = {};
	for k in d:
		if func(k, d[k]):
			ret[k] = d[k];
	return ret;
