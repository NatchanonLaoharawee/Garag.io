from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
import RPi.GPIO as GPIO
import time
import os

load_dotenv()

RELAY_PIN = int(os.getenv("RELAY_PIN", 17))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set in .env")

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)

app = Flask(__name__)

def verify_token():
    token = request.headers.get("x-token")
    if token != SECRET_TOKEN:
        abort(403)

@app.route("/toggle", methods=["POST"])
def toggle():
    verify_token()
    GPIO.output(RELAY_PIN, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    return jsonify({"status": "toggled"})

@app.route("/status", methods=["GET"])
def status():
    verify_token()
    return jsonify({"status": "online"})

