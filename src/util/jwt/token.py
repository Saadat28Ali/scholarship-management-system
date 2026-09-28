import jwt;
from dotenv import load_dotenv;
from os import getenv;
from time import time;

load_dotenv();

def createToken(payload: dict) -> str:
	payload["exp"] = round(time(), 2) + float(30*24*60*60); # token has validity of 30 days
	return jwt.encode(payload, getenv("SECRET"), algorithm="HS256");

def verifyToken(token: str) -> bool:
	try:
		payload: dict = jwt.decode(token, getenv("SECRET"), algorithms=["HS256"]);
	except jwt.exceptions.InvalidTokenError as e:
		print(f"Token error: {e}");
		return False;
	return True;

def getPayload(token: str) -> dict:
	try:
		payload: dict = jwt.decode(token, getenv("SECRET"), algorithms=["HS256"]);
	except jwt.exceptions.InvalidTokenError as e:
		print(f"Token error: {e}");
		return {};
	return payload;
