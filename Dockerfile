FROM python:3.6

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

COPY . /srv/web
RUN chmod 755 /srv/web/docker-entrypoint.sh
RUN mkdir /srv/logs

WORKDIR /srv/web
ENTRYPOINT ["/srv/web/docker-entrypoint.sh"]
CMD ["manage.py"]
