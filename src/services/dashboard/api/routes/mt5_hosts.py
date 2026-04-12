"""MT5 Host管理API"""
import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.common.database.connection import db
from src.common.models.mt5_host import MT5Host

router = APIRouter(prefix="/api/mt5-hosts", tags=["MT5 Hosts"])


# ==================== 请求模型 ====================

class CreateMT5HostRequest(BaseModel):
    """创建MT5主机请求"""
    name: str
    host_type: str  # demo/real
    host: str
    port: int = 9090
    api_key: Optional[str] = None
    timeout: int = 10
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    use_investor: bool = True
    enabled: bool = True
    weight: float = 1.0
    tags: List[str] = []
    notes: Optional[str] = None


class UpdateMT5HostRequest(BaseModel):
    """更新MT5主机请求"""
    name: Optional[str] = None
    host_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None
    timeout: Optional[int] = None
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    use_investor: Optional[bool] = None
    enabled: Optional[bool] = None
    weight: Optional[float] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


# ==================== API端点 ====================

@router.get("")
async def list_mt5_hosts(
    host_type: Optional[str] = None,
    enabled: Optional[bool] = None
):
    """
    获取MT5主机列表

    Query参数：
    - host_type: 过滤类型 (demo/real)
    - enabled: 过滤启用状态
    """
    try:
        with db.session_scope() as session:
            query = session.query(MT5Host)

            # 过滤条件
            if host_type:
                query = query.filter(MT5Host.host_type == host_type)
            if enabled is not None:
                query = query.filter(MT5Host.enabled == enabled)

            hosts = query.order_by(MT5Host.created_at.desc()).all()

            return {
                "total": len(hosts),
                "hosts": [h.to_dict() for h in hosts]
            }

    except Exception as e:
        print(f"❌ 获取MT5主机列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{host_id}")
async def get_mt5_host(host_id: str):
    """获取单个MT5主机详情"""
    try:
        with db.session_scope() as session:
            host = session.query(MT5Host).filter(MT5Host.id == host_id).first()

            if not host:
                raise HTTPException(status_code=404, detail="MT5主机不存在")

            return host.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取MT5主机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_mt5_host(request: CreateMT5HostRequest):
    """创建MT5主机"""
    try:
        with db.session_scope() as session:
            # 生成ID
            host_id = str(uuid.uuid4())[:8]

            # 创建主机记录
            host = MT5Host(
                id=host_id,
                name=request.name,
                host_type=request.host_type,
                host=request.host,
                port=request.port,
                api_key=request.api_key,
                timeout=request.timeout,
                login=request.login,
                password=request.password,
                server=request.server,
                use_investor=request.use_investor,
                enabled=request.enabled,
                weight=request.weight,
                tags=json.dumps(request.tags),
                notes=request.notes
            )

            session.add(host)
            session.flush()

            print(f"✅ 创建MT5主机: {request.name} ({host_id})")

            return {
                "success": True,
                "host_id": host_id,
                "host": host.to_dict()
            }

    except Exception as e:
        print(f"❌ 创建MT5主机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{host_id}")
