"""Load the real per-quarter text files into one DuckDB database.

sub.txt, num.txt and pre.txt are read straight off disk with DuckDB's own
CSV reader (tab-delimited, no quoting) and filtered to the two forms this
project claims (10-Q, 10-K) before anything is persisted, since the raw
files also contain every other form (8-K, S-1, 20-F, ...) this project does
not touch.
"""

from __future__ import annotations

import pathlib

import duckdb

from featurex import config, download

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "featurex.duckdb"

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    adsh VARCHAR NOT NULL,
    cik BIGINT,
    name VARCHAR,
    form VARCHAR,
    period DATE,
    fy INTEGER,
    fp VARCHAR,
    filed DATE,
    accepted TIMESTAMP,
    quarter VARCHAR NOT NULL,
    PRIMARY KEY (adsh)
);

CREATE TABLE IF NOT EXISTS num (
    adsh VARCHAR NOT NULL,
    tag VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    ddate DATE,
    qtrs INTEGER,
    uom VARCHAR,
    segments VARCHAR,
    coreg VARCHAR,
    value DOUBLE
);

CREATE TABLE IF NOT EXISTS pre (
    adsh VARCHAR NOT NULL,
    report INTEGER,
    line INTEGER,
    stmt VARCHAR,
    inpth INTEGER,
    rfile VARCHAR,
    tag VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    plabel VARCHAR,
    negating INTEGER
);
"""


def build_database(quarters: list[str] | None = None, force: bool = False) -> duckdb.DuckDBPyConnection:
    quarters = quarters or config.QUARTERS
    if DB_PATH.exists() and not force:
        return duckdb.connect(str(DB_PATH))

    download.ensure_all_downloaded(quarters)

    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA)

    for quarter in quarters:
        qdir = download.quarter_dir(quarter)
        sub_path = str(qdir / "sub.txt").replace("\\", "/")
        num_path = str(qdir / "num.txt").replace("\\", "/")
        pre_path = str(qdir / "pre.txt").replace("\\", "/")

        con.execute(
            f"""
            INSERT INTO submissions
            SELECT adsh, cik, name, form,
                   strptime(CAST(period AS VARCHAR), '%Y%m%d')::DATE AS period,
                   fy, fp,
                   strptime(CAST(filed AS VARCHAR), '%Y%m%d')::DATE AS filed,
                   accepted::TIMESTAMP AS accepted,
                   '{quarter}' AS quarter
            FROM read_csv('{sub_path}', delim='\t', header=True, quote='"',
                           columns={{
                               'adsh':'VARCHAR','cik':'BIGINT','name':'VARCHAR','sic':'VARCHAR',
                               'countryba':'VARCHAR','stprba':'VARCHAR','cityba':'VARCHAR','zipba':'VARCHAR',
                               'bas1':'VARCHAR','bas2':'VARCHAR','baph':'VARCHAR',
                               'countryma':'VARCHAR','stprma':'VARCHAR','cityma':'VARCHAR','zipma':'VARCHAR',
                               'mas1':'VARCHAR','mas2':'VARCHAR','countryinc':'VARCHAR','stprinc':'VARCHAR',
                               'ein':'VARCHAR','former':'VARCHAR','changed':'VARCHAR','afs':'VARCHAR',
                               'wksi':'VARCHAR','fye':'VARCHAR','form':'VARCHAR','period':'VARCHAR',
                               'fy':'INTEGER','fp':'VARCHAR','filed':'VARCHAR','accepted':'VARCHAR',
                               'prevrpt':'VARCHAR','detail':'VARCHAR','instance':'VARCHAR',
                               'nciks':'VARCHAR','aciks':'VARCHAR'
                           }})
            WHERE form IN ('10-Q', '10-K')
            """
        )

        con.execute(
            f"""
            INSERT INTO num
            SELECT n.adsh, n.tag, n.version,
                   strptime(CAST(n.ddate AS VARCHAR), '%Y%m%d')::DATE AS ddate,
                   n.qtrs, n.uom, NULLIF(n.segments, '') AS segments,
                   NULLIF(n.coreg, '') AS coreg, n.value
            FROM read_csv('{num_path}', delim='\t', header=True, quote='"',
                           columns={{
                               'adsh':'VARCHAR','tag':'VARCHAR','version':'VARCHAR','ddate':'VARCHAR',
                               'qtrs':'INTEGER','uom':'VARCHAR','segments':'VARCHAR','coreg':'VARCHAR',
                               'value':'DOUBLE','footnote':'VARCHAR'
                           }}) AS n
            WHERE n.adsh IN (SELECT adsh FROM submissions WHERE quarter = '{quarter}')
            """
        )

        con.execute(
            f"""
            INSERT INTO pre
            SELECT p.adsh, p.report, p.line, p.stmt, p.inpth, p.rfile, p.tag, p.version,
                   p.plabel, p.negating
            FROM read_csv('{pre_path}', delim='\t', header=True, quote='"',
                           columns={{
                               'adsh':'VARCHAR','report':'INTEGER','line':'INTEGER','stmt':'VARCHAR',
                               'inpth':'INTEGER','rfile':'VARCHAR','tag':'VARCHAR','version':'VARCHAR',
                               'plabel':'VARCHAR','negating':'INTEGER'
                           }}) AS p
            WHERE p.adsh IN (SELECT adsh FROM submissions WHERE quarter = '{quarter}')
            """
        )

    con.execute("CREATE INDEX IF NOT EXISTS num_adsh_tag ON num(adsh, tag)")
    con.execute("CREATE INDEX IF NOT EXISTS pre_adsh ON pre(adsh)")
    return con


def connect() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        return build_database()
    return duckdb.connect(str(DB_PATH))
