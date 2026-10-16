import base64, os, tempfile

# Configure the service before it is imported (the DB engine is created at import time).
_tmp = tempfile.mkdtemp()
os.environ["CERT_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CERT_LOCAL_MASTER_KEY_BASE64"] = base64.b64encode(os.urandom(32)).decode()
os.environ["CERT_API_KEY"] = "test-key"
os.environ["CERT_KMS_MODE"] = "local"
