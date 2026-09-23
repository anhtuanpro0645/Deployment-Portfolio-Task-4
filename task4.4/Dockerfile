# ---- Task 4.4: BMI Calculator CLI (non-web, run-to-completion) ----
# Alpine base: the tool only uses the Python standard library, so no
# pip packages or build tools are needed and the image stays very small.
FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    HISTORY_FILE=/data/bmi_history.log

# Non-root user for security.
RUN adduser -D -u 10001 appuser

WORKDIR /app
COPY --chown=appuser:appuser bmi_tool.py .

# /data holds the input CSV, report and history - mount a host folder or volume here.
RUN mkdir /data && chown appuser:appuser /data
VOLUME ["/data"]

USER appuser

# ENTRYPOINT fixes the program; CMD gives default arguments (batch mode)
# that can be overridden on `docker run`.
ENTRYPOINT ["python", "/app/bmi_tool.py"]
CMD ["--input", "/data/people.csv", "--output", "/data/output/bmi_report.txt"]