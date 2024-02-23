FROM python
WORKDIR /main
COPY . /main
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
