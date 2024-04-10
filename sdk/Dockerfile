FROM python:3.11-alpine

RUN apk add binutils
WORKDIR /app/python
COPY ./* /app/python

CMD ./install.sh
