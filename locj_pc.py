import os.path
from test_status import TestStatus
import yaml
from pathlib import Path
from common import eprint, fmt_dict, todo
from argparse import ArgumentParser, ArgumentError
import sys
import typing as typ
import paramiko
import subprocess as sp
from subprocess import TimeoutExpired

defaultLocjConfigPath = Path.home() / Path(".config/CSCC2023-BJTU/LocJ.yaml")
locjFingerprintContent = "local-judge"


def is_test_suite_yaml(path: Path):
	return path.is_file() and path.suffix == ".yaml"


def is_test_case_folder(path: Path):
	return path.is_dir() and (path / Path("info.yaml")).exists()


def check_legal_cargs(cargs):
	assert isinstance(cargs, list)
	allStr = True
	for s in cargs:
		allStr = allStr and isinstance(s, str)
	assert allStr


def get_tctl_and_ttl(locjConfig: typ.Dict, tsConfig: typ.Optional[typ.Dict], tcConfig: typ.Dict):
	keyName = "tctl"
	if keyName in tcConfig.keys():
		tctl = tcConfig[keyName]
	elif tsConfig is not None and keyName in tsConfig.keys():
		tctl = tsConfig[keyName]
	else:
		tctl = locjConfig[keyName]
	keyName = "ttl"
	if keyName in tcConfig.keys():
		ttl = tcConfig[keyName]
	elif tsConfig is not None and keyName in tsConfig.keys():
		ttl = tsConfig[keyName]
	else:
		ttl = locjConfig[keyName]
	return tctl, ttl


def read_locj_config(locjConfigPath: Path = defaultLocjConfigPath, doCheck: bool = True):
	with open(locjConfigPath, "r") as fp:
		locjConfig: typ.Dict = yaml.safe_load(fp)
	if not doCheck:
		return locjConfig
	# pi-hostname pi-username pi-password
	piHostName: str = locjConfig["pi-hostname"]
	piUsername: str = locjConfig["pi-username"]
	piPassword: typ.Optional[str] = locjConfig.setdefault("pi-password", None)
	# check connection
	ssh = paramiko.SSHClient()
	ssh.load_host_keys(os.path.expanduser(Path.home() / ".ssh/known_hosts"))
	ssh.connect(hostname=piHostName, username=piUsername, password=piPassword)
	# pi-locj-path
	piLocjPath: str = locjConfig["pi-locj-path"]
	assert ssh.exec_command(command=f"cat {piLocjPath}/locj-fingerprint.txt")[1].readlines() == ["local-judge"]
	# pi-py-prefix
	piPyPrefix = locjConfig["pi-py-prefix"]
	assert ssh.exec_command(command=f"{piPyPrefix} {piLocjPath}/hello_world.py")[1].readlines() == ["hello"]
	# pi-univ-path
	piUnivPath = locjConfig["pi-univ-path"]
	assert ssh.exec_command(command=f"cat {piUnivPath}/univ-fingerprint.txt")[1] == "univ"
	# pc-univ-path
	pcUnivPath = locjConfig["pc-univ-path"]
	with open(Path(pcUnivPath) / "univ-fingerprint.txt", "r") as fp:
		assert fp.readline() == "univ"
	# pi-tmp-path
	piTmpPath = locjConfig["pi-tmp-path"]
	assert ssh.exec_command(command=f"test -d {piTmpPath} && echo y || echo n")[1] == "y"
	# pc-tmp-path
	pcTmpPath = locjConfig["pc-tmp-path"]
	assert Path(pcTmpPath).is_dir()
	# tctl ttl src-ext-name
	assert ("tctl" in locjConfig.keys())
	assert ("ttl" in locjConfig.keys())
	assert ("src-ext-name" in locjConfig.keys())
	# ca-exe
	assert ("ca-exe" in locjConfig.keys())
	ssh.close()
	return locjConfig


