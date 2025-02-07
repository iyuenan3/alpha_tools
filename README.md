# Brain Alpha

## 项目简介
Brain Alpha 是一个基于 Python 的项目，旨在利用 WorldQuant BRAIN 平台开发和模拟 Alpha 表达式。项目分为两个主要模块：Alpha Creator 和 Alpha Simulator。

## 功能

### Alpha Creator

#### 主要功能
- **登录**：使用用户凭据与 WorldQuant BRAIN API 进行身份验证。
- **获取数据字段**：从指定的数据集中提取支持的字段。
- **生成 Alpha 表达式**：基于基本面数据生成大量 Alpha 表达式。
- **输出待模拟文件**：将生成的 Alpha 表达式保存到 CSV 文件中，供后续模拟使用。

#### 运行方法
1. 创建 `brain_credential.txt` 文件，内容如下：
   ```json
   ["your_username", "your_password"]
   ```
2. 运行脚本：
   ```bash
   python alpha_creator.py
   ```
3. 生成的待模拟 Alpha 文件为：`alphas_pending_simulated.csv`。

### Alpha Simulator

#### 主要功能
- **多任务并发模拟**：支持同时运行多个回测任务。
- **任务管理**：动态加载 Alpha 表达式队列，自动处理成功或失败的模拟任务。
- **日志记录**：记录回测任务的状态和进度。
- **错误处理**：对网络请求失败和 API 错误进行重试和日志记录。

#### 运行方法
1. 确保已生成 `alphas_pending_simulated.csv` 文件。
2. 运行脚本：
   ```bash
   python alpha_simulator.py
   ```
3. 模拟结果：
   - 已完成 Simulate 的 Alpha 表达式保存到：`alphas_simulated.csv`

### Alpha Check

#### 主要功能
- **登录**：使用用户凭据与 WorldQuant BRAIN API 进行身份验证。
- **获取 Alpha 列表**：根据特定筛选条件（如 Fitness、Sharpe、Turnover 等）获取 Alpha 列表。
- **检查提交状态**：检查 Alpha 是否通过 Check Submiassion 测试，并在平台上更新其状态。
- **筛选成功的 Alpha**：识别并返回通过 Check Submiassion 测试的 Alpha 列表。

#### 运行方法
1. 运行脚本：
   ```bash
   python alpha_check.py
   ```

### Monitor Simulation

#### 主要功能
`monitor_simulation.sh` 是一个用于监控 `simulation.log` 日志文件的 Bash 脚本。如果日志文件在 10 分钟内未更新，则脚本会尝试终止 `alpha_simulator.py` 进程，然后重新启动该进程。该脚本可用于保障 `alpha_simulator.py` 的持续运行，避免因异常停止而导致的服务中断。

## 使用方法
1. 赋予执行权限：
   在终端中运行以下命令，确保脚本具有可执行权限：
   ```bash
   chmod +x monitor_simulation.sh
   ```
2. 运行守护进程:
   使用 `nohup` 让脚本在后台运行，并将日志输出到 `monitor.log`：
   ```bash
   nohup ./monitor_simulation.sh >> monitor.log 2>&1 &
   ```
3. 查看守护进程日志:
   可以使用以下命令实时查看 `monitor.log` 的日志输出：
   ```bash
   tail -f monitor.log
   ```
4. 终止守护进程:
   如果需要停止 `monitor_simulation.sh`，可以使用 `pkill` 命令：
   ```bash
   pkill -f monitor_simulation.sh
   ```

### 项目文件结构
```
brain_alpha/
├── LICENSE                       # Apache 2.0 License 文件
├── README.md                     # 说明书
├── auth_utils.py                 # Brain 登入脚本
├── alpha_check.py                # Alpha Check 脚本
├── alpha_creator.py              # Alpha Creator 脚本
├── alpha_simulator.py            # Alpha Simulator 脚本
├── alphas_pending_simulated.csv  # 待模拟的 Alpha 表达式文件
├── alphas_simulated.csv          # 所有已完成 Simulate 的 Alphas
├── monitor_simulation.sh         # 用于监控 simulation.log
├── brain_credential.txt          # 用户凭据文件
├── requirements.txt              # 依赖包
├── check.log                     # Alpha Check 日志
└── simulation.log                # Alpha Simulator 日志
```

### 运行环境
1. Python 3.12 及以上版本
2. 使用 `requirements.txt` 安装所需的库。
3. [WorldQuant BRAIN 平台](https://www.worldquantbrain.com/)的有效账号
4. 一个名为 `brain_credentials.txt` 的文件，存储您的 API 用户名和密码，文件格式如下：
  ```json
  ["your_username", "your_password"]
  ```

### 使用说明
1. 克隆仓库：
   ```bash
   git clone https://github.com/your-username/brain_alpha.git
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 将 `brain_credentials.txt` 文件放置在脚本所在的目录下。
3. 运行脚本：
   ```bash
   python alpha_creator.py
   ```
4. 脚本会生成一个名为 `alphas_pending_simulated.csv` 的文件，其中包含生成的 Alpha 表达式。
5. 运行 Simulate：
   ```bash
   chmod +x monitor_simulation.sh
   nohup ./monitor_simulation.sh >> monitor.log 2>&1 &
   ```

---

## 贡献
欢迎贡献代码！如果有任何改进建议，请提交 issue 或 pull request。

## 许可证
本项目基于 Apache License 2.0 许可。详情请参阅 `LICENSE` 文件。
