from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
import RPi.GPIO as GPIO
import time
import os
import logging

load_dotenv()

RELAY_PIN = int(os.getenv("RELAY_PIN", 17))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set in .env")

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

def verify_token():
    token = request.headers.get("x-token")
    if token != SECRET_TOKEN:
        logger.warning("Unauthorized request from %s", request.remote_addr)
        abort(403)

@app.route("/toggle", methods=["POST"])
def toggle():
    verify_token()
    logger.info("Toggle triggered by %s", request.remote_addr)
    GPIO.output(RELAY_PIN, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    return jsonify({"status": "toggled"})

@app.route("/status", methods=["GET"])
def status():
    verify_token()
    logger.info("Status checked by %s", request.remote_addr)
    return jsonify({"status": "online"})
