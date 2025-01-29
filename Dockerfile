# Use the official image as a parent image
ARG PYTHON_VERSION=3.9-slim
FROM python:${PYTHON_VERSION}

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir .[dev,deploy]

# Make port 5000 available to the world outside this container
EXPOSE 80

# Run app.py when the container launches
CMD ["gunicorn", "-w", "4", "-b","0.0.0.0:80", "--forwarded-allow-ips=*", "--access-logfile=-","app:app"]
