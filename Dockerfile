# ---- Stufe 1: Build ----
# Diese Stufe dient nur der Installation der Python-Abhängigkeiten.
# Wir wechseln zu Alpine Linux, das deutlich kleiner als 'slim' ist.
FROM python:3.13-alpine AS builder

# Setze Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installiere Build-Abhängigkeiten, falls Pakete kompiliert werden müssen (wegen musl libc).
# Diese werden im finalen Image nicht enthalten sein.
RUN apk add --no-cache build-base

WORKDIR /app

# Installiere die Abhängigkeiten. Dieser Layer wird gecached.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stufe 2: Final ----
# Dies ist die finale, optimierte Stufe. Wir starten wieder von einem sauberen Image.
FROM python:3.13-alpine

# Erstelle einen dedizierten, unprivilegierten Benutzer für die Anwendung.
# Die Syntax für Alpine ist anders.
RUN addgroup -S app && adduser -S -G app app

# Setze Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Kopiere die installierten Pakete und ausführbaren Dateien (wie gunicorn) aus der Build-Stufe.
# Die Pfade sind in Alpine-Images identisch.
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Kopiere den Anwendungscode.
COPY app.py .

# Setze den neuen Benutzer als Eigentümer für das gesamte App-Verzeichnis, damit die Anwendung Logs schreiben kann.
RUN chown -R app:app /app
# Wechsle zum unprivilegierten Benutzer.
USER app

# Gib den Port an, auf dem die Anwendung lauscht.
EXPOSE 8000

# Der Befehl, der beim Starten des Containers ausgeführt wird
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]