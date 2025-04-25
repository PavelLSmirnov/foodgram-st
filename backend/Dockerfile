FROM python:3.13.3-alpine3.21

WORKDIR /backend

COPY . .

RUN pip install -r requirements.txt
RUN python manage.py collectstatic

RUN chmod +x ./start-docker.sh

CMD ["./start-docker.sh"]
