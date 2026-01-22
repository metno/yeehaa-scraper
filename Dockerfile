# Copyright 2022 met.no. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

FROM registry.met.no/baseimg/ubuntu:24.04 


ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get -yy install --no-install-recommends \
    apt-utils python3 python3-dev python3-pip python3-setuptools python3-venv wget libatk1.0-0 libcairo2 libcups2 libfontconfig1 libgdk-pixbuf2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libxss1 fonts-liberation libnss3 lsb-release xdg-utils

RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install --upgrade pip

RUN pip install requests==2.32.3
RUN pip install tldextract==5.1.3
RUN pip install bs4==0.0.2
RUN pip install selenium==4.30.0
RUN pip install langdetect==1.0.9
RUN pip install webdriver_manager
RUN pip install pyotp
RUN pip install markdownify
RUN pip install python-dateutil

