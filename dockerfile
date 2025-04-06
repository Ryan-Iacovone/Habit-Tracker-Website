# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container at /app
COPY requirements.txt .

# Could use git clone here to keep my project up to date. 
# RUN git clone https://github.com/streamlit/streamlit-example.git 

# Install the dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to /app
COPY . .

# Expose the port Streamlit uses
EXPOSE 8080

# Command left empty because it's handled in the docker-compose file
CMD []