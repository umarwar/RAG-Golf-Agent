import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory

from config.settings import GolfAgentConfig


_config = GolfAgentConfig()
_bundle_name = "secure-connect-golfguiders-v.zip"

# Ensure Cassandra uses /tmp (works locally and in containers)
tempfile.tempdir = "/tmp"
os.environ["TMPDIR"] = "/tmp"


def _bundle_path() -> Path:
    """Return path to secure connect bundle copied into /tmp."""
    source = Path(__file__).resolve().parent.parent / _bundle_name
    target = Path("/tmp") / _bundle_name
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return target


@lru_cache(maxsize=1)
def get_session():
    """Create (or reuse) a Cassandra session."""
    if not _config.CASSANDRA_USERNAME or not _config.CASSANDRA_PASSWORD:
        raise ValueError("CASSANDRA credentials are required")

    cloud_config = {"secure_connect_bundle": str(_bundle_path())}
    auth_provider = PlainTextAuthProvider(
        username=_config.CASSANDRA_USERNAME,
        password=_config.CASSANDRA_PASSWORD,
    )

    cluster = Cluster(
        cloud=cloud_config,
        auth_provider=auth_provider,
        protocol_version=4,
        connect_timeout=10,
        control_connection_timeout=10,
    )
    print("✓ Cassandra connection established")
    session = cluster.connect("core")
    session.row_factory = dict_factory
    return session


def fetch_rows(query: str, params: List[Any]) -> List[Dict[str, Any]]:
    session = get_session()
    result = session.execute(query, params)
    return result.all()
