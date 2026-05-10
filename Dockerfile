# First, specify the base Docker image.
# You can see the Docker images from Apify at https://hub.docker.com/r/apify/.
FROM apify/actor-python:3.14

# Install browsers to a shared path accessible by ALL users (not root's home cache).
# This env var is inherited at runtime too, so Playwright always finds the browsers.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Copy requirements first (as root) for better layer caching
COPY requirements.txt ./

# Install Python deps and Playwright browsers as root into the shared path
RUN echo "Python version:" \
 && python --version \
 && echo "Installing Python dependencies:" \
 && pip install -r requirements.txt \
 && echo "Installing Playwright browser (Chromium) to shared path:" \
 && python -m playwright install --with-deps chromium \
 && echo "Granting read/execute permissions to all users:" \
 && chmod -R o+rx /ms-playwright \
 && echo "Done."

# Switch to non-root user for runtime security
USER myuser

# Copy the remaining source files
COPY --chown=myuser:myuser . ./

# Compile the Actor code
RUN python -m compileall -q my_actor/

# Launch the Actor
CMD ["python", "-m", "my_actor"]
