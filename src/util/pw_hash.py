from bcrypt import hashpw, checkpw, gensalt;

class PwHash:
	ENCODING: str = "utf-8";
	def encode(s: str) -> bytes:
		return s.encode(PwHash.ENCODING);

	def decode(b: bytes) -> str:
		return b.decode(PwHash.ENCODING);

	def hashed(pw: str) -> str:
		pw_bin: bytes = PwHash.encode(pw);
		hashed_pw_bin: bytes = hashpw(pw_bin, gensalt());
		return PwHash.decode(hashed_pw_bin);

	def matches(new_pw: str, stored_pw: str) -> bool:
		new_pw_bin: bytes = PwHash.encode(new_pw);
		stored_pw_bin: bytes = PwHash.encode(stored_pw);
		return checkpw(new_pw_bin, stored_pw_bin);

if __name__ == "__main__":
	# Code for testing
	from sys import argv
	PW: str = "password";
	HASHED_PW: str = PwHash.hashed(PW);
	print(PwHash.matches(argv[1], HASHED_PW));
