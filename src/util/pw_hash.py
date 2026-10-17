from bcrypt import hashpw, checkpw, gensalt;

class PwHash:
	ENCODING: str = "utf-16";
	def hashed(pw: str) -> str:
		return hashpw(pw.encode(PwHash.ENCODING), gensalt());

	def matches(new_pw: str, stored_pw: str) -> bool:
		return checkpw(new_pw.encode(PwHash.ENCODING), stored_pw);
