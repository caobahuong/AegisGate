# AegisGate Backend (Core)

This directory serves as the root backend container. The core engine and implementation are located in [`../core/`](../core/README.md).

To run the backend from here:
```bash
python main.py
```
Or from the root directory:
```bash
python -m uvicorn core.main:app --host 127.0.0.1 --port 8000 --reload
```

For full documentation of the backend architecture, services, state machine, and models, please refer to [`../core/README.md`](../core/README.md).