async def update_mt5_host(host_id: str, request: UpdateMT5HostRequest):
    """更新MT5主机"""
    try:
        with db.session_scope() as session:
            host = session.query(MT5Host).filter(MT5Host.id == host_id).first()

            if not host:
                raise HTTPException(status_code=404, detail="MT5主机不存在")

            # 更新字段
            if request.name is not None:
                host.name = request.name
            if request.host_type is not None:
                host.host_type = request.host_type
            if request.host is not None:
                host.host = request.host
            if request.port is not None:
                host.port = request.port
            if request.api_key is not None:
                host.api_key = request.api_key
            if request.timeout is not None:
                host.timeout = request.timeout
            if request.login is not None:
                host.login = request.login
            if request.password is not None:
                host.password = request.password
            if request.server is not None:
                host.server = request.server
            if request.use_investor is not None:
                host.use_investor = request.use_investor
            if request.enabled is not None:
                host.enabled = request.enabled
            if request.weight is not None:
                host.weight = request.weight
            if request.tags is not None:
                host.tags = json.dumps(request.tags)
            if request.notes is not None:
                host.notes = request.notes

            session.flush()

            print(f"✅ 更新MT5主机: {host.name} ({host_id})")

            return {
                "success": True,
                "host": host.to_dict()
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 更新MT5主机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{host_id}")
async def delete_mt5_host(host_id: str):
    """删除MT5主机"""
    try:
        with db.session_scope() as session:
            host = session.query(MT5Host).filter(MT5Host.id == host_id).first()

            if not host:
                raise HTTPException(status_code=404, detail="MT5主机不存在")

            host_name = host.name
            session.delete(host)
            session.flush()

            print(f"✅ 删除MT5主机: {host_name} ({host_id})")

            return {
                "success": True,
                "message": f"已删除MT5主机: {host_name}"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 删除MT5主机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{host_id}/test")
async def test_mt5_host(host_id: str):
    """
    测试主机连接（多层级）

    Level 1: TCP端口可达性
    Level 2: HTTP服务响应
    Level 3: MT5 API功能
    """
    import time
    import socket
    import requests

    try:
        with db.session_scope() as session:
            host = session.query(MT5Host).filter(MT5Host.id == host_id).first()

            if not host:
                raise HTTPException(status_code=404, detail="MT5主机不存在")

            test_results = {
                "host_id": host_id,
                "host_name": host.name,
                "host": host.host,
                "port": host.port,
                "tests": {
                    "level1_tcp": None,
                    "level2_http": None,
                    "level3_mt5": None
                }
            }

            # ===== Level 1: TCP端口测试 =====
            tcp_start = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(host.timeout)
                result = sock.connect_ex((host.host, host.port))
                sock.close()

                tcp_latency = int((time.time() - tcp_start) * 1000)

                if result == 0:
                    test_results["tests"]["level1_tcp"] = {
                        "status": "success",
                        "message": f"端口 {host.port} 可达",
                        "latency_ms": tcp_latency
                    }
                else:
                    test_results["tests"]["level1_tcp"] = {
                        "status": "failed",
                        "message": f"端口 {host.port} 不可达 (连接被拒绝或超时)",
                        "latency_ms": tcp_latency
                    }
                    # TCP失败，后续测试无意义
                    return {
                        "success": False,
                        **test_results,
                        "overall_status": "tcp_failed"
                    }

            except Exception as tcp_error:
                test_results["tests"]["level1_tcp"] = {
                    "status": "error",
                    "message": f"TCP测试异常: {str(tcp_error)}",
                    "latency_ms": 0
                }
                return {
                    "success": False,
                    **test_results,
                    "overall_status": "tcp_error"
                }

            # ===== Level 2: HTTP服务测试 =====
            http_start = time.time()
            try:
                url = f"http://{host.host}:{host.port}/health"
                headers = {}
                if host.api_key:
                    headers['Authorization'] = f'Bearer {host.api_key}'

                response = requests.get(url, headers=headers, timeout=host.timeout)
                http_latency = int((time.time() - http_start) * 1000)

                if response.status_code == 200:
                    test_results["tests"]["level2_http"] = {
                        "status": "success",
                        "message": "HTTP服务正常响应",
                        "latency_ms": http_latency,
                        "status_code": response.status_code
                    }

                    # ===== Level 3: MT5 API测试 =====
                    try:
                        health_data = response.json()
                        mt5_connected = health_data.get('mt5_connected', False)

                        if mt5_connected:
                            test_results["tests"]["level3_mt5"] = {
                                "status": "success",
                                "message": "MT5 Terminal已连接",
                                "details": health_data
                            }
                            return {
                                "success": True,
                                **test_results,
                                "overall_status": "all_passed",
                                "latency_ms": http_latency
                            }
                        else:
                            test_results["tests"]["level3_mt5"] = {
                                "status": "failed",
                                "message": "MT5 API Bridge运行但MT5 Terminal未连接",
                                "details": health_data
                            }
                            return {
                                "success": False,
                                **test_results,
                                "overall_status": "mt5_not_connected",
                                "latency_ms": http_latency
                            }
                    except:
                        test_results["tests"]["level3_mt5"] = {
                            "status": "unknown",
                            "message": "响应格式不是MT5 API（可能是其他HTTP服务）"
                        }
                        return {
                            "success": True,
                            **test_results,
                            "overall_status": "http_ok_not_mt5",
                            "latency_ms": http_latency
                        }
                else:
                    test_results["tests"]["level2_http"] = {
                        "status": "failed",
                        "message": f"HTTP响应异常 (状态码: {response.status_code})",
                        "latency_ms": http_latency,
                        "status_code": response.status_code
                    }
                    return {
                        "success": False,
                        **test_results,
                        "overall_status": "http_error"
                    }

            except requests.exceptions.Timeout:
                test_results["tests"]["level2_http"] = {
                    "status": "timeout",
                    "message": f"HTTP请求超时（>{host.timeout}s）",
                    "latency_ms": 0
                }
                return {
                    "success": False,
                    **test_results,
                    "overall_status": "http_timeout"
                }
            except requests.exceptions.ConnectionError as http_error:
                test_results["tests"]["level2_http"] = {
                    "status": "failed",
                    "message": "端口开放但不是HTTP服务 (可能是其他协议)",
                    "latency_ms": 0
                }
                return {
                    "success": False,
                    **test_results,
                    "overall_status": "not_http_service"
                }
            except Exception as http_error:
                test_results["tests"]["level2_http"] = {
                    "status": "error",
                    "message": f"HTTP测试异常: {str(http_error)}",
                    "latency_ms": 0
                }
                return {
                    "success": False,
                    **test_results,
                    "overall_status": "http_exception"
                }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 测试主机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
