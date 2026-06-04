from collections.abc import Iterable


def retire_worker(owner, worker, disconnect: Iterable[tuple[object, object]] = (), timeout_ms: int = 1000):
    """Detach a QThread-like worker without destroying it while it is still running."""
    if worker is None:
        return

    for signal, slot in disconnect:
        try:
            if slot is None:
                signal.disconnect()
            else:
                signal.disconnect(slot)
        except Exception:
            pass

    retired = getattr(owner, "_retired_workers", None)
    if retired is None:
        retired = []
        setattr(owner, "_retired_workers", retired)

    for old in list(retired):
        try:
            if old.isRunning():
                continue
            retired.remove(old)
            old.deleteLater()
        except Exception:
            retired.remove(old)

    try:
        if worker.isRunning():
            worker.requestInterruption()
            worker.quit()
            if not worker.wait(timeout_ms):
                retired.append(worker)
                return
        worker.deleteLater()
    except Exception:
        retired.append(worker)
