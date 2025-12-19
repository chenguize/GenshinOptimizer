import json
import os


def convert_mona_to_my_format(input_file: str, output_file: str):
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        mona_data = json.load(f)

    # 1. 完整的映射表（处理莫娜驼峰命名）
    raw_set_map = {
        "instructor": "教官",
        "shimenawareminiscence": "追忆之注连",
        "tenacityofthemillelith": "千岩牢固",
        "finaleofthedeepgalleries": "深廊终曲",
        "thunderingfury": "如雷的盛怒",
        "wanderertroupe": "流浪大地的乐团",
        "gladiatorfinale": "角斗士的终幕礼",
        "longnightsoath": "长夜显现的誓言", "obsidiancodex": "黑曜典藏",
        "scrolloftheheroofcindercity": "烬城勇者绘卷", "scrolloftheheroofanancientcity": "烬城勇者绘卷",
        "weaverssongofthemoonlitnight": "纺月的夜歌", "pinnacleofcreation": "穹境示显之夜",
        "marechausseehunter": "逐影猎人", "goldentroupe": "黄金剧团",
        "nighttimewhispersintheechoingwoods": "回声之林夜话", "songofdayspast": "昔时之歌",
        "fragmentofharmonicwhimsy": "谐律异想断章", "unfinishedreverie": "未竟的遐思",
        "deepwoodmemories": "深林的记忆", "gildeddreams": "饰金之梦",
        "emblemofseveredfate": "绝缘之旗印", "noblesseoblige": "昔日宗室之仪",
        "viridescentvenerer": "翠绿之影", "archaicpetra": "悠古的磐岩",
        "nymphsdream": "水仙之梦", "heartofdepth": "沉沦之心"
    }

    element_map = {
        "icebonus": "Cryo", "firebonus": "Pyro", "waterbonus": "Hydro",
        "windbonus": "Anemo", "rockbonus": "Geo", "thunderbonus": "Electro",
        "grassbonus": "Dendro", "physicalbonus": "Physical"
    }

    raw_stat_map = {
        "lifestatic": "hp_flat", "lifepercentage": "hp_percent",
        "attackstatic": "atk_flat", "attackpercentage": "atk_percent",
        "defendstatic": "def_flat", "defendpercentage": "def_percent",
        "elementalmastery": "em", "recharge": "energy_recharge",
        "critical": "crit_rate", "criticaldamage": "crit_dmg",
        "cureeffect": "healing_bonus"
    }
    for k in element_map.keys(): raw_stat_map[k] = "elemental_bonus"

    slot_fix_map = {
        "flower": "flower", "feather": "plume", "plume": "plume",
        "sand": "sands", "sands": "sands", "cup": "goblet",
        "goblet": "goblet", "head": "circlet", "circlet": "circlet"
    }

    # 2. 提取数据
    all_raw_artifacts = []
    if isinstance(mona_data, dict):
        if "artifacts" in mona_data:
            all_raw_artifacts = mona_data["artifacts"]
        else:
            for val in mona_data.values():
                if isinstance(val, list): all_raw_artifacts.extend(val)
    elif isinstance(mona_data, list):
        all_raw_artifacts = mona_data

    result = []
    skipped_count = 0
    skipped_details = []
    current_id = 1

    for art in all_raw_artifacts:
        # --- 等级筛选逻辑 ---
        level = art.get("level", 0)
        if level != 20:
            skipped_count += 1
            skipped_details.append(f"ID: {art.get('id', 'N/A')} | Set: {art.get('setName')} | Level: {level}")
            continue

        # 部位与套装识别
        raw_pos = art.get("position", art.get("slot", ""))
        target_slot = slot_fix_map.get(raw_pos.lower())
        if not target_slot: continue

        set_name = raw_set_map.get(art.get("setName", "").lower(), art.get("setName"))

        # 主副词条处理
        m_tag = art.get("mainTag", {})
        mk = m_tag.get("name", "").lower()

        new_art = {
            "id": current_id,
            "set": set_name,
            "slot": target_slot,
            # "level" 字段按要求移除
            "main_stat": {
                "type": raw_stat_map.get(mk, mk),
                "value": m_tag.get("value", 0),
                "element": element_map.get(mk, "null")
            },
            "substats": []
        }

        for sub in art.get("normalTags", []):
            sk = sub["name"].lower()
            new_art["substats"].append({
                "type": raw_stat_map.get(sk, sk),
                "value": sub["value"],
                "element": "null"
            })

        result.append(new_art)
        current_id += 1

    # 3. 单行保存
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, art in enumerate(result):
            line = json.dumps(art, ensure_ascii=False)
            f.write(f"  {line}{',' if i < len(result) - 1 else ''}\n")
        f.write("]\n")

    # 4. 输出报告
    print(f"\n" + "═" * 50)
    print(f"【圣遗物转换与筛选报告】")
    print(f"扫描源数据总量: {len(all_raw_artifacts)} 件")
    print(f"筛选掉非20级圣遗物: {skipped_count} 件")
    print(f"最终成功转换: {len(result)} 件")
    print("═" * 50)

    if skipped_count > 0:
        print("\n[过滤详情 (Level != 20)]:")
        for detail in skipped_details[:10]:  # 仅显示前10条
            print(f"  - {detail}")
        if skipped_count > 10:
            print(f"  ... 以及其他 {skipped_count - 10} 件")
    print("═" * 50 + "\n")


if __name__ == "__main__":
    convert_mona_to_my_format("../data/raw/mona.json", "../data/processed/artifacts.json")