from ..kernel_tables import AnalysisError
from .insight import accounting as accounting
from .insight import graphs as graphs
from .interface import app, console
from .projection import benchmark as benchmark
from .projection import changes as changes
from .projection import prose as prose
from .quality import checking as checking
from .quality import contextual as contextual
from .quality import showcase as showcase


def main() -> None:
    """Report expected source-analysis failures without hiding programming errors."""
    try:
        app()
    except AnalysisError as error:
        console.print(f"Analysis failed: {error}", markup=False)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
