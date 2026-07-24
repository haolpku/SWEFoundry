FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/workspace
COPY codebase/ /app/workspace/
COPY knowledge/ /app/knowledge/
RUN python -m compileall -q /app/workspace
CMD ["/bin/sh"]
