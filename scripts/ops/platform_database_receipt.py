"""P4 request-bound receipts; never infer rollback from a failed operation."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid


class OperationReceipt:
    def __init__(self, path, entry, execution_id, request):
        self.path = Path(path)
        self.identity = {"entry": entry, "execution_id": execution_id, "request": request}
        self.effects = {"commit_state": "not_attempted", "external_started": False}

    def write(self, status, **values):
        payload = dict(values, **self.identity, status=status, ok=status == "passed",
                       effects=({"commit_state": "unknown", "external_state": "unknown",
                                 "replay_allowed": False} if status == "pending" else dict(self.effects)))
        descriptor, temporary = tempfile.mkstemp(prefix=".receipt-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return payload

    def succeed(self, result):
        return self.write("passed", **{key: value for key, value in result.items()
                                      if key not in ("ok", "entry")})


@contextmanager
def operation_receipt(path, entry, execution_id, request):
    # The wrapper supplies an expected ID; direct diagnostics receive a fresh ID.
    identity = execution_id or uuid.uuid4().hex
    if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("PLATFORM_DATABASE_EXECUTION_ID_INVALID")
    receipt = OperationReceipt(path, entry, identity, request)
    receipt.path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(receipt.path) + ".lock", "a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt.write("pending")  # Invalidate earlier success before any model call.
        try:
            yield receipt
        except BaseException as error:
            try:
                receipt.write("failed", error_type=type(error).__name__)
            except OSError:
                pass  # Pending stays non-success; preserve the operation error.
            raise


def validate_success(payload, execution_id, request):
    if (payload.get("ok") is not True or payload.get("status") != "passed"
            or payload.get("execution_id") != execution_id or payload.get("request") != request):
        raise ValueError("PLATFORM_DATABASE_RECEIPT_IDENTITY_OR_RESULT_MISMATCH")
    return payload
