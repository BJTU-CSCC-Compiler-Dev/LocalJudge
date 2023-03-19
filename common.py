import sys
import json


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)


def fmt_dict(d):
	return json.dumps(d, indent=4)


def todo(msg: str = ""):
	eprint(f"TODO: [{msg}]")
	raise NotImplementedError()