def judge_test_case_single(
		pcTcPath: Path,
		locjConfig: typ.Dict,
		cargs: typ.List[str],
		tsConfig: typ.Optional[typ.Dict] = None,
		caExe: typ.Optional[typ.List[str]] = None
):
	resStatus = TestStatus.AC
	stderr = ""
	# load some info from locjConfig
	extName: str = locjConfig["src-ext-name"]
	pcTmpPath: Path = Path(locjConfig["pc-tmp-path"])
	piTmpPath: Path = Path(locjConfig["pi-tmp-path"])
	piHostName: str = locjConfig["pi-hostname"]
	piUsername: str = locjConfig["pi-username"]
	piPyPrefix = locjConfig["pi-py-prefix"]
	piLocjPath = Path(locjConfig["pi-locj-path"])
	caExe = caExe if caExe is None else locjConfig["ca-exe"]
	# ssh to pi
	ssh = paramiko.SSHClient()
	ssh.load_host_keys(os.path.expanduser(Path.home() / ".ssh/known_hosts"))
	ssh.connect(hostname=piHostName, username=piUsername)
	sftp = ssh.open_sftp()
	# load tcConfig
	with open(pcTcPath / "info.yaml", "r") as fp:
		tcConfig: typ.Dict = yaml.safe_load(fp)
	tcName: str = tcConfig["case-name"]
	tctl, ttl = get_tctl_and_ttl(locjConfig, tsConfig, tcConfig)
	# transfer .c, .in, .ans files
	pcTcSrcPath = pcTcPath / f"{tcName}.{extName}"
	pcTcInPath = pcTcPath / f"{tcName}.in"
	pcTcAnsPath = pcTcPath / f"{tcName}.ans"
	assert pcTcSrcPath.exists()
	assert pcTcInPath.exists()
	assert pcTcAnsPath.exists()
	piTcPath = piTmpPath
	piTcSrcPath = piTcPath / f"{tcName}.{extName}"
	piTcInPath = piTcPath / f"{tcName}.in"
	piTcAnsPath = piTcPath / f"{tcName}.ans"
	sftp.put(localpath=str(pcTcSrcPath), remotepath=str(piTcSrcPath))
	sftp.put(localpath=str(pcTcInPath), remotepath=str(piTcInPath))
	sftp.put(localpath=str(pcTcAnsPath), remotepath=str(piTcAnsPath))
	# compile and assemble on pc
	cargs += [str(pcTcSrcPath), "-o", f"{pcTmpPath}/{tcName}.S"]
	try:
		spRet = sp.run(cargs, cwd=Path.cwd(), timeout=tctl / 1000)
		resStatus = TestStatus.TCE if spRet.returncode != 0 else resStatus
		stderr = spRet.stderr
	except TimeoutExpired:
		resStatus = TestStatus.TCTLE
	if resStatus == TestStatus.AC:
		caExe += [f"{pcTmpPath}/{tcName}.S", "-o", f"{pcTmpPath}/{tcName}"]
		spRet = sp.run(caExe, cwd=Path.cwd())
		resStatus = TestStatus.TLKE if spRet.returncode != 0 else resStatus
		stderr = spRet.stderr
	# collect tc-info and transfer tc-info.yaml file
	tcInfo = dict()
	tcInfo["test-case-path"] = str(piTcPath)
	tcInfo["ttl"] = ttl
	tcInfo["exe-path"] = f"{piTmpPath}/{tcName}"
	pcTcInfoPath = pcTmpPath / "tc-info.yaml"
	piTcInfoPath = piTmpPath / "tc-info.yaml"
	with open(pcTcInfoPath, "w") as fp:
		yaml.safe_dump(data=tcInfo, stream=fp)
	if resStatus == TestStatus.AC:
		sftp.put(str(pcTcInfoPath), str(piTcInfoPath))
		sftp.put(f"{pcTmpPath}/{tcName}", f"{piTmpPath}/{tcName}")
	# run test
	piTcResultPath = piTmpPath / "tc-result.yaml"
	pcTcResultPath = pcTmpPath / "tc-result.yaml"
	tcRes = dict()
	if resStatus == TestStatus.AC:
		ssh.exec_command(
			command=f"{piPyPrefix} {piLocjPath / 'locj_pi.py'} --info {piTcInfoPath} --result {piTcResultPath}")
		sftp.get(str(piTcResultPath), str(pcTcResultPath))
		with open(pcTcResultPath, "r") as fp:
			tcRes: typ.Dict = yaml.safe_load(fp)
	else:
		tcRes = {
			"test-status": resStatus.value,
			"stderr": stderr,
		}
	# collect tc-result and
	sftp.close()
	ssh.close()
	return tcRes


argParser = ArgumentParser(prog="locj_pc")
argParser.add_argument("--univ", action="store_true", default=False, help="Univ test.")
argParser.add_argument("--single", action="store_true", default=False, help="Single test.")
argParser.add_argument("--path", action="store", help="Path to test case folder or test suite yaml file.")
argParser.add_argument("--cargs", action="store", help="Compiler args.")


def main():
	locjConfig = read_locj_config(doCheck=True)
	args = argParser.parse_args(sys.argv[1:])
	assert (args.univ ^ args.single)
	path = Path(args.path)
	cargs = eval(args.cargs)
	check_legal_cargs(cargs)
	if is_test_suite_yaml(path):
		pass
	elif is_test_case_folder(path):
		if args.single:
			tcRes = judge_test_case_single(path, locjConfig, cargs)
		else:
			todo()
	else:
		raise ArgumentError(message=f"Path [{path}] is not test suite nor test case!", argument=None)


if __name__ == '__main__':
	main()
