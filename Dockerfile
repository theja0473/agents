# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application directory into the container at /app
COPY github_pr_reviewer /app/github_pr_reviewer

# Make port 7860 available to the world outside this container
EXPOSE 7860

# Define environment variable
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Run reviewer.py when the container launches
CMD ["python", "github_pr_reviewer/reviewer.py"]
