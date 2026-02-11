# base image with Python 3.10
FROM python:3.10-slim

# set working directory
WORKDIR /app

# copy only dependency files first for caching
COPY requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy all remaining project files
COPY . .

# ensure uvicorn listens on the dynamic PORT
ENV PORT 8000

# expose for render
EXPOSE 8000

# start the app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
