from apputils import health_check, lifespan, validate
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(lifespan=lifespan)
app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/validate", validate, methods=["POST"])


@app.get("/", deprecated=True)
async def redirect_to_docs():
    return RedirectResponse(url="/docs", status_code=308)


# Run using the following command: fastapi run
