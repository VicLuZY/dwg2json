from __future__ import annotations

import click

from .parser import Dwg2JsonParser


@click.command()
@click.argument("input_path", type=click.Path(exists=False))
@click.option("-o", "--output", "output_path", type=click.Path(), default=None)
@click.option("--xref-root", "xref_roots", multiple=True, type=click.Path())
@click.option("--indent", default=2, show_default=True, type=int)
def main(input_path: str, output_path: str | None, xref_roots: tuple[str, ...], indent: int) -> None:
    parser = Dwg2JsonParser(xref_search_roots=list(xref_roots))
    written = parser.parse_to_json_file(input_path, output_path=output_path, indent=indent)
    click.echo(written)


if __name__ == "__main__":
    main()
