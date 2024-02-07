# Use the official Node.js image as the base image
FROM node:21-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the package.json and package-lock.json files to the working directory
COPY package*.json ./

# Install the app dependencies
RUN npm install

# Install the http-server package globally
RUN npm install -g http-server

# Copy the rest of the app source code to the working directory
COPY . .

# Build the Vue.js app for production
RUN npm run build

# Expose the container's port 8080
EXPOSE 8080

# Define the command to run the app when the container starts
# CMD [ "http-server", "-P", "http://localhost:8080?", "dist" ]

# Start the Vue.js app
CMD ["npm". "run", "dev"]