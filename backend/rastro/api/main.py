"""API do Rastro da Emenda. Endpoints de negócio entram na etapa 7 do roteiro."""

from fastapi import FastAPI

from rastro import __version__

app = FastAPI(
    title="Rastro da Emenda",
    version=__version__,
    description="Segue cada real da emenda parlamentar até o contrato no município.",
)


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok", "versao": __version__}
