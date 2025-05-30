import os
import time
import requests
import json
import uuid

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh") # Added default
NTFY_CONFIRM_TOPIC = os.environ.get("NTFY_CONFIRM_TOPIC")
NTFY_RESPONSE_TOPIC = os.environ.get("NTFY_RESPONSE_TOPIC")

def request_confirmation(tweet_text: str) -> str | None:
    """
    Requests confirmation via ntfy push notification to a phone.
    Returns True if approved, False otherwise (rejected or timed out).
    """
    if not all([NTFY_SERVER, NTFY_CONFIRM_TOPIC, NTFY_RESPONSE_TOPIC]):
        print("Ntfy server/topic environment variables not set. Falling back to terminal confirmation.")
        user_input = input(f"Post tweet '{tweet_text[:70].replace('\n', ' ')}...'? (yes/no): ").strip().lower()
        return user_input in ['yes', 'y']

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
            },
            {
                "action": "http", "label": "Re-generate 🔁",
                "url": f"{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}", "method": "POST",
                "body": json.dumps({"id": confirmation_id, "decision": "regenerate"}),
                "headers": {"Content-Type": "application/json", "X-Title": f"Regenerate tweet {confirmation_id[:8]}"}, "clear": True,
            }
        ]
    }
    try:
        requests.post(base_ntfy_url, json=message_payload, timeout=10)
        print(f"Confirmation request sent to ntfy topic '{base_ntfy_url}/{NTFY_CONFIRM_TOPIC}'. Waiting for response on '{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}' for ID {confirmation_id[:8]}...")
    except requests.exceptions.RequestException as e:
        print(f"Error sending ntfy notification: {e}. Falling back to terminal confirmation.")
        user_input = input(f"Ntfy send failed. Post tweet '{tweet_text[:70].replace('\n', ' ')}...' anyway? (yes/no): ").strip().lower()
        return user_input in ['yes', 'y']

    poll_url = f"{base_ntfy_url}/{NTFY_RESPONSE_TOPIC}/json"
    try:
        resp = requests.get(poll_url, stream=True)
        approved = False
        for line in resp.iter_lines():
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
        print(f"Polling ntfy timed out for URL {poll_url}: {e}. Retrying...")
        time.sleep(5)
    except requests.exceptions.RequestException as e:
        print(f"Error polling ntfy response: {e}. Retrying in 10s.")
        time.sleep(10)

    return False

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
        print("Skipping ntfy test: NTFY_CONFIRM_TOPIC or NTFY_RESPONSE_TOPIC not set.")

