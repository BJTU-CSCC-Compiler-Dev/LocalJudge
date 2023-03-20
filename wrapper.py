from argparse import ArgumentParser
import sys
from pathlib import Path
import subprocess as sp
from subprocess import TimeoutExpired
import yaml
from test_status import TestStatus
import os, sys, stat

argParser = ArgumentParser(prog="wrapper")
argParser.add_argument("--tcPath", action="store", required=True)
argParser.add_argument("--ttl", action="store", required=True)

if __name__ == '__main__':
	args = argParser.parse_args(sys.argv[1:])
	tcPath = args.tcPath
	ttl = int(args.ttl)
	assert Path(tcPath).exists()
	# load tcInfo and read info
	with open(f"{tcPath}/tcInfo.yaml", "r") as fp:
		tcInfo = yaml.safe_load(fp)
	tcName = tcInfo["case-name"]
	stderr = ""
	out = None
	ans = None
	try:
		with open(f"{tcPath}/{tcName}.in", "r") as fin:
			with open(f"{tcPath}/{tcName}.out", "w") as fout:
				os.chmod(f"{tcPath}/{tcName}", stat.S_IXUSR | stat.S_IWUSR | stat.S_IRUSR)
				spRet = sp.run(f"{tcPath}/{tcName}", stdin=fin, stdout=fout, timeout=ttl)
		stderr = "" if spRet.stderr is None else spRet.stderr
		with open(f"{tcPath}/{tcName}.out", "w+") as fp:
			fp.write(f"{spRet.returncode}")
		with open(f"{tcPath}/{tcName}.out", "r") as fp:
			out = fp.readlines()
		with open(f"{tcPath}/{tcName}.ans", "r") as fp:
			ans = fp.readlines()
		if out == ans:
			resStatus = TestStatus.AC
		else:
			resStatus = TestStatus.TWA
	except TimeoutExpired:
		resStatus = TestStatus.TTLE
	testResInfo = {
		"test-status": resStatus.value,
		"stderr": stderr,
	}
	# noinspection PyUnreachableCode
	if False:
		if out is not None:
			testResInfo["out"] = out
		if ans is not None:
			testResInfo["ans"] = ans
	with open(f"{tcPath}/testResInfo.yaml", "w") as fp:
		fp.write(yaml.safe_dump(testResInfo, indent=4))
