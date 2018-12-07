# w3af.org
# https://github.com/andresriancho/w3af/tree/master/extras

FROM ubuntu:16.04

# Initial setup
RUN mkdir /home/w3af

WORKDIR /home/w3af

# TERM=linux squashes errors about "Falling back to ..."
# during package installation
ENV \
 HOME=/home/w3af \
 LANG=en_US.UTF-8 \
 LANGUAGE=en_US:en \
 LOGNAME=w3af \
 TERM=linux

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections \
 && apt-get update \
 && apt-get upgrade -y \
 && apt-get dist-upgrade -y \
 # Install basic and GUI requirements
 # python-lxml because it doesn't compile correctly from pip
 && apt-get install -y \
      build-essential \
      curl \
      libxslt1-dev \
      libxml2-dev \
      libsqlite3-dev \
      libyaml-dev \
      openssh-server \
      python-dev \
      git \
      python-lxml \
      wget \
      libssl-dev \
      xdot \
      python-gtk2 \
      python-gtksourceview2 \
      python-pip \
      python-setuptools \
      ubuntu-artwork \
      dmz-cursor-theme \
      ca-certificates \
      libffi-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# TODO - actually use the w3af user instead of running everything as root
# Get ssh package ready
RUN useradd w3af \
 && mkdir /var/run/sshd \
 && echo 'root:w3af' | chpasswd \
 && mkdir /home/w3af/.ssh/ \
 && echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDjXxcHjyVkwHT+dSYwS3vxhQxZAit6uZAFhuzA/dQ2vFu6jmPk1ewMGIYVO5D7xV3fo7/RXeCARzqHl6drw18gaxDoBG3ERI6LxVspIQYjDt5Vsqd1Lv++Jzyp/wkXDdAdioLTJyOerw7SOmznxqDj1QMPCQni4yhrE+pYH4XKxNx5SwxZTPgQWnQS7dasY23bv55OPgztI6KJzZidMEzzJVKBXHy1Ru/jjhmWBghiXYU5RBDLDYyT8gAoWedYgzVDmMZelLR6Y6ggNLOtMGiGYfPWDUz9Z6iDAUsOQBtCJy8Sj8RwSQNpmOgSzBanqnhed14hLwdYhnKWcPNMry71 w3af@w3af-docker.org' > /home/w3af/.ssh/w3af-docker.pub \
 && mkdir -p /root/.ssh/ \
 && cat /home/w3af/.ssh/w3af-docker.pub >> /root/.ssh/authorized_keys

RUN apt-get update \
 && apt-get install -y \
      libjavascriptcoregtk-1.0-0 \
      libpango1.0-0 \
      libwebkitgtk-1.0-0 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl -Lo /tmp/python-support_1.0.15_all.deb http://ftp.br.debian.org/debian/pool/main/p/python-support/python-support_1.0.15_all.deb \
 && dpkg -i /tmp/python-support_1.0.15_all.deb \
 && curl -Lo /tmp/python-webkit_1.1.8-3_amd64.deb http://ftp.br.debian.org/debian/pool/main/p/pywebkitgtk/python-webkit_1.1.8-3_amd64.deb \
 && dpkg -i /tmp/python-webkit_1.1.8-3_amd64.deb

RUN apt-get update \
 && apt-get install -y \
      nodejs \
      npm \
 && cd /usr/bin \
 && ln -sf nodejs node \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install w3af
COPY . /home/w3af/w3af

WORKDIR /home/w3af/w3af

ENV LC_ALL=C

# w3af_console fails but craete /tmp/w3af_dependency_install.sh
# sed changes the install script to add the -y and not require input
RUN pip install --upgrade pip \
 &&  ./w3af_console \
 ; sed 's/sudo //g' -i /tmp/w3af_dependency_install.sh \
 && sed 's/apt-get/apt-get -y/g' -i /tmp/w3af_dependency_install.sh \
 && sed 's/pip install/pip install --upgrade/g' -i /tmp/w3af_dependency_install.sh \
 && /tmp/w3af_dependency_install.sh \
 && ./w3af_gui \
 ; sed 's/sudo //g' -i /tmp/w3af_dependency_install.sh \
 && sed 's/apt-get/apt-get -y/g' -i /tmp/w3af_dependency_install.sh \
 && sed 's/pip install/pip install --upgrade/g' -i /tmp/w3af_dependency_install.sh \
 && /tmp/w3af_dependency_install.sh \
 # Cleanup to make the image smaller
 && rm /tmp/w3af_dependency_install.sh \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && rm -rf /tmp/pip-build-root

# Compile the py files into pyc in order to speed-up w3af's start
RUN python -m compileall -q .

# try to compile everything into single file binaries
# intention is to provide a solution to the issues installing in the latest
# kali releases (not a perfect solution right now)
RUN pip install pyinstaller \
 && pyinstaller --onefile w3af_api \
 && pyinstaller --onefile w3af_console \
 && pyinstaller --onefile w3af_gui

EXPOSE 22 44444

CMD ["/usr/sbin/sshd", "-D"]
