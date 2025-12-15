from __future__ import annotations

import json
from pathlib import Path
import typer
from rich import print

from qualityfoundry.models.schemas import RequirementInput, ExecutionRequest, Action, ActionType, Locator
from qualityfoundry.services.generation.generator import generate_bundle
from qualityfoundry.services.execution.executor import execute

app = typer.Typer(add_completion=False, help="QualityFoundry CLI")

@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Run FastAPI server."""
    import uvicorn
    uvicorn.run("qualityfoundry.main:app", host=host, port=port, reload=True)

@app.command()
def generate(
    title: str = typer.Option(..., help="Requirement title"),
    text: str = typer.Option(..., help="Requirement text"),
    out: Path = typer.Option(Path("./bundle.json"), help="Output JSON file"),
):
    """Generate a structured case bundle (MVP deterministic generator)."""
    bundle = generate_bundle(RequirementInput(title=title, text=text))
    out.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"[green]Wrote[/green] {out}")

@app.command()
def run(
    url: str = typer.Option("https://example.com", help="Target URL"),
    headless: bool = typer.Option(True, help="Headless mode"),
):
    """Run a minimal example against a URL (DSL -> Playwright)."""
    req = ExecutionRequest(
        base_url=url,
        headless=headless,
        actions=[
            Action(type=ActionType.GOTO, url=url),
            Action(type=ActionType.ASSERT_VISIBLE, locator=Locator(strategy="text", value="Example Domain", exact=False)),
        ],
    )
    result = execute(req)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    app()
