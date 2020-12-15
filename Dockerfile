FROM python:3.8

RUN pip3 install pipenv

ENV PROJECT_DIR /usr/src/app

WORKDIR ${PROJECT_DIR}

COPY . .

RUN pipenv install --deploy --ignore-pipfile

EXPOSE 5000

CMD ["python", "run.py"]