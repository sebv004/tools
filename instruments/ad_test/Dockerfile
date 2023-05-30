FROM python
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y \
    python3-dev libldap2-dev libssl-dev libsasl2-dev openssl iputils-ping

ADD . /application
WORKDIR /application
RUN	pip install -r requirements.txt
EXPOSE 5000
VOLUME /application

CMD uwsgi --http :5000  --manage-script-name --mount /myapplication=test_ad:app --enable-threads --processes 5 --log-master