from argparse import ArgumentParser
import sys
from pathlib import Path
import subprocess as sp
from subprocess import TimeoutExpired
import yaml
from test_status import TestStatus

argParser = ArgumentParser(prog="locj-pi")
argParser.add_argument("--info", action="store")
argParser.add_argument("--result", action="store")

if __name__ == '__main__':
	args = argParser.parse_args(sys.argv[1:])
	testInfoPath = Path(args.info)
	resultPath = Path(args.result)
	with open(testInfoPath, "r") as fp:
		testInfo = yaml.safe_load(fp)
	tcPath = testInfo["test-case-path"]
	ttl = testInfo["ttl"]
	exePath = testInfo["exe-path"]
	with open(tcPath, "r") as fp:
		tcInfo = yaml.safe_load(fp)
	tcName = tcInfo["case-name"]
	stderr = ""
	out = None
	ans = None
	try:
		spRet = sp.run([exePath], stdin=tcPath / f"{tcName}.in", stdout=tcPath / f"{tcName}.out", timeout=ttl)
		stderr = spRet.stderr
		with open(tcPath / f"{tcName}.out", "w+") as fp:
			fp.write(f"\n{spRet.returncode}")
		with open(tcPath / f"{tcName}.out", "r") as fp:
			out = fp.readlines()
		with open(tcPath / f"{tcName}.ans", "r") as fp:
			ans = fp.readlines()
		if out == ans:
			resStatus = TestStatus.AC
		else:
			resStatus = TestStatus.TWA
	except TimeoutExpired:
		resStatus = TestStatus.TTLE
	result = {
		"test-status": resStatus.value,
		"stderr": stderr,
	}
	if out is not None:
		result["out"] = out
	if ans is not None:
		result["ans"] = ans
	with open(resultPath, "w") as fp:
		fp.write(yaml.safe_dump(result, indent=4))