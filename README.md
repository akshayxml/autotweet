# AutoTweet

AutoTweet is a Python application that leverages the Llama 3 language model to generate technical tweets on various topics. It integrates with `ntfy.sh` for a push notification-based confirmation workflow before posting to X (formerly Twitter). 

## Table of Contents

- [Features](#features)
- [How it Works](#how-it-works)
- [Setup](#setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Running as a Systemd Service (Linux)](#running-as-a-systemd-service-linux)
- [Contributing](#contributing)

## Features

*   **Automated Tweet Generation:** Uses the `meta-llama/Meta-Llama-3-8B-Instruct` model to create concise technical tweets.
*   **X Integration:** Posts approved tweets directly to your X account.
*   **Notification-based Confirmation:**
    *   Sends a push notification via a self-hosted or public `ntfy.sh` server to your device.
    *   Allows you to "Approve ✅" or "Discard ❌" the tweet directly from the notification.
*   **Direct Posting Option:** A command-line argument (`--force-post`) allows bypassing the confirmation step for direct posting
*   **Configurable Topics:** Easily customize the list of topics for tweet generation.
*   **Quantization Support:** Supports 4-bit quantization using `bitsandbytes` to reduce memory usage on both CPU and GPU.

## How it Works

1.  **Model Loading:** The Llama 3 model and tokenizer are loaded from Hugging Face.
2.  **Topic Selection:** A random topic is chosen from a predefined list.
3.  **Tweet Generation:** A prompt is constructed, and the Llama 3 model generates a short technical tweet (under 280 characters) about the selected topic.
4.  **Confirmation Request:** Unless `--force-post` is used, a notification with action buttons is sent to your configured `ntfy.sh` topic. The script then listens on the response topic for your decision. If `ntfy.sh` environment variables are not correctly set, the script will raise an error.
5.  **Action Based on Confirmation:**
    *   **Approve:** The tweet is posted to X.
    *   **Discard:** The tweet is not posted.
6.  **Termination:** After sending the notification and receiving a response (or timing out), the script exits. It does not loop internally.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/akshayxml/autotweet.git
    cd autotweet
    ```

2.  **Install Dependencies:**
    Make sure you have Python 3.x installed.
    It's highly recommended to create and activate a virtual environment first:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
    Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    # For CUDA support with PyTorch, ensure your PyTorch installation matches your CUDA version.
    # See: https://pytorch.org/get-started/locally/
    ```

3.  **Hugging Face Login/Token:**
    To download and use the Llama 3 model, you need to:
    *   Accept the Llama 3 license on its Hugging Face model card.
    *   Log in via the Hugging Face CLI:
        ```bash
        huggingface-cli login
        ```
    *   Alternatively, you can set the `HF_TOKEN` environment variable with your Hugging Face access token.

4.  **Environment Variables:**
    Create a `.env` file in the project root by copying the provided `.env.example` file (`cp .env.example .env`) and then fill in your actual values. Alternatively, you can set these environment variables directly in your system.


    *   **X API Credentials (Required):**
        ```
        X_CONSUMER_KEY="your_consumer_key"
        X_CONSUMER_SECRET="your_consumer_secret"
        X_ACCESS_TOKEN="your_access_token"
        X_ACCESS_TOKEN_SECRET="your_access_token_secret"
        X_BEARER_TOKEN="your_bearer_token"
        ```

    *   **ntfy.sh Configuration (Required, unless using `--force-post`):**
        ```
        NTFY_SERVER="https://ntfy.sh" # Optional, defaults to public ntfy.sh. Use your own if self-hosting.
        NTFY_CONFIRM_TOPIC="your_unique_confirm_topic_name" # e.g., autotweet_confirm_myuser
        NTFY_RESPONSE_TOPIC="your_unique_response_topic_name" # e.g., autotweet_response_myuser
        ```
        *Note: Ensure `NTFY_CONFIRM_TOPIC` and `NTFY_RESPONSE_TOPIC` are unique and private to you if using the public `ntfy.sh` server.*

    *   **Hugging Face Token (Optional, if not using `huggingface-cli login`):**
        ```
        HF_TOKEN="your_hugging_face_read_token"
        ```

## Usage

1.  Ensure all prerequisites and environment variables are set up.
2.  Run the main script: 
    * **With ntfy.sh confirmation (default):**
        Make sure your `ntfy.sh` environment variables are set.
        ```bash
        python main.py
        ```
    *   **To skip confirmation and post directly:**
        ```bash
        python main.py --force-post
        ```
3.  The script will start generating tweets.
4.  If not using `--force-post`, subscribe to your `NTFY_CONFIRM_TOPIC` on your phone/device using the ntfy app or web client. You will receive notifications to approve, reject, or regenerate tweets.

## Configuration

You can modify the following in `main.py`:

*   `LLAMA3_MODEL_NAME`: Change the Llama 3 model variant if needed (ensure compatibility).
*   `TWEET_TIMEGAP_SECS`: Adjust the time interval (in seconds) between tweet generation attempts. Default is 12 hours.
    ```python
    TWEET_TIMEGAP_SECS = 60 * 60 * 12 # 12 hours
    ```
*   `topics`: Add or remove topics for tweet generation.
    ```python
    topics = [
        "kubernetes", "docker", "c++", "golang", "java", "nodejs", "redis",
        "python", "system design", "data structures and algorithms",
        "operating system", "computer networking", "databases", "kafka", "javascript"
    ]
    ```

## Dependencies

All Python dependencies are listed in `requirements.txt`. The main dependencies include:
*   `transformers`: For interacting with Hugging Face models.
*   `torch`: The deep learning framework used by the model.
*   `tweepy`: For interacting with the X API.
*   `requests`: For making HTTP requests (e.g., to ntfy.sh).
*   `python-dotenv`: For managing environment variables from a `.env` file.

## Running with Systemd (Linux)

To run AutoTweet automatically every day, you can set it up with a systemd service and timer.

1.  **Create the Service and Timer files:**

    Create `autotweet.service` and `autotweet.timer` files (templates are provided in the repository) and copy them to `/etc/systemd/system/`.

    **autotweet.service**
    Make sure to adjust `User`, `WorkingDirectory`, and `ExecStart` paths to match your setup.
    ```ini
    [Unit]
    Description=Run AutoTweet once
    After=network.target

    [Service]
    Type=oneshot
    User=your_username
    WorkingDirectory=/path/to/your/autotweet_project
    ExecStart=/path/to/your/autotweet_project/venv/bin/python3 /path/to/your/autotweet_project/main.py
    ```

    **autotweet.timer**
    This configures the script to run daily at 10:00 AM.
    ```ini
    [Unit]
    Description=Run AutoTweet daily

    [Timer]
    OnCalendar=*-*-* 10:00:00
    Persistent=true

    [Install]
    WantedBy=timers.target
    ```

2.  **Enable and start the timer:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now autotweet.timer
    ```

3.  **Check the status:**

    You can check the status of the timer using:

    ```bash
    sudo systemctl status autotweet.timer
    ```

    And check when it was last run and when it will run next:
    ```bash
    systemctl list-timers --all | grep autotweet
    ```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.