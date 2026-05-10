# First, specify the base Docker image.
# You can see the Docker images from Apify at https://hub.docker.com/r/apify/.
# You can also use any other image from Docker Hub.
FROM apify/actor-python:3.14

# Copy requirements.txt as root so we can install system-level deps
COPY requirements.txt ./

# Install Python packages and Playwright browsers (must run as root for --with-deps)
RUN echo "Python version:" \
 && python --version \
 && echo "Pip version:" \
 && pip --version \
 && echo "Installing dependencies:" \
 && pip install -r requirements.txt \
 && echo "Installing Playwright browser (Chromium) with system dependencies:" \
 && python -m playwright install --with-deps chromium \
 && echo "All installed Python packages:" \
 && pip freeze

# Switch to non-root user for runtime security
USER myuser

# Copy the remaining source files
COPY --chown=myuser:myuser . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python -m compileall -q my_actor/

# Specify how to launch the source code of your Actor.
CMD ["python", "-m", "my_actor"]
