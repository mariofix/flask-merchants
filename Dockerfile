# Use the official image as a parent image
ARG PYTHON_VERSION=3.9-slim
FROM python:${PYTHON_VERSION}

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir .[dev]

# Make port 5000 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV FLASK_APP=app.py

# Run app.py when the container launches
CMD ["flask", "run", "-p", "80", "--reload"]
