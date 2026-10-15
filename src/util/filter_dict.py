def filterDictByKeys(d: dict, keyset: set[str]) -> dict:

# returns a dict where the keys match the keys in
# keyset
# --------------------------------------------------

	ret: dict = {};
	for k in keyset:
		if k in d:
			ret[k] = d[k];
	return ret;

def filterDictByFunc(d: dict, func: "Function") -> dict:

# returns a dict where the keys when used as an arg
# in func return True
# --------------------------------------------------

	ret: dict = {};
	for k in d:
		if func(k, d[k]):
			ret[k] = d[k];
	return ret;
