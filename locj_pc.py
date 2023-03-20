import os.path
from test_status import TestStatus
import yaml
from pathlib import Path
from common import eprint, fmt_dict, todo, bprint, panic
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
	return path.is_dir() and (path / Path("tcInfo.yaml")).exists()


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
	assert ssh.exec_command(command=f"cat {piUnivPath}/univ-fingerprint.txt")[1].readlines() == ["univ\n"]
	# pc-univ-path
	pcUnivPath = locjConfig["pc-univ-path"]
	with open(Path(pcUnivPath) / "univ-fingerprint.txt", "r") as fp:
		assert fp.readline() == "univ\n"
	# pi-tmp-path
	piTmpPath = locjConfig["pi-tmp-path"]
	assert ssh.exec_command(command=f"test -d {piTmpPath} && echo y || echo n")[1].readlines() == ["y\n"]
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


def gen_exe(
		piTcPath: Path, pcTcPath: Path, tcName: str,
		tctl: int, extName: str, cargs: typ.List[str], caExe: typ.List[str],
		ssh: paramiko.client.SSHClient, sftp: paramiko.sftp_client.SFTPClient):
	"""
	Called after data (.in, .ans, ...) prepared.
	"""
	resStatus = TestStatus.AC
	stderr = str()
	cargs = cargs + [f"{pcTcPath}/{tcName}.{extName}", "-o", f"{pcTcPath}/{tcName}.S"]
	try:
		spRet = sp.run(cargs, cwd=Path.cwd(), timeout=tctl / 1000)
		resStatus = TestStatus.TCE if spRet.returncode != 0 else resStatus
		stderr = spRet.stderr
	except TimeoutExpired:
		resStatus = TestStatus.TCTLE
	if resStatus == TestStatus.AC:
		caExe = caExe + [f"{pcTcPath}/{tcName}.S", "-o", f"{pcTcPath}/{tcName}"]
		spRet = sp.run(caExe, cwd=Path.cwd())
		resStatus = TestStatus.TLKE if spRet.returncode != 0 else resStatus
		stderr = spRet.stderr
	sftp.put(f"{pcTcPath}/{tcName}", f"{piTcPath}/{tcName}")
	return resStatus, stderr


def run_wrapper_and_get_res(
		piTcPath: Path, pcTcPath: Path, ttl: int,
		piPyPrefix: str, piLocjPath: Path,
		ssh: paramiko.client.SSHClient, sftp: paramiko.sftp_client.SFTPClient):
	ssh.exec_command(command=f"{piPyPrefix} {piLocjPath}/wrapper.py --tcPath {piTcPath} --ttl {ttl}")
	sftp.get(f"{piTcPath}/testResInfo.yaml", f"{pcTcPath}/testResInfo.yaml")
	with open(f"{pcTcPath}/testResInfo.yaml", "r") as fp:
		tcRes: typ.Dict = yaml.safe_load(fp)
	return tcRes


def transfer_single_test_case(
		tcName: str, extName: str, piTcPath: Path, pcTcPath: Path,
		sftp: paramiko.sftp_client.SFTPClient):
	pcTcSrcPath = pcTcPath / f"{tcName}.{extName}"
	pcTcInPath = pcTcPath / f"{tcName}.in"
	pcTcAnsPath = pcTcPath / f"{tcName}.ans"
	pcTcInfoPath = pcTcPath / "tcInfo.yaml"
	assert pcTcSrcPath.exists()
	assert pcTcInPath.exists()
	assert pcTcAnsPath.exists()
	assert pcTcInfoPath.exists()
	piTcSrcPath = piTcPath / f"{tcName}.{extName}"
	piTcInPath = piTcPath / f"{tcName}.in"
	piTcAnsPath = piTcPath / f"{tcName}.ans"
	piTcInfoPath = piTcPath / "tcInfo.yaml"
	sftp.put(localpath=str(pcTcSrcPath), remotepath=str(piTcSrcPath))
	sftp.put(localpath=str(pcTcInPath), remotepath=str(piTcInPath))
	sftp.put(localpath=str(pcTcAnsPath), remotepath=str(piTcAnsPath))
	sftp.put(localpath=str(pcTcInfoPath), remotepath=str(piTcInfoPath))


def ssh_to_pi(locjConfig: typ.Dict):
	ssh = paramiko.SSHClient()
	ssh.load_host_keys(os.path.expanduser(Path.home() / ".ssh/known_hosts"))
	ssh.connect(
		hostname=locjConfig["pi-hostname"], username=locjConfig["pi-username"],
		password=locjConfig.setdefault("pi-password", None))
	sftp = ssh.open_sftp()
	return ssh, sftp


def get_pi_tc_path(isSingle: bool, isUniv: bool, piTmpPath: Path, pcTcPath: Path, piUnivPath: Path, pcUnivPath: Path):
	if isSingle:
		return piTmpPath
	elif isUniv:
		return piUnivPath / pcTcPath.relative_to(pcUnivPath)
	else:
		panic()


def judge_test_case(
		pcTcPath: Path,
		locjConfig: typ.Dict,
		cargs: typ.List[str],
		isSingle: bool, isUniv: bool,
		tsConfig: typ.Optional[typ.Dict] = None,
		caExe: typ.Optional[typ.List[str]] = None,
):
	# load some info from locjConfig
	extName: str = locjConfig["src-ext-name"]
	piTmpPath: Path = Path(locjConfig["pi-tmp-path"])
	piPyPrefix: str = locjConfig["pi-py-prefix"]
	piLocjPath: Path = Path(locjConfig["pi-locj-path"])
	piUnivPath: Path = Path(locjConfig["pi-univ-path"])
	pcUnivPath: Path = Path(locjConfig["pc-univ-path"])
	caExe = caExe if caExe is not None else locjConfig["ca-exe"]
	# ssh to pi
	ssh, sftp = ssh_to_pi(locjConfig)
	# load tcConfig
	with open(pcTcPath / "tcInfo.yaml", "r") as fp:
		tcConfig: typ.Dict = yaml.safe_load(fp)
	tcName: str = tcConfig["case-name"]
	tctl, ttl = get_tctl_and_ttl(locjConfig, tsConfig, tcConfig)
	# generate piTcPath info and transfer files (if needed)
	piTcPath = get_pi_tc_path(isSingle, isUniv, piTmpPath, pcTcPath, pcUnivPath, piUnivPath)
	if isSingle:
		transfer_single_test_case(tcName, extName, piTcPath, pcTcPath, sftp)
	# compile and assemble on pc
	resStatus, stderr = gen_exe(piTcPath, pcTcPath, tcName, tctl, extName, cargs, caExe, ssh, sftp)
	# run test
	if resStatus == TestStatus.AC:
		tcRes = run_wrapper_and_get_res(piTcPath, pcTcPath, ttl, piPyPrefix, piLocjPath, ssh, sftp)
	else:
		tcRes = {
			"test-status": resStatus.value,
			"stderr": stderr,
		}
	# collect tc-result and return
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
			tcRes = judge_test_case(path, locjConfig, cargs, True, False)
			print(tcRes)
		else:
			todo()
	else:
		raise ArgumentError(message=f"Path [{path}] is not test suite nor test case!", argument=None)


if __name__ == '__main__':
	main()
