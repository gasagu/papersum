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

[!Docker Hub](https://hub.docker.com/r/gasagu/papersum)

The easiest way to run this service is by using the pre-built Docker image from Docker Hub. See the Docker Compose section for details.

## 📝 Note on Compliance (Disclaimer)

This tool generates a cryptographic hash (SHA256) of a file and stores it within Paperless-ngx. This process creates an immutable link between the source file and the digital document, enhancing traceability and integrity.

**Relevance for Compliance (e.g., German GoBD):** When configured correctly, including the proper setup of permissions within Paperless-ngx, this tool **is intended to support** compliance with regulatory requirements for digital record-keeping, such as the **German GoBD** (*Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen und Unterlagen in elektronischer Form sowie zum Datenzugriff*).

**Disclaimer:** The author is not a legal expert, and this information does not constitute legal advice. Achieving full compliance depends on your entire system architecture and operational processes. This tool is provided as a technical aid only. For a legally binding assessment, please consult a qualified professional, such as a tax advisor or a lawyer specializing in compliance.

## 🔐 Permissions and Workflow for Compliance

To create a robust and compliant workflow (e.g., for GoBD in Germany), it's crucial to configure permissions within Paperless-ngx correctly. The goal is to ensure that once a document's hash is written by this service, it cannot be altered by regular users, thus preserving the document's integrity.

This setup involves two types of users: a regular user and a dedicated API user.

### 1. Regular User Permissions

Your day-to-day users should have restricted permissions to prevent accidental or intentional modification of the integrity hash.

-   Go to `Settings -> Users & Groups` in Paperless-ngx.
-   Select the group your regular users belong to.
-   Under `Permissions`, ensure that the permissions for `delete_document` are **NOT** granted.
-   Under `Permissions`, ensure that the permissions for `change_document` and `delete_document` are **NOT** granted. This is the key step to making the records immutable for regular users.
-   Users in this group will be able to view documents but will not be able to edit metadata (including the hash) or delete the files.

### 2. Dedicated API User

Create a new, separate user account solely for the `papersum` service.

-   Go to `Settings -> Users & Groups` and create a new user (e.g., `papersum_api_user`).
-   Grant this user the following specific permissions:
    -   `view_document`: To find the document and download it for hash verification.
    -   `change_document`: To write the SHA256 hash into the custom field.
-   Create an API token for this user.
-   Use this user's API token for the `PAPERLESS_API_TOKEN` environment variable.

### 3. Paperless-ngx Workflow for Permissions

To ensure that documents are immediately accessible to the correct users after being added, you should create a workflow within Paperless-ngx.

-   Go to `Settings -> Workflows`.
-   Create a new workflow.
-   **Trigger**: Set the trigger to `Consumption finished`.
-   **Actions**: Add an action of type `Set permissions`.
-   In the action's settings, under `Set view permissions for`, select the user group that contains your regular users.
-   This workflow will automatically make every new document readable for all members of that group right after it has been processed by Paperless.

### Resulting Workflow

1.  A document is consumed by Paperless-ngx.
2.  A **Paperless-ngx workflow** triggers automatically, granting `view` permissions to the regular user group. The document is now visible to them.
3.  A post-consumption webhook triggers the `papersum` service.
4.  `papersum`, authenticated as the powerful `papersum_api_user`, finds the document, verifies its content by comparing hashes, and writes the definitive SHA256 hash to the custom field.
5.  Regular users can view the document and its immutable hash but cannot change or delete it, as their group lacks the necessary `change_document` and `delete_document` permissions.

This complete process ensures document integrity and accessibility are handled automatically and securely.

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
- A running Paperless-ngx instance.
- A custom field created in Paperless-ngx to store the hash.

### 1. Docker Compose (Recommended)

This is the easiest way to run the service, as it doesn't require cloning the source code.

1.  **Create a directory** for your configuration and a `logs` subdirectory.
    ```bash
    mkdir papersum-service && cd papersum-service
    mkdir logs
    ```

2.  **Create a `docker-compose.yml` file** inside the `papersum-service` directory with the following content. Replace the environment variables with your actual Paperless-ngx details.

    ```yaml
    version: "3.7"

    services:
      papersum:
        image: gasagu/papersum:1.0 # You can also use 'latest' for the newest version
        container_name: papersum
        restart: unless-stopped
        ports:
          - "8000:8000"
        volumes:
          # Mount logs to persist the checksum log file on your host machine
          - ./logs:/app/logs
        environment:
          - PAPERLESS_API_URL=http://your-paperless-instance.com
          - PAPERLESS_API_TOKEN=your_secret_api_token
          - PAPERLESS_CUSTOM_FIELD_ID=1
          - LOG_LEVEL=INFO
    ```

3.  **Start the service:**
    Docker Compose will automatically pull the image from Docker Hub.
    ```bash
    docker-compose up -d
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

## 🤝 Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and submit a pull request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
