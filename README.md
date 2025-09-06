# PaperSum

A simple and robust webhook service designed to integrate with [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx). It receives a file, calculates its SHA256 hash, finds the corresponding document in Paperless by its original filename, and stores the hash in a designated custom field.

This is particularly useful for creating an immutable link or verification mechanism between an external system and a document stored in Paperless.

## 🎯 Features

- **Webhook Endpoint**: Listens for `POST` requests with a file payload.
- **Hashing**: Calculates SHA256 and MD5 hashes of the incoming file.
- **Paperless-ngx Integration**: Communicates with the Paperless-ngx API to find documents and update them.
- **Retry Logic**: Intelligently retries searching for the document in Paperless, accounting for potential processing delays.
- **Integrity Check**: Verifies that the file received via webhook matches the file stored in Paperless by comparing their SHA256 hashes before updating.
- **Configurable**: All settings are managed via environment variables.
- **Checksum Logging**: Maintains a separate, clean log file (`logs/checksums.log`) of all processed files and their hashes.
- **Production-Ready**: Built with a secure, multi-stage Dockerfile using a non-root user.

## 📝 Note on Compliance (Disclaimer)

This tool generates a cryptographic hash (SHA256) of a file and stores it within Paperless-ngx. This process creates an immutable link between the source file and the digital document, enhancing traceability and integrity.

**Relevance for Compliance (e.g., German GoBD):** When configured correctly, including the proper setup of permissions within Paperless-ngx, this tool **is intended to support** compliance with regulatory requirements for digital record-keeping, such as the **German GoBD** (*Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen und Unterlagen in elektronischer Form sowie zum Datenzugriff*).

**Disclaimer:** The author is not a legal expert, and this information does not constitute legal advice. Achieving full compliance depends on your entire system architecture and operational processes. This tool is provided as a technical aid only. For a legally binding assessment, please consult a qualified professional, such as a tax advisor or a lawyer specializing in compliance.

## ⚙️ Configuration

The application is configured using environment variables. The method for setting them depends on how you run the service (Docker Compose vs. local development).

### Environment Variables

| Variable                    | Description                                                                                             | Default | Required |
| --------------------------- | ------------------------------------------------------------------------------------------------------- | ------- | -------- |
| `PAPERLESS_API_URL`         | The base URL of your Paperless-ngx instance (e.g., `http://192.168.1.10:8000`).                          | `None`  | **Yes**  |
| `PAPERLESS_API_TOKEN`       | Your Paperless-ngx API token. You can create one in the Paperless admin settings.                       | `None`  | **Yes**  |
| `PAPERLESS_CUSTOM_FIELD_ID` | The ID of the custom field in Paperless where the SHA256 hash will be stored.                           | `1`     | No       |
| `LOG_LEVEL`                 | The logging level for the console output. Can be `DEBUG`, `INFO`, `WARNING`, `ERROR`.                   | `INFO`  | No       |

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.13+ (for local development)
- A running Paperless-ngx instance.
- A custom field created in Paperless-ngx to store the hash.

### 1. Docker Compose (Recommended)

This is the easiest and recommended way to run the service.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url> && cd papersum
    ```

2.  **Create a `docker-compose.yml` file** in the project root and add your configuration directly into the `environment` section.

    ```yaml
    version: "3.7"

    services:
      papersum:
        build: .
        container_name: papersum
        restart: unless-stopped
        ports:
          - "8000:8000"
        volumes:
          # Mount logs to persist checksum log file
          - ./logs:/app/logs
        environment:
          - PAPERLESS_API_URL=http://your-paperless-instance.com
          - PAPERLESS_API_TOKEN=your_secret_api_token
          - PAPERLESS_CUSTOM_FIELD_ID=1
          - LOG_LEVEL=INFO
    ```

4.  **Start the service:**
    ```bash
    docker-compose up --build -d
    ```
The service will be available at `http://localhost:8000`.

### 2. Local Development

1.  **Clone the repository** and navigate into the directory.

2.  **Create a `.env` file** for your local configuration. You can copy the example file to get started. This file is ignored by Git and should not be committed.
    ```bash
    cp .env.example .env
    ```
    Then, edit `.env` with your values.

3.  **Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the application:**
    The app will start in debug mode on port 5000.
    ```bash
    python app.py
    ```

## 🔧 Webhook Usage

To use the service, send a `POST` request to the `/webhook` endpoint with a `multipart/form-data` payload. The file must be included in a form field named `file`.

Example using `curl`:
```bash
curl -X POST http://localhost:8000/webhook -F "file=@/path/to/your/document.pdf"
```

## 🐳 Dockerfile Explained

The `Dockerfile` uses a **multi-stage build** to create a small and secure final image.

1.  **`builder` stage**: This stage uses a full Python image with build tools (`build-base`) to install the Python dependencies from `requirements.txt`. This keeps build-time dependencies out of the final image.

2.  **Final stage**: This stage starts from a clean, lightweight `python:3.13-alpine` base. It creates a dedicated, non-root user (`app`) for running the application. Only the installed Python packages and the application code (`app.py`) are copied from the `builder` stage. This approach significantly reduces the image size and improves security by adhering to the principle of least privilege.

## 🤝 Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and submit a pull request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
