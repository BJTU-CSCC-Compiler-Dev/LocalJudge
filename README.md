# Intro

LocalJudge为系统能力大赛编译赛道设计。这个比赛需要参赛者设计一个源语言为类C语言、目标语言为ArmV7汇编的编译器，并根据汇编语言经过汇编器后生成的可执行文件在树莓派上的执行时间、正确性来排名。在这个比赛中，本地黑盒测试非常重要（很多队伍甚至是“测试导向开发”）。但是此前缺少比较简单易用的测试框架，LocalJudge就是为了解决这个痛点而设计的。

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



# Workline

对于每一次test case，假设源文件是`T.c`，你的编译器把`T.c`编译成`T.s`，之后发送到树莓派上，经过汇编、链接成`T`可执行文件，之后执行`T`，输入为`T.in`，输出是`T.out`，之后和`T.ans`对比，如果相同就是正确，否则就是错误（注意`T.out`和`T.ans`的最后一行都是返回值，所以程序一般不存在RE）。整体的测试流程如下：

| PC                                    | Pi                               | Error Type                                                   |
| ------------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| Make Project                          |                                  | CCE = Compiler Compile Error<br />CBTLE = Compiler Build Time Limit Exceeded |
| Compile T.c to T.s with your compiler |                                  | TCE = Test program Compile Error<br />TCTLE = Test program Compile Time Limit Exceeded |
| Send T.s to Pi                        |                                  | UKE = UnKnown Error                                          |
|                                       | Assemble T.s and link with `gcc` | TLKE = Test program LinK Error                               |
|                                       | Run `T.c`                        | TTLE = Test program Time Limit Exceeded                      |
|                                       | Compare `T.out` and `T.ans`      | TRE = Test program Runtime Error<br />TWA = Test program Wrong Answer |
|                                       | Return `AC`                      |                                                              |

最后会将运行状态（包括时间等）返回、统计。

注意，这里的汇编也可以在PC机上完成（交叉编译）。



# 测试接口

## 配置文件说明

我们的配置文件按照等级从高到低分成三层：LocJ层、test suite指定层、test case指定层，注意低层的配置文件里相同的项会覆盖高层配置文件的。比如如果低层配置文件有项`t`为1，而高层配置文件的`t`为2，那么就会使用低层配置文件的内容。

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
* `pi-tmp-path`指向Pi的一个文件夹，LocJ不保证这个文件夹下的内容得到正确备份，所以你不应该在这个文件夹存放任何数据。
* `pc-tmp-path`指向PC的一个文件夹，LocJ不保证这个文件夹下的内容得到正确备份，所以你不应该在这个文件夹存放任何数据。
* `pi-py-prefix`是pi上执行python代码的前缀。可以是`python3`、`python`、`conda run -n bjtu-cscc-compiler python3`等等。
* 以Ubuntu为例，`ca-exe`可以是`['arm-linux-gnueabihf-gcc', '-static']`，可以通过`sudo apt-get install gcc-arm-linux-gnueabihf`来安装。



## test case层配置

在一个test case的文件夹下，有这些文件（假设源文件是C语言的）：

```
T.c
T.in
T.ans
info.yaml
```

其中`T.c`、`T.in`、`T.ans`分别是源语言文件、输入文件、正确答案的输出文件（这里`T`就是case name，见后面解释）。`info.yaml`是这个test case的信息。

`info.yaml`一般包括：

| Key               | Value Type | Description                                                  |
| ----------------- | ---------- | ------------------------------------------------------------ |
| case-name         | string     | The name of this test.                                       |
| from              | string     | This test case is from where.                                |
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



## LocJ-PC和LocJ-Pi的通信

### LocJ-PC给LocJ-Pi发tc-info.yaml信

对于每一个test case，LocJ-PC都会发一个`tc-info.yaml`给LocJ-Pi，LocJ-Pi则会根据`tc-info.yaml`的信息执行相应的测试，并产生结果。`tc-info.yaml`包含：

| Key            | Value Type | Description                         |
| -------------- | ---------- | ----------------------------------- |
| test-case-path | string     | Test type.                          |
| ttl            | int        | Test program time Limit (unit: ms). |
| exe-path       | string     | The path to exe flie.               |

注：

* 一般LocJ-PC会在`pc-tmp-path`下生成`tc-info.yaml`。
* LocJ-PC会指定test case的路径。对于univ测试，这个路径就是univ文件夹下的某个子文件夹；对于single测试，这个路径是`pi-tmp-path`。



## result表项

对于每一个test case，LocJ-Pi会返回一个`tc-result.yaml`给LocJ-PC。LocJ-PC再根据测试的不同处理不同的信息。`tc-result.yaml`包含：

| Key         | Value Type | Description               |
| ----------- | ---------- | ------------------------- |
| test-status | string     | Test status of this test. |
| stderr      | string     |                           |
| [out]       | string     |                           |
| [ans]       | string     |                           |



# 执行详细流程

## single test case测试

假设`test-case-name`是`T`，`src-ext-name`是`c`。

1. ssh连接pi，开启sftp服务。
2. 读取tc的`info.yaml`，获得信息。
3. 将`T.c`、`T.in`、`T.ans`发送到`pi-tmp-path`。
4. 用`cargs`编译`T.c`生成`T.S`，用`ca-exe`链接`T.S`生成`T`。
5. 收集`tc-info`信息并转化成`tc-info.yaml`、传送到pi上。
6. 



# 命令行参数说明



