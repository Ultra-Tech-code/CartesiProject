import os
import traceback
import logging
import requests
import random

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = os.environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")

MAX_ATTEMPTS = 5
attempts = 0

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

def guess_the_number(computer_guess, user_number, attempt):
    if computer_guess == user_number:
        return "correct"
    elif computer_guess < user_number:
        return "low"
    else:
        return "high"

def handle_advance(data):
    global attempts
    global lower_bound
    global upper_bound

    logger.info(f"Received advance request data {data}")
    status = "accept"

    try:
        user_number = int(hex2str(data["payload"]))
        computer_guesses = []

        random.seed()  
        lower_bound = 1  
        upper_bound = 100 

        for attempt in range(MAX_ATTEMPTS):
            computer_guess = random.randint(lower_bound, upper_bound)
            computer_guesses.append(computer_guess)

            feedback = guess_the_number(computer_guess, user_number, attempt)

            if feedback == "correct":
                result = f"Computer guessed correctly in {attempt + 1} attempts! The number was {user_number}, You Lose ☹️☹️☹️!!"
                logger.info(result)
                break
            else:
                logger.info(f"Computer guessed {computer_guess} (attempt {attempt + 1}), feedback: {feedback}")

                
                if feedback == "high":
                    upper_bound = computer_guess - 1
                else:  # feedback == "low"
                    lower_bound = computer_guess + 1

                lower_bound = max(1, lower_bound)
                upper_bound = min(100, upper_bound)

                computer_guess = random.randint(lower_bound, upper_bound) 

        else:
            result = f"Computer ran out of attempts. The number was {user_number}, You Won 🏅🏅!!"
            logger.info(f"Adding notice with payload: '{result}'")
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