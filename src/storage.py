"""OCI Object Storage helper for model/result upload and download."""

import os
import glob as globmod
import config as cfg
from src import logger

log = logger.get("storage")

OCI_NAMESPACE = os.environ.get("Q_OCI_NAMESPACE", "")
OCI_BUCKET = os.environ.get("Q_OCI_BUCKET", "qtradeBucket")

_client = None


def _get_client():
    global _client, OCI_NAMESPACE
    if _client is None:
        import oci
        config = oci.config.from_file()
        _client = oci.object_storage.ObjectStorageClient(config)
        if not OCI_NAMESPACE:
            OCI_NAMESPACE = _client.get_namespace().data
    return _client


def enabled() -> bool:
    return bool(os.environ.get("Q_OCI_NAMESPACE") or
                os.path.exists(os.path.expanduser("~/.oci/config")))


def upload_file(local_path: str, prefix: str, object_name: str = None):
    client = _get_client()
    object_name = prefix + (object_name or os.path.basename(local_path))
    with open(local_path, "rb") as f:
        client.put_object(OCI_NAMESPACE, OCI_BUCKET, object_name, f)
    log.debug(f"Uploaded {object_name} → {OCI_BUCKET}")


def download_file(object_name: str, local_path: str):
    client = _get_client()
    resp = client.get_object(OCI_NAMESPACE, OCI_BUCKET, object_name)
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    with open(local_path, "wb") as f:
        for chunk in resp.data.raw.stream(1024 * 1024):
            f.write(chunk)
    log.debug(f"Downloaded {object_name} → {local_path}")


def upload_models(models_dir: str = None):
    if not enabled():
        return
    models_dir = models_dir or os.path.join(cfg.DATA_DIR, "models")
    files = globmod.glob(os.path.join(models_dir, "*.pt"))
    for f in files:
        upload_file(f, "models/")
    log.info(f"Uploaded {len(files)} models to {OCI_BUCKET}/models/")


def upload_results(data_dir: str = None):
    if not enabled():
        return
    data_dir = data_dir or cfg.DATA_DIR
    for pattern in ["training_results*.csv"]:
        for f in globmod.glob(os.path.join(data_dir, pattern)):
            upload_file(f, "results/")
    log.info(f"Uploaded results to {OCI_BUCKET}/results/")


def download_models(models_dir: str = None):
    if not enabled():
        return
    client = _get_client()
    models_dir = models_dir or os.path.join(cfg.DATA_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    objects = client.list_objects(OCI_NAMESPACE, OCI_BUCKET, prefix="models/").data.objects
    count = 0
    for obj in objects:
        if obj.name.endswith(".pt"):
            local_name = obj.name.removeprefix("models/")
            download_file(obj.name, os.path.join(models_dir, local_name))
            count += 1
    log.info(f"Downloaded {count} models from {OCI_BUCKET}/models/")
