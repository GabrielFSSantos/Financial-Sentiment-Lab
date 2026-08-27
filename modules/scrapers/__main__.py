"""CLI de coleta multiportal."""

import sys

if len(sys.argv) > 1 and sys.argv[1] == "report":
    from modules.scrapers.report import main as report_main

    raise SystemExit(report_main(sys.argv[2:]))

if len(sys.argv) > 1 and sys.argv[1] == "debug-search":
    from modules.scrapers.cli.debug_search import main as debug_search_main

    raise SystemExit(debug_search_main(sys.argv[2:]))

if len(sys.argv) > 1 and sys.argv[1] == "build-strict":
    from modules.scrapers.cli.build_strict import main as build_strict_main

    raise SystemExit(build_strict_main(sys.argv[2:]))

if len(sys.argv) > 1 and sys.argv[1] == "filter-corpus":
    from modules.scrapers.cli.filter_corpus import main as filter_corpus_main

    raise SystemExit(filter_corpus_main(sys.argv[2:]))

from modules.scrapers.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
