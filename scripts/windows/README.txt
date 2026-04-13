==========================================
Windows MT5 Worker 快速指南
==========================================

【使用】
双击运行: worker.bat

菜单:
  1. 安装MT5终端
  2. 下载历史数据
  3. 启动Bridge监听
  4. 查看状态

【配置】
在Mac/Cloud的配置文件添加此Worker:

config/mac.yaml:
  mt5_hosts:
    demo_worker_1:
      type: "demo"           # demo/real
      host: "192.168.1.100"  # 此Windows IP
      port: 9090
      login: 5049130509

【防火墙】
New-NetFirewallRule -DisplayName "MT5" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow
