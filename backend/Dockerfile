# Use the official Python base image
FROM python:3.12-slim
ARG REQUIREMENTS=test

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements/${REQUIREMENTS}.txt ./requirements.txt

# Install the dependencies
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Expose the port on which the FastAPI app will run
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
