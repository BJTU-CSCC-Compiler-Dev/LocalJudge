# Intro

LocalJudge为系统能力大赛（CSCC）编译赛道设计。这个比赛需要参赛者设计一个源语言为类C语言、目标语言为ArmV7汇编的编译器，并根据汇编语言经过汇编器后生成的可执行文件在树莓派上的执行时间、正确性来排名。在这个比赛中，本地黑盒测试非常重要（很多队伍甚至是“测试导向开发”）。但是此前缺少比较简单易用的测试框架，LocalJudge就是为了解决这个痛点而设计的。

由于测试过程既需要在开发编译器的机器（下称PC机）上进行包括构建项目、编译源语言、汇编产生可执行文件等操作，也需要在树莓派（下称Pi）上进行执行、记录等操作，所以LocalJudge框架包括运行在PC机的部分和运行在Pi的部分。两部分通过规定的协议通信。

LocalJudge将每一个测试称为测试例（test case），将一系列测试例称为测试组（test suite）。你可以以test case或者test suite为单位测试。为了减少通信时间，你可以在PC机和Pi上分别创建内容一样的文件夹，这样你可以在PC机上指定测试的路径，LocalJudge不会将内容发送到Pi上，而是直接在Pi上用路径对应的内容进行测试。我们称这对文件夹路径为univ-path，这种测试方式为univ测试。

当然，你也可以要求LocalJudge发送测试内容到Pi上再进行测试，LocalJudge称这种测试为single测试。

我们需要你的PC机为Linux系统。



后续文档中使用的简称：

| 原称               | 简称                       |
| ------------------ | -------------------------- |
| LocalJudge         | LocJ                       |
| Compiler you build | UCPC (User Compiler on PC) |
| time limit         | tl                         |
| Pi上的LocalJudge   | LocJ-Pi                    |
| PC上的LocalJudge   | LocJ-PC                    |
| test case          | tc                         |
| test suite         | ts                         |



# 测试接口

## `TestStatus`分类

对于每一次test case，假设源文件是`T.c`，你的编译器把`T.c`编译成`T.s`，之后发送到树莓派上，经过汇编、链接成`T`可执行文件，之后执行`T`，输入为`T.in`，输出是`T.out`，之后和`T.ans`对比，如果相同就是正确，否则就是错误（注意CSCC会将返回值当作输出的一部分，所以一般不判TRE）。整体的测试流程如下：

| PC                                    | Pi                               | TestStatus                                                   |
| ------------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| Make Project                          |                                  | CCE = Compiler Compile Error<br />CBTLE = Compiler Build Time Limit Exceeded |
| Compile T.c to T.s with your compiler |                                  | TCE = Test program Compile Error<br />TCTLE = Test program Compile Time Limit Exceeded |
| Send T.s to Pi                        |                                  | UKE = UnKnown Error                                          |
|                                       | Assemble T.s and link with `gcc` | TLKE = Test program LinK Error                               |
|                                       | Run `T.c`                        | TTLE = Test Time Limit Exceeded                              |
|                                       | Compare `T.out` and `T.ans`      | TRE = Test Runtime Error<br />TWA = TestWrong Answer         |
|                                       | Return `AC`                      | AC = ACcepted                                                |

注意，这里的汇编也可以在PC机上完成（交叉编译）。



## 配置文件说明

我们的配置文件按照等级**从高到低**分成三层：LocJ层、test suite指定层、test case指定层，注意低层的配置文件里相同的项会覆盖高层配置文件的。比如如果低层配置文件有项`t`为1，而高层配置文件的`t`为2，那么就会使用低层配置文件的内容。

注意每一层配置文件都有限定能够配置的内容，你需要参照文档进行配置。比如如果LocJ层的文档没有说允许配置`t`的值，那么你在LocJ层对`t`的配置就会被忽略。



## LocJ层配置

你需要在PC机上创建配置文件`~/.config/CSCC2023-BJTU/LocJ.yaml`，它包括以下内容：

| Key           | Value Type     | Description                                          |
| ------------- | -------------- | ---------------------------------------------------- |
| pi-hostname   | string         | The hostname of pi (for connection).                 |
| pi-username   | string         | The user name of pi (for connection).                |
| [pi-password] | string         | The passwork of pi (for connection).                 |
| pi-locj-path  | string         | The **absolute path** to LocalJudge repo root in pi. |
| pi-py-prefix  | string         | The python prefix for pi.                            |
| pi-univ-path  | string         | Pi univ-path.                                        |
| pc-univ-path  | string         | Pc univ-path.                                        |
| pi-tmp-path   | string         | The path to tmp folder in pi.                        |
| pc-tmp-path   | string         | The path to tmp folder in pc.                        |
| tctl          | int            | Test program compile time limit (unit: ms).          |
| ttl           | int            | Test program time Limit (unit: ms).                  |
| src-ext-name  | string         | The extension name of source file (like `c`, `sy`).  |
| ca-exe        | list of string | Cross assembler executable and args.                 |


注意：

