import requests
import json

# 配置地址
BASE_URL = "http://127.0.0.1:8000/api"
TEST_ID = "MOON_TEST_CHAR"
RENAME_ID = "MOON_CHAR_FINAL"

def print_response(resp, title):
    """格式化打印 API 响应内容"""
    print(f"\n{'='*30} {title} {'='*30}")
    print(f"状态码: {resp.status_code}")
    try:
        # 使用 indent=2 格式化打印 JSON
        print("响应体:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except:
        print(f"内容: {resp.text}")

def run_content_test():
    print("🚀 开始 API 响应内容完整性测试\n")

    # 1. 获取元数据 (验证月体系类型是否存在)
    res_meta = requests.get(f"{BASE_URL}/meta")
    print_response(res_meta, "1. 元数据 (GET /api/meta)")

    # 2. 创建虚拟测试角色 (验证 crit_dmg 和 def 铁律字段)
    mock_data = {
        "base_stats": {
            "elements": ["Hydro"],
            "atk": 500,
            "hp": 18000,
            "def": 850.0,     # 对应模型中的 def_
            "crit_rate": 0.05,
            "crit_dmg": 0.88, # 铁律命名字段
            "em": 300,
            "energy_recharge_bonus": 0.35
        },
        "skills": {
            "ChargedAttack": {
                "default": {
                    "multipliers": [{"type": "hp_percent", "value": 25.0}],
                    "element": "Dendro",
                    "damage_type": "MoonBloom" # 设定月绽放类型
                }
            }
        },
        "buffs": [
            {
                "type": "moon_base_flat",
                "value": "em * 4.0", # 测试公式解析
                "scope": "self"
            }
        ]
    }
    res_create = requests.post(f"{BASE_URL}/characters/{TEST_ID}", json=mock_data)
    print_response(res_create, f"2. 创建角色 (POST /api/characters/{TEST_ID})")

    # 3. 验证保存后的数据结构 (重点观察别名 def 是否被正确序列化)
    res_get = requests.get(f"{BASE_URL}/characters/{TEST_ID}")
    print_response(res_get, "3. 验证数据回显 (GET /api/characters)")

    # 4. 执行月绽放伤害计算 (核心：观察 solutions 中的面板)
    calc_req = {
        "target_char": TEST_ID,
        "teammates": [],
        "skill_type": "ChargedAttack",
        "reaction": "MoonBloom",
        "forced_set": "" # 保持为空以确保有计算结果
    }
    res_calc = requests.post(f"{BASE_URL}/calculate", json=calc_req)
    print_response(res_calc, "4. 计算结果 (POST /api/calculate)")

    # 5. 更新套装动态公式
    set_update = {
        "effects": {
            "2": [{"type": "em", "value": 80.0}],
            "4": [{"type": "moon_dmg_bonus", "value": "min(0.8, em * 0.001)"}]
        }
    }
    res_set = requests.post(f"{BASE_URL}/rules/set_effects/TEST_MOON_SET", json=set_update)
    print_response(res_set, "5. 设置套装规则 (POST /api/rules/set_effects)")

    # 6. 删除测试数据
    res_del = requests.delete(f"{BASE_URL}/characters/{TEST_ID}")
    print_response(res_del, f"6. 删除角色 (DELETE /api/characters/{TEST_ID})")

if __name__ == "__main__":
    run_content_test()