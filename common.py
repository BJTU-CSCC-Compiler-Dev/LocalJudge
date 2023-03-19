import sys
import json


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)


def bprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	exit(0)


def fmt_dict(d):
	return json.dumps(d, indent=4)


def todo(msg: str = ""):
	eprint(f"TODO: [{msg}]")
	raise NotImplementedError()