* Pi的`pi-univ-path`内容和Pc的`pc-univ-path`内容必须保证完全一致。LocJ不保证如果内容不一致会出现什么效果。我们建议这里使用git做控制。

* `pi-tmp-path`指向Pi的一个文件夹，LocJ不保证这个文件夹下的内容得到正确备份，所以你不应该在这个文件夹存放除了`.gitignore`文件外的任何数据。

* `pc-tmp-path`指向PC的一个文件夹，LocJ不保证这个文件夹下的内容得到正确备份，所以你不应该在这个文件夹存放除了`.gitignore`文件外的任何数据。

* `pi-py-prefix`是pi上执行python代码的前缀。可以是`python3`、`python`、`conda run -n bjtu-cscc-compiler python3`等等。

* `ca-exe`是交叉汇编器的命令行参数。以Ubuntu为例，`ca-exe`可以是`['arm-linux-gnueabihf-gcc', '-static']`，可以通过`sudo apt-get install gcc-arm-linux-gnueabihf`来安装。

  此外，`ca-exe`也支持通过命令行参数改变，见后续的文档。



## test case层配置

在一个test case的文件夹下，有这些文件（假设源文件是C语言的）：

```
T.c
T.in
T.ans
tcInfo.yaml
```

其中`T.c`、`T.in`、`T.ans`分别是源语言文件、输入文件、正确答案的输出文件（这里`T`就是case name，见后面解释）。`info.yaml`是这个test case的信息。

按照CSCC的样例规则，`T.ans`除了程序的输出外，还会额外被append程序的返回值（或者返回值模256）。

`tcInfo.yaml`一般包括：

| Key               | Value Type | Description                                                  |
| ----------------- | ---------- | ------------------------------------------------------------ |
| case-name         | string     | The name of this test.                                       |
| [from]            | string     | This test case is from where.                                |
| [tctl]            | int        | Test program compile time limit (unit: ms).                  |
| [ttl]             | int        | Test program time Limit (unit: ms).                          |
| [gcc-run-time]    | int        | Time spent by program compiled by gcc (unit: ms).            |
| [gcc-o2-run-time] | int        | Time spent by program compiled by gcc with option -O2 (unit: ms). |

注：

* `case-name`即`T`，比如一个test case如果叫tes的话，那么同文件下下就必须是`tes.c`、`tes.in`、`tes.ans`。
* `[x]`表示可选配置`x`。



## test suite层配置

LocJ以一个yaml文件作为一个test suite，这个yaml里有这些内容：

| Key        | Value Type      | Description                                        |
| ---------- | --------------- | -------------------------------------------------- |
| suite-name | string          | The name of this suite.                            |
| test-cases | list of strings | Pathes to all test cases this test suite includes. |
| [tctl]     | int             | Test program compile time limit (unit: ms).        |
| [ttl]      | int             | Test program time Limit (unit: ms).                |

注：

* `test-cases`是路径的列表，如果是相对路径的话，那么会相对yaml配置文件所在的文件夹。如果你选择univ测试，那么你必须保证所有test case都在`pc-univ-path`之下，否则LocJ会报错。



## test case result表项

对于每一个test case，LocJ-PC会在`tcPath`下生成`testResInfo.yaml`。LocJ-PC再根据测试的不同处理不同的信息。`tcResInfo.yaml`包含：

| Key         | Value Type | Description                       |
| ----------- | ---------- | --------------------------------- |
| test-status | string     | Test status of this test.         |
| stderr      | string     | Stderr of this test.              |
| [out]       | string     | Stdout of this test.              |
| [ans]       | string     | Answer file `T.ans` of this test. |

注：

* `test-status`就是`TestStatus`。
* 按照CSCC的样例标准，`stderr`会包含测试时间信息，所以`stderr`在返回的结果里。



## test suite result表项

对于每一个test suite，LocJ-PC会收集每一个test case的结果后，在`tsPath`下生成`testResInfo.yaml`：

| Key      | Value Type | Description               |
| -------- | ---------- | ------------------------- |
| res-list | list       | Test result of each case. |
|          |            |                           |

注：

* `res-list`下的每一个



## 命令行参数

你可以给LocJ-PC传一些命令行参数，它们的作用如下：

* `--univ`或`--single`：表示测试是univ测试还是single测试。
* `--path`，一个PC上的路径，指向test case或者test suite的文件夹。注意LocJ-PC会根据这个文件夹下是有`tsInfo.yaml`还是`tcInfo.yaml`判断这是个test case还是test suite。
* `--cargs`，你的Compiler的命令行参数。一个例子：`--cargs "['arm-linux-gnueabihf-gcc', '-x', 'c', '-S']"`。





# TODO

这里记录一些可以增加的feature（按照紧急程度排序，越靠上越紧急）：

* 改进文档：改成以需求驱动的文档。

* 在test case的`testResInfo.yaml`下增加运行时间项。

  > 由于python的`subprocess`本身没有提供计时的接口，所以可能需要要求程序自身支持输出执行时间。

* 在test suite的`testResInfo.yaml`下增加test case的路径（或者test case自己在结果记录路径）。

* 增加命令行参数`caExe`。
