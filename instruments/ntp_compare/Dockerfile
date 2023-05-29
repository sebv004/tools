FROM python
RUN apt-get update
RUN apt-get upgrade -y


ADD . /application
WORKDIR /application
RUN	pip install -r requirements.txt
EXPOSE 5000
VOLUME /application

CMD uwsgi --http :5000  --manage-script-name --mount /myapplication=ntp_compare:app --enable-threads --processes 5 --log-master