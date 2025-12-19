from fasthtml.common import *
import json
import os
from starlette.responses import RedirectResponse

# 数据路径
DATA_PATH = "data/rules/characters.json"


def load_characters():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载 characters.json 失败: {e}")
        return {}


def save_characters(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 全局变量初始化
characters = load_characters()

# 常量
skill_types = ["NormalAttack", "ChargedAttack", "PlungingAttack", "ElementalSkill", "ElementalBurst"]
elements = ["Physical", "Pyro", "Hydro", "Electro", "Cryo", "Dendro", "Anemo", "Geo"]
elements_with_null = ["null"] + elements
damage_types = ["attack", "Charged", "plunging", "Skill", "Burst"]
reactions = [None, "vaporize_hydro", "vaporize_pyro", "melt_pyro", "melt_cryo", "aggravate", "spread"]


# 工具函数
def get_character_options():
    opts = []
    for cid, data in characters.items():
        elems = data.get("base_stats", {}).get("elements")
        if elems:
            opts.append((cid, elems[0]))
    return opts


def get_character_options_with_empty():
    return [('', '（可选）')] + get_character_options()


# 自定义 JS/CSS
custom_assets = """
<style>
    .multiplier-row { display: grid; grid-template-columns: 1fr 1fr 60px; gap: 10px; align-items: end; margin-bottom: 8px; }
    .buff-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1.5fr 60px; gap: 10px; align-items: end; margin-bottom: 10px; }
    .remove-btn { background: #ff4444; color: white; border: none; border-radius: 4px; cursor: pointer; padding: 5px 10px; }
    .add-btn { background: #00aa00; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
    details { margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #fafafa; }
    summary { font-weight: bold; cursor: pointer; font-size: 1.1em; }
    .success-alert { background:#d4edda; color:#155724; padding:15px; border-radius:6px; margin:20px 0; border:1px solid #c3e6cb; }
    fieldset { display: flex; flex-wrap: wrap; gap: 15px; padding: 15px; border: 1px solid #ccc; border-radius: 6px; }
    fieldset legend { font-weight: bold; }
    .form-section { margin-bottom: 1.5rem; }
</style>
<script>
function addMultiplier(skill) {
    const container = document.getElementById(skill + '_multipliers');
    const index = container.children.length;
    const row = document.createElement('div');
    row.className = 'multiplier-row';
    row.innerHTML = `
        <select name="${skill}_mult_type_${index}">
            <option value="atk_percent">攻击力%</option>
            <option value="hp_percent">生命值%</option>
            <option value="def_percent">防御力%</option>
            <option value="em">元素精通</option>
        </select>
        <input type="number" step="0.01" name="${skill}_mult_value_${index}" value="0">
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">－</button>
    `;
    container.appendChild(row);
}

function addBuff() {
    const container = document.getElementById('buffs_container');
    const index = container.children.length;
    const row = document.createElement('div');
    row.className = 'buff-row';
    row.innerHTML = `
        <select name="buff_type_${index}">
            <option value="damage_bonus">伤害加成</option>
            <option value="elemental_bonus">元素伤害加成</option>
            <option value="atk_percent">攻击力%</option>
            <option value="hp_percent">生命值%</option>
            <option value="crit_rate">暴击率</option>
            <option value="crit_dmg">暴击伤害</option>
            <option value="em">元素精通</option>
            <option value="def_reduction">防御削弱</option>
            <option value="resistance_percent">抗性降低</option>
            <option value="burst_bonus">大招加成</option>
            <option value="skill_bonus">技能加成</option>
            <option value="charged_bonus">重击加成</option>
        </select>
        <input type="number" step="0.01" name="buff_value_${index}" value="0">
        <select name="buff_scope_${index}">
            <option value="self">自身</option>
            <option value="team">队伍</option>
        </select>
        <select name="buff_element_${index}">
            <option value="null">null（无元素限制）</option>
            <option value="Physical">Physical</option>
            <option value="Pyro">Pyro</option>
            <option value="Hydro">Hydro</option>
            <option value="Electro">Electro</option>
            <option value="Cryo">Cryo</option>
            <option value="Dendro">Dendro</option>
            <option value="Anemo">Anemo</option>
            <option value="Geo">Geo</option>
        </select>
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">－</button>
    `;
    container.appendChild(row);
}
</script>
"""

app, rt = fast_app(
    pico=True,
    hdrs=(
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.amber.min.css'),
        Script(custom_assets)
    )
)


# --- 路由部分 ---

@rt("/")
def get():
    # 确保主页数据同步
    global characters
    characters = load_characters()
    char_opts = get_character_options()
    char_opts_empty = get_character_options_with_empty()
    config_link = A("编辑配置", href="/edit_config",
                    cls="button", style="position: absolute; top: 20px; right: 20px; background:#ff8c00; color:white;")

    return Titled("原神伤害计算器 🎮",
                  config_link,
                  Div(
                      H2("角色与队伍配置", cls="text-center"),
                      Form(
                          Grid(
                              Div(Label("主C角色:"),
                                  Select(*[Option(f"{cid} ({elem})", value=cid) for cid, elem in char_opts],
                                         name="target_char", required=True)),
                              Div(Label("队友1 (可选):"),
                                  Select(*[Option(text, value=val) for val, text in char_opts_empty],
                                         name="teammate1")),
                          ),
                          Grid(
                              Div(Label("队友2 (可选):"),
                                  Select(*[Option(text, value=val) for val, text in char_opts_empty],
                                         name="teammate2")),
                              Div(Label("队友3 (可选):"),
                                  Select(*[Option(text, value=val) for val, text in char_opts_empty],
                                         name="teammate3")),
                          ),
                          Grid(
                              Div(Label("技能类型:"),
                                  Select(*[Option(st, value=st) for st in skill_types], name="skill_type",
                                         value="ElementalSkill")),
                              Div(Label("元素反应:"),
                                  Select(*[Option(r or "无", value=r or "") for r in reactions], name="reaction")),
                          ),
                          Button("计算伤害", type="submit", cls="primary", style="width: 100%; margin-top: 20px;"),
                          action="/result", method="post", cls="card"
                      ),
                      style="max-width: 900px; margin: 60px auto 40px; padding: 20px;"
                  ))


@rt("/result", methods=["POST"])
async def post(req):
    form_data = await req.form()
    target_char = form_data.get("target_char")
    teammates = [form_data.get(f"teammate{i}") for i in range(1, 4) if form_data.get(f"teammate{i}")]
    skill_type = form_data.get("skill_type", "ElementalSkill")
    reaction = form_data.get("reaction") or None

    try:
        from main import run_optimizer
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()
        run_optimizer(target_char, teammates, skill_type=skill_type, reaction=reaction)
        output = captured.getvalue()
    except Exception as e:
        output = f"计算出错：{str(e)}\n请检查 main.py 是否存在 run_optimizer 函数"
    finally:
        sys.stdout = old_stdout

    return Titled("优化结果",
                  Div(
                      H3("计算结果"),
                      Pre(output, style="background:#f8f9fa;padding:20px;border-radius:8px;overflow-x:auto;"),
                      A("← 返回修改", href="/", cls="button secondary mt-3"),
                      cls="card", style="max-width:1000px;margin:40px auto;"
                  ))


@rt("/edit_config")
def get(selected_char: str = "", saved: str = "0", new: str = "0"):
    current_chars = load_characters()
    char_list = list(current_chars.keys())
    is_new = new == "1"

    if is_new:
        selected_char = ""
        char_data = {"base_stats": {}, "skills": {}, "buffs": []}
    else:
        if not selected_char and char_list:
            selected_char = char_list[0]
        char_data = current_chars.get(selected_char, {"base_stats": {}, "skills": {}, "buffs": []})

    base = char_data.get("base_stats", {})
    current_elements = base.get("elements", [])
    alert = Div("✅ 修改已成功保存！", cls="success-alert") if saved == "1" else None

    element_fieldset = Fieldset(
        Legend("角色元素（可多选）"),
        *[Label(Input(type="checkbox", name="elements", value=e, checked=(e in current_elements)), f" {e}") for e in
          elements]
    )

    form_content = [alert] if alert else []
    form_content += [
        H3("新建角色" if is_new else f"编辑角色：{selected_char}", cls="text-center mt-4"),
        # 记录旧名称，用于更名时的数据迁移
        Input(type="hidden", name="old_char_id", value=selected_char),
        Grid(
            Div(element_fieldset),
            Div(Label("基础攻击力"), Input(type="number", name="atk", value=base.get("atk", 300))),
            Div(Label("基础生命值"), Input(type="number", name="hp", value=base.get("hp", 12000))),
        ),
        Grid(
            Div(Label("基础防御力"), Input(type="number", name="def", value=base.get("def", 700))),
            Div(Label("暴击率"),
                Input(type="number", step="0.01", name="crit_rate", value=base.get("crit_rate", 0.05))),
            Div(Label("暴击伤害"), Input(type="number", step="0.01", name="crit_dmg", value=base.get("crit_dmg", 0.5))),
            Div(Label("元素精通"), Input(type="number", name="em", value=base.get("em", 0))),
        ),
        Hr(),
        H4("技能配置"),
    ]

    skills = char_data.get("skills", {})
    for skill_name in skill_types:
        skill_info = skills.get(skill_name, {}).get("default", {})
        element = skill_info.get("element", "Physical")
        dmg_type = skill_info.get("damage_type", "Skill")
        multipliers = skill_info.get("multipliers", [])

        mult_rows = []
        for i, m in enumerate(multipliers):
            mult_rows.append(
                Div(
                    Select(*[Option(txt, value=val, selected=(val == m.get("type")))
                             for val, txt in [("atk_percent", "攻击力%"), ("hp_percent", "生命值%"),
                                              ("def_percent", "防御力%"), ("em", "元素精通")]],
                           name=f"{skill_name}_mult_type_{i}"),
                    Input(type="number", step="0.01", name=f"{skill_name}_mult_value_{i}", value=m.get("value", 0)),
                    Button("－", type="button", cls="remove-btn", onclick="this.parentElement.remove()"),
                    cls="multiplier-row"
                )
            )

        form_content += [
            Details(
                Summary(skill_name),
                Grid(
                    Div(Label("元素类型"), Select(*[Option(e, value=e, selected=(e == element)) for e in elements],
                                                  name=f"{skill_name}_element")),
                    Div(Label("伤害类型"), Select(*[Option(d, value=d, selected=(d == dmg_type)) for d in damage_types],
                                                  name=f"{skill_name}_damage_type")),
                ),
                Div(*mult_rows, id=f"{skill_name}_multipliers"),
                Button("＋ 添加倍率", type="button", cls="add-btn", onclick=f"addMultiplier('{skill_name}')")
            )
        ]

    buffs = char_data.get("buffs", [])
    form_content += [
        Hr(),
        H4("Buff 增益效果"),
        Div(id="buffs_container", *[
            Div(
                Select(*[Option(txt, value=val, selected=(val == b.get("type")))
                         for val, txt in [
                             ("damage_bonus", "伤害加成"), ("elemental_bonus", "元素伤害加成"),
                             ("atk_percent", "攻击力%"), ("hp_percent", "生命值%"),
                             ("crit_rate", "暴击率"), ("crit_dmg", "暴击伤害"),
                             ("em", "元素精通"), ("def_reduction", "防御削弱"),
                             ("resistance_percent", "抗性降低"), ("burst_bonus", "大招加成"),
                             ("skill_bonus", "技能加成"), ("charged_bonus", "重击加成")
                         ]], name=f"buff_type_{i}"),
                Input(type="number", step="0.01", name=f"buff_value_{i}", value=b.get("value", 0)),
                Select(Option("自身", value="self", selected=(b.get("scope", "self") == "self")),
                       Option("队伍", value="team", selected=(b.get("scope", "self") == "team")),
                       name=f"buff_scope_{i}"),
                Select(*[Option(e if e != "null" else "null（无元素限制）", value=e,
                                selected=(e == b.get("element", "null"))) for e in elements_with_null],
                       name=f"buff_element_{i}"),
                Button("－", type="button", cls="remove-btn", onclick="this.parentElement.remove()"),
                cls="buff-row"
            ) for i, b in enumerate(buffs)
        ]),
        Button("＋ 添加 Buff", type="button", cls="add-btn", onclick="addBuff()"),
        Hr(),
        Button("💾 保存角色", type="submit", cls="primary large")
    ]

    return Titled("角色配置管理 ⚙️",
                  Div(
                      A("← 返回主页", href="/", cls="button outline"),
                      A("＋ 新建角色", href="/edit_config?new=1", cls="button", style="margin-left:10px;"),
                      style="margin-bottom:20px;"
                  ),
                  Div(
                      Select(*[Option("— 选择现有角色 —", value="", disabled=not char_list)] +
                              [Option(cid, value=cid, selected=(cid == selected_char and not is_new)) for cid in
                               char_list],
                             onchange="if(this.value) location.href='/edit_config?selected_char='+this.value",
                             cls="mb-4"),
                      Form(
                          Label("角色ID (保存后将同步更新)"),
                          Input(type="text", name="char_id", value=selected_char, placeholder="角色ID（如 nahida）",
                                required=True, style="font-family: monospace;"),  # 去掉了 readonly
                          *form_content,
                          action="/save_config",
                          method="post"
                      ),
                      cls="card", style="max-width:1200px; margin:20px auto; padding:30px;"
                  ))


@rt("/save_config", methods=["POST"])
async def post(req):
    form_data = await req.form()
    new_char_id = form_data.get("char_id", "").strip()
    old_char_id = form_data.get("old_char_id", "").strip()

    if not new_char_id:
        return RedirectResponse("/edit_config", status_code=303)

    global characters
    characters = load_characters()

    # --- 核心改名逻辑 ---
    # 如果旧角色存在且名称发生了变化
    if old_char_id and old_char_id in characters and old_char_id != new_char_id:
        # 1. 拷贝旧数据到新 Key
        characters[new_char_id] = characters[old_char_id]
        # 2. 删除旧 Key
        del characters[old_char_id]

    # 初始化新键数据
    data = characters.setdefault(new_char_id, {"base_stats": {}, "skills": {}, "buffs": []})
    base = data["base_stats"]

    # 元素多选处理
    selected_elements = [v for k, v in form_data.items() if k == "elements"]
    base["elements"] = selected_elements or ["Physical"]

    # 基础数值
    base["atk"] = int(form_data.get("atk", 300))
    base["hp"] = int(form_data.get("hp", 12000))
    base["def"] = int(form_data.get("def", 700))
    base["crit_rate"] = float(form_data.get("crit_rate", 0.05))
    base["crit_dmg"] = float(form_data.get("crit_dmg", 0.5))
    base["em"] = int(form_data.get("em", 0))

    # 技能解析
    skills = data.setdefault("skills", {})
    for skill_name in skill_types:
        skills.setdefault(skill_name, {"default": {"multipliers": [], "element": "Physical", "damage_type": "Skill"}})
        default = skills[skill_name]["default"]
        default["element"] = form_data.get(f"{skill_name}_element", "Physical")
        default["damage_type"] = form_data.get(f"{skill_name}_damage_type", "Skill")

        multipliers = []
        i = 0
        while f"{skill_name}_mult_type_{i}" in form_data:
            mtype = form_data.get(f"{skill_name}_mult_type_{i}")
            mval = form_data.get(f"{skill_name}_mult_value_{i}")
            if mtype and mval:
                multipliers.append({"type": mtype, "value": float(mval)})
            i += 1
        default["multipliers"] = multipliers

    # Buff 解析
    data["buffs"] = []
    i = 0
    while f"buff_type_{i}" in form_data:
        btype = form_data.get(f"buff_type_{i}")
        if btype:
            data["buffs"].append({
                "type": btype,
                "value": float(form_data.get(f"buff_value_{i}", 0)),
                "scope": form_data.get(f"buff_scope_{i}", "self"),
                "element": form_data.get(f"buff_element_{i}", "null")
            })
        i += 1

    save_characters(characters)
    # 强制同步内存数据
    characters = load_characters()

    return RedirectResponse(f"/edit_config?selected_char={new_char_id}&saved=1", status_code=303)


serve()