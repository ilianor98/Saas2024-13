# Use the official Python image from the Docker Hub
FROM python:3.9

# Install SQLite3
RUN apt-get update && apt-get install -y sqlite3

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies globally
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Command to run the application
CMD ["python", "run.py"]
