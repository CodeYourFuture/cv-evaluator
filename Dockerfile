FROM python:3.12-slim
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
COPY ./build_assets.py /code/build_assets.py
RUN python build_assets.py --static-dir app/static
CMD ["uvicorn", "app.main:app", "--proxy-headers", "--port", "8000", "--host", "0.0.0.0"]
