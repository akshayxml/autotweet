import os
import time
import requests
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh") # Added default
NTFY_CONFIRM_TOPIC = os.getenv("NTFY_CONFIRM_TOPIC")
NTFY_RESPONSE_TOPIC = os.getenv("NTFY_RESPONSE_TOPIC")
POLL_READ_TIMEOUT_SECS = 300

def request_confirmation(tweet_text: str, timeout: int = None) -> str:
    """
    Requests confirmation via ntfy push notification to a phone.
    Returns the decision ('approve', 'reject', 'regenerate') or raises TimeoutError.
    """
    if not all([NTFY_SERVER, NTFY_CONFIRM_TOPIC, NTFY_RESPONSE_TOPIC]):
        raise ValueError("NTFY_SERVER, NTFY_CONFIRM_TOPIC, and NTFY_RESPONSE_TOPIC environment variables must be set for ntfy confirmation.")

    confirmation_id = str(uuid.uuid4())
    base_ntfy_url = NTFY_SERVER.rstrip('/')

    message_payload = {
        "topic": NTFY_CONFIRM_TOPIC,
        "message": f"Approve tweet?\n\n---\n{tweet_text}\n---",
        "title": "AutoTweet: Confirm Tweet",
        "priority": 4, 
        "tags": ["bell", "incoming_call"], 
        "actions": [
            {
                "action": "http", "label": "Approve ✅",
                "url": f"{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}", "method": "POST",
                "body": json.dumps({"id": confirmation_id, "decision": "approve"}),
                "headers": {"Content-Type": "application/json", "X-Title": f"Approved tweet {confirmation_id[:8]}"}, "clear": True,
            },
            {
                "action": "http", "label": "Discard ❌",
                "url": f"{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}", "method": "POST",
                "body": json.dumps({"id": confirmation_id, "decision": "reject"}),
                "headers": {"Content-Type": "application/json", "X-Title": f"Rejected tweet {confirmation_id[:8]}"}, "clear": True,
            }
        ]
    }
    try:
        requests.post(base_ntfy_url, json=message_payload, timeout=10)
        print(f"Confirmation request sent to ntfy topic '{base_ntfy_url}/{NTFY_CONFIRM_TOPIC}'. Waiting for response on '{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}' for ID {confirmation_id[:8]}...")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error sending ntfy notification to {base_ntfy_url}: {e}")

    poll_url = f"{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}/json"
    start_time = time.time()
    
    while True:
        if timeout is not None and time.time() - start_time > timeout:
            raise TimeoutError(f"No response received on ntfy topic {poll_url} for ID {confirmation_id[:8]} within the expected timeframe.")
            
        try:
            # Poll with a short read timeout to allow checking the total elapsed time periodically.
            resp = requests.get(poll_url, stream=True, timeout=POLL_READ_TIMEOUT_SECS)
            for line in resp.iter_lines():
                if timeout is not None and time.time() - start_time > timeout:
                    raise TimeoutError(f"No response received on ntfy topic {poll_url} for ID {confirmation_id[:8]} within the expected timeframe.")
                    
                if line:
                    event = json.loads(line.decode('utf-8'))
                    if event.get("event") == "message":
                        message_payload = json.loads(event.get("message", "{}"))
                        if message_payload.get("id") == confirmation_id:
                            decision = message_payload.get("decision")
                            print(f"Received decision via ntfy: '{decision}' for ID {confirmation_id[:8]}")
                            return decision
        except requests.exceptions.ConnectionError as e:
            print(f"Polling ntfy failed due to ConnectionError for URL {poll_url}: {e}. Retrying...")
            time.sleep(5)
        except requests.exceptions.Timeout as e:
            # Ignore short read timeouts and continue the while loop to check total elapsed time.
            continue
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error polling ntfy response from {poll_url}: {e}")

if __name__ == '__main__':
    # Example usage (optional, for testing notification_handler.py directly)
    if NTFY_CONFIRM_TOPIC and NTFY_RESPONSE_TOPIC:
        print("Testing ntfy confirmation...")
        test_tweet = "This is a test tweet for ntfy confirmation."
        user_response = request_confirmation(test_tweet)
        if user_response == "approve":
            print("Test tweet APPROVED via ntfy.")
        elif user_response == "reject":
            print("Test tweet REJECTED via ntfy.")
        elif user_response == "regenerate":
            print("REGENERATE tweet request via ntfy.")
    else:
        print("Skipping ntfy test: NTFY_SERVER, NTFY_CONFIRM_TOPIC, or NTFY_RESPONSE_TOPIC not set. Set these environment variables to test.")
