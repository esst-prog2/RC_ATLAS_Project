from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SOURCE_PATH = Path(__file__).with_name("LogiTrackRC v4.4.py")
MODULE_NAME = "logitrack_rc_v4_4_source"

spec = spec_from_file_location(MODULE_NAME, SOURCE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load application module from {SOURCE_PATH}")

module = module_from_spec(spec)
spec.loader.exec_module(module)

app = module.app
main = module.main

if __name__ == "__main__":
    main()
