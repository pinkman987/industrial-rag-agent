TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "检索工业设备运维知识库，返回与用户问题相关的文档片段和引用来源。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用户的设备故障、运维或排查问题。",
                    },
                    "device_code": {
                        "type": "string",
                        "description": "可选设备编码，例如 SV300-01，仅用于辅助检索。",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_device_info",
            "description": "查询指定设备的基础信息，例如设备名称、类型、位置、厂家和状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_code": {
                        "type": "string",
                        "description": "设备编码，例如 SV300-01、CONV-A1、CNC-X200。",
                    },
                },
                "required": ["device_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_alarm_records",
            "description": "查询指定设备最近的报警记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_code": {
                        "type": "string",
                        "description": "设备编码，例如 SV300-01。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回最近多少条报警记录，默认 5。",
                        "default": 5,
                    },
                },
                "required": ["device_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_maintenance_records",
            "description": "查询指定设备最近的维修记录和工单处理结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_code": {
                        "type": "string",
                        "description": "设备编码，例如 SV300-01。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回最近多少条维修记录，默认 5。",
                        "default": 5,
                    },
                },
                "required": ["device_code"],
            },
        },
    },
]


TOOL_NAMES = [tool["function"]["name"] for tool in TOOL_SPECS]
