FROM python:3.12-slim
COPY oracle/routekit_oracle.py /usr/local/bin/routekit-oracle
RUN chmod 0555 /usr/local/bin/routekit-oracle
WORKDIR /app/workspace
COPY codebase/ /app/workspace/
