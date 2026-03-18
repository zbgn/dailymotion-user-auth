# Use the official Python base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install --upgrade pip
RUN pip install uv

# Copy the rest of the application code to the working directory
COPY . .

# Install dependencies from lock file
RUN uv sync --frozen --group test

# Expose the port on which the FastAPI app will run
EXPOSE 8000

# Start the FastAPI app
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
