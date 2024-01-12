from os import environ
import traceback
import logging
import requests
import random

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")


def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")

def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()

def guess_the_number(user_guess, secret_number):
    # Check if the guess is correct
    if user_guess == secret_number:
        return "You Won"
    elif user_guess < secret_number:
        return "Too low! Try again."
    else:
        return "Too high! Try again."

def handle_advance(data):
    logger.info(f"Received advance request data {data}")
    status = "accept"

    # Generate secret_number from one to 100
    secret_number = random.randint(1, 100)

    try:
        user_guess = int(hex2str(data["payload"]))
        logger.info(f"Received input: {user_guess}")

        # Evaluates expression
        result = guess_the_number(user_guess, secret_number)

        # Emits notice with result
        logger.info(f"Adding notice with payload: '{result}' The correct number was '{secret_number}'")
        response = requests.post(rollup_server + "/notice", json={"payload": str2hex(str(result))})
        logger.info(f"Received notice status {response.status_code} body {response.content}")

    except Exception as e:
        status = "reject"
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        logger.error(msg)
        response = requests.post(rollup_server + "/report", json={"payload": str2hex(msg)})
        logger.info(f"Received report status {response.status_code} body {response.content}")

    return status  

def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    return "accept"

handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
