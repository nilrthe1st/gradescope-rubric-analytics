from pathlib import Path
import sys

from streamlit.web import cli as stcli


def main() -> None:
    """Launch Streamlit with app/app.py via `python -m app`."""
    script = Path(__file__).resolve().parent / "app.py"
    sys.argv = ["streamlit", "run", str(script)]
    stcli.main()


if __name__ == "__main__":
    main()
