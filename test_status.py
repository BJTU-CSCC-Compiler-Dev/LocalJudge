from enum import Enum


# noinspection SpellCheckingInspection
class TestStatus(Enum):
	# CCE = Compiler Compile Error
	CCE = "CCE"
	# CBTLE = Compiler Build Time Limit Exceeded
	CBTLE = "CBTLE"
	# TCE = Test program Compile Error
	TCE = "TCE"
	# TCTLE = Test program Compile Time Limit Exceeded
	TCTLE = "TCTLE"
	# UKE = UnKnown Error
	UKE = "UKE"
	# TLKE = Test program LinK Error
	TLKE = "TLKE"
	# TTLE = Test program Time Limit Exceeded
	TTLE = "TTLE"
	# Test program Runtime Error
	TRE = "TRE"
	# Test Wrong Answer
	TWA = "TWA"
	# ACcepted
	AC = "AC"


if __name__ == '__main__':
	print(TestStatus.AC.value)
