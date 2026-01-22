FROM ubuntu:24.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    unzip \
    python3 \
    python3-pip \
    python3.12-venv\
    curl\
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver for Chrome 115+
# Using the new Chrome for Testing endpoints
RUN CHROME_MAJOR_VERSION=$(google-chrome --version | sed -E 's/.* ([0-9]+)(\.[0-9]+){3}.*/\1/') \
    && echo "Chrome major version: $CHROME_MAJOR_VERSION" \
    && CHROMEDRIVER_VERSION=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR_VERSION}") \
    && echo "ChromeDriver version: $CHROMEDRIVER_VERSION" \
    && wget -q -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip -j /tmp/chromedriver-linux64.zip chromedriver-linux64/chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver-linux64.zip \
    && chmod +x /usr/local/bin/chromedriver \
    && chromedriver --version

# Install Selenium for testing
#RUN pip3 install selenium --break-system-packages

ARG SCRAPER_USERNAME
ARG SCRAPER_PASSWORD
ARG SCRAPER_TOTP_SECRET

ENV SCRAPER_USERNAME=$SCRAPER_USERNAME
ENV SCRAPER_PASSWORD=$SCRAPER_PASSWORD
ENV SCRAPER_TOTP_SECRET=$SCRAPER_TOTP_SECRET

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:/app:$PATH"

RUN python3 -m pip install --upgrade pip

#RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt .
COPY scraper_config.json .
COPY yeehaa_scraper.py .
RUN pip install -r requirements.txt


# Set display port to avoid crash
ENV DISPLAY=:99

CMD ["/bin/bash"]