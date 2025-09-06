from flask import Flask, request
import logging
import hashlib
import os
import requests
from dotenv import load_dotenv
import time
from urllib.parse import quote

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION from environment variables ---
PAPERLESS_BASE_URL = os.getenv('PAPERLESS_API_URL')
PAPERLESS_API_TOKEN = os.getenv('PAPERLESS_API_TOKEN')
CUSTOM_FIELD_ID = int(os.getenv('PAPERLESS_CUSTOM_FIELD_ID', 1))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# --- Configuration for retry logic ---
MAX_RETRIES = 5
RETRY_DELAY = 3

# --- Environment variable validation ---
if not PAPERLESS_BASE_URL or not PAPERLESS_API_TOKEN:
    print("FEHLER: Die Umgebungsvariablen PAPERLESS_API_URL und PAPERLESS_API_TOKEN müssen gesetzt sein!")
    exit(1)

# --- Logging Setup ---
# Logs werden an stdout/stderr gesendet, um vom Container-Laufzeitsystem (z.B. Docker)
# verarbeitet zu werden. Es wird keine Log-Datei mehr geschrieben.
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# Gunicorn compatibility
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# --- Checksum Log File Setup ---
# Dieser Logger schreibt nur die Checksummen in eine separate Datei.
checksum_logger = logging.getLogger('checksum_logger')
checksum_logger.setLevel(logging.INFO)
# Verhindern, dass die Logs an den Root-Logger weitergegeben werden (damit sie nicht in der Konsole erscheinen)
checksum_logger.propagate = False

# Handler für die Checksummen-Datei
checksum_log_file = 'logs/checksums.log'
os.makedirs(os.path.dirname(checksum_log_file), exist_ok=True)
checksum_file_handler = logging.FileHandler(checksum_log_file)
# Einfaches Format: Zeitstempel wird manuell hinzugefügt, hier nur die Nachricht.
checksum_file_handler.setFormatter(logging.Formatter('%(message)s'))
checksum_logger.addHandler(checksum_file_handler)

@app.route('/webhook', methods=['POST'])
def checksum_webhook():
    if 'file' not in request.files:
        app.logger.warning("Webhook received but no file found in the request.")
        return "No file found in webhook.", 400

    webhook_file = request.files['file']
    
    # Step 1: Calculate SHA256 of the received file
    sha256_hash_webhook = hashlib.sha256()
    webhook_file.stream.seek(0)
    for chunk in iter(lambda: webhook_file.stream.read(8192), b''):
        sha256_hash_webhook.update(chunk)
    webhook_file_digest = sha256_hash_webhook.hexdigest()

    # Step 1b: Calculate MD5 of the received file
    md5_hash_webhook = hashlib.md5()
    webhook_file.stream.seek(0)
    for chunk in iter(lambda: webhook_file.stream.read(8192), b''):
        md5_hash_webhook.update(chunk)
    md5_file_digest = md5_hash_webhook.hexdigest()
    webhook_file.stream.seek(0)

    # Log to console
    app.logger.info(f"File: '{webhook_file.filename}', SHA256: {webhook_file_digest}, MD5: {md5_file_digest}")

    # Log to the special checksum file as requested
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    checksum_logger.info(f"{timestamp}, orig_name_sha256_md5,{webhook_file.filename},{webhook_file_digest},{md5_file_digest}")

    headers = {"Authorization": f"Token {PAPERLESS_API_TOKEN}"}
    
    # Step 2: Search for the document by filename
    encoded_filename = quote(webhook_file.filename)
    search_url = f"{PAPERLESS_BASE_URL}/api/documents/?original_filename__icontains={encoded_filename}"

    for attempt in range(MAX_RETRIES):
        try:
            app.logger.debug(f"Searching for document with filename '{webhook_file.filename}'... (Attempt {attempt + 1}/{MAX_RETRIES})")
            
            search_response = requests.get(search_url, headers=headers)
            search_response.raise_for_status()
            search_data = search_response.json()

            app.logger.debug(f"API search response: {search_data}")

            if search_data.get('count', 0) > 0:
                app.logger.debug(f"{search_data['count']} document(s) with matching name found. Verifying hashes.")

                for doc in search_data['results']:
                    document_id = doc['id']
                    app.logger.debug(f"Checking document with ID {document_id}...")

                    download_url = f"{PAPERLESS_BASE_URL}/api/documents/{document_id}/download/"
                    with requests.get(download_url, headers=headers, stream=True) as r:
                        r.raise_for_status()
                        sha256_hash_paperless = hashlib.sha256()
                        for chunk in r.iter_content(chunk_size=8192):
                            sha256_hash_paperless.update(chunk)
                        paperless_file_digest = sha256_hash_paperless.hexdigest()

                    app.logger.debug(f"SHA256 of Paperless file (ID {document_id}): {paperless_file_digest}")

                    if webhook_file_digest == paperless_file_digest:
                        app.logger.info(f"SUCCESS: Match found for '{webhook_file.filename}' (ID: {document_id}). Updating custom field.")
                        
                        patch_url = f"{PAPERLESS_BASE_URL}/api/documents/{document_id}/"
                        payload = {"custom_fields": [{"field": CUSTOM_FIELD_ID, "value": webhook_file_digest}]}
                        
                        patch_response = requests.patch(patch_url, json=payload, headers=headers)
                        patch_response.raise_for_status()
                        
                        return f"SHA256 stored in document {document_id}.", 200

                app.logger.warning(f"File '{webhook_file.filename}' found, but hash did not match. Waiting {RETRY_DELAY}s.")
                time.sleep(RETRY_DELAY)
            
            else: # count == 0
                app.logger.warning(f"Attempt {attempt + 1}: No document named '{webhook_file.filename}' found yet. Waiting {RETRY_DELAY}s.")
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error during API communication: {e}")
            response_text = e.response.text if e.response else 'N/A'
            app.logger.error(f"Response text: {response_text}")
            return "Error during API communication", 500

    app.logger.error(f"Could not find a matching document for '{webhook_file.filename}' after {MAX_RETRIES} attempts.")
    return "Matching document not found.", 404

if __name__ == '__main__':
    # Nur für lokales Debugging, im Docker wird Gunicorn verwendet.
    app.run(port=5000, debug=True)
